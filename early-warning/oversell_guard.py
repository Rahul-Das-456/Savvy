#!/usr/bin/env python3
"""
Oversell Guard: an early-warning check for Exception 1 (sell order larger than the position).

It runs in two places:
  1. Pre-trade: every sell order is checked against what the account can actually deliver
     by settlement (T+1). Hard failures are blocked before they reach Fidelity.
  2. Intraday / nightly: the same rules run across the day's order flow to catch patterns
     (duplicates, cumulative sells, repeat advisors) and produce a supervisor brief.

The rules decide. AI never decides to block or release an order. The optional --ai flag
asks Claude to turn the alerts into a supervisor brief and plain-English advisor messages.

All data in ./data is fake.

Usage:
  python3 oversell_guard.py                 # rules only, writes out/alerts.json and out/alerts.md
  python3 oversell_guard.py --ai            # adds a Claude-written brief (needs `pip install anthropic`
                                            # and ANTHROPIC_API_KEY or an `ant auth login` profile)
  python3 oversell_guard.py --today 2026-11-05 --data ./data --out ./out
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path

HOLIDAYS = {dt.date(2026, 11, 11), dt.date(2026, 11, 26), dt.date(2026, 12, 25)}  # bond-market holidays used for T+1 math (demo)
DUP_WINDOW_SEC = 600          # same account, symbol, side and quantity within 10 minutes
NEAR_FULL = 0.90              # sell of 90%+ of what is available: confirm it is a full liquidation
REPEAT_LOOKBACK_DAYS = 30     # advisor with 2+ oversell breaks in 30 days gets escalated
CA_WINDOW_BDAYS = 2           # corporate action ex-date within 2 business days

SEV_ORDER = {"BLOCK": 0, "HOLD": 1, "WARN": 2, "INFO": 3}


# ---------- data ----------

def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def add_bdays(d: dt.date, n: int) -> dt.date:
    while n > 0:
        d += dt.timedelta(days=1)
        if d.weekday() < 5 and d not in HOLIDAYS:
            n -= 1
    return d


@dataclass
class Alert:
    order_id: str
    time: str
    account: str
    advisor: str
    symbol: str
    qty: int
    severity: str
    rule: str
    finding: str
    action: str
    cites: str
    available: int | None = None
    context: dict = field(default_factory=dict)


# ---------- the checks ----------

def run(data: Path, today: dt.date) -> tuple[list[Alert], dict]:
    positions = {(r["account"], r["symbol"]): r for r in read_csv(data / "positions.csv")}
    pending = defaultdict(list)
    for r in read_csv(data / "pending.csv"):
        pending[(r["account"], r["symbol"])].append(r)
    corp = defaultdict(list)
    for r in read_csv(data / "corporate_actions.csv"):
        corp[r["symbol"]].append(r)
    history = read_csv(data / "history.csv")
    orders = sorted(read_csv(data / "orders.csv"), key=lambda r: r["time"])

    settle = add_bdays(today, 1)  # T+1 under SEA Rule 15c6-1
    sold_today = defaultdict(int)  # cumulative sells per account and symbol
    seen = []                      # for duplicate detection
    alerts: list[Alert] = []

    # advisors with repeat oversell breaks
    cutoff = today - dt.timedelta(days=REPEAT_LOOKBACK_DAYS)
    breaks_by_adv = defaultdict(int)
    for h in history:
        if h["event"] == "OVERSELL_BREAK" and dt.date.fromisoformat(h["date"]) >= cutoff:
            breaks_by_adv[h["advisor"]] += 1

    for o in orders:
        if o["side"] != "SELL":
            continue
        key = (o["account"], o["symbol"])
        qty = int(o["qty"])
        pos = positions.get(key)
        base = dict(order_id=o["order_id"], time=o["time"], account=o["account"], advisor=o["advisor"],
                    symbol=o["symbol"], qty=qty)

        # what can be delivered by settlement
        settled = int(pos["settled_qty"]) if pos else 0
        pledged = int(pos["pledged_qty"] or 0) if pos else 0
        buys_in, out, unconfirmed_in = 0, 0, 0
        notes = []
        for p in pending.get(key, []):
            p_qty, p_date = int(p["qty"]), dt.date.fromisoformat(p["expected_settle"])
            if p["type"] == "BUY_UNSETTLED" and p["status"] == "CONFIRMED" and p_date <= settle:
                buys_in += p_qty
                notes.append(f"{p_qty} from an unsettled buy settling {p_date}")
            elif p["type"] == "ACATS_OUT" and p["status"] in ("APPROVED", "IN_PROGRESS"):
                out += p_qty
                notes.append(f"{p_qty} committed to an outgoing ACATS transfer")
            elif p["type"] == "ACATS_IN":
                unconfirmed_in += p_qty
                notes.append(f"{p_qty} on an incoming ACATS transfer, status {p['status']}, due {p_date}")
        available = settled - pledged + buys_in - out - sold_today[key]
        ctx = dict(settled=settled, pledged=pledged, unsettled_buys=buys_in, ats_out=out,
                   sold_earlier_today=sold_today[key], incoming_unconfirmed=unconfirmed_in, notes=notes)

        def add(sev, rule, finding, action, cites):
            alerts.append(Alert(**base, severity=sev, rule=rule, finding=finding, action=action, cites=cites,
                                available=available, context=ctx))

        # 1. account restriction (legal hold, freeze)
        if pos and pos.get("restriction"):
            add("BLOCK", "R1 Restricted account",
                f"Account carries {pos['restriction']}. No sells until Legal releases it.",
                "Reject the order. Notify Compliance and Legal the same day; log the attempt.",
                "FINRA 3110(b); FINRA 4511")
            continue  # nothing else matters until the hold is lifted

        # 2. duplicate order
        t = dt.datetime.combine(today, dt.time.fromisoformat(o["time"]))
        for prev in seen:
            if (prev["account"], prev["symbol"], prev["qty"]) == (o["account"], o["symbol"], o["qty"]) \
                    and 0 <= (t - prev["_t"]).total_seconds() <= DUP_WINDOW_SEC:
                add("HOLD", "R2 Possible duplicate",
                    f"Same account, symbol and quantity as {prev['order_id']} {int((t - prev['_t']).total_seconds())}s earlier.",
                    "Hold. Ask the advisor to confirm both orders are intended before release.",
                    "FINRA 3110; SEA 17a-3(a)(6)")
        seen.append({**o, "_t": t})

        # 3. oversell: the exception this tool exists to prevent
        if qty > available:
            short = qty - available
            if qty <= available + unconfirmed_in and unconfirmed_in:
                add("HOLD", "R3 Depends on unconfirmed transfer",
                    f"Covers only if the incoming transfer arrives. Without it, {short} shares short at T+1 ({settle}).",
                    "Hold until Fidelity confirms the ACATS shares, or reduce the order to the available amount.",
                    "Reg SHO 200(g); Reg SHO 204(a); SEA 15c3-3(m)")
            else:
                why = "pledged as collateral" if pledged and qty <= settled - out - sold_today[key] + buys_in else \
                      "committed to an outgoing transfer" if out else \
                      "already sold earlier today" if sold_today[key] else "not in the account"
                add("BLOCK", "R4 Sell exceeds deliverable position",
                    f"Sells {qty}, can deliver {max(available, 0)} by {settle}. {short} shares short; the excess is {why}.",
                    "Block pre-trade. Advisor resubmits for the available amount, or Ops confirms incoming shares first.",
                    "Reg SHO 200(g)(1); Reg SHO 203(b)(1); Reg SHO 204(a); FINRA 4311")
        elif available > 0 and qty >= NEAR_FULL * available and \
                not any(a.order_id == o["order_id"] and a.severity in ("BLOCK", "HOLD") for a in alerts):
            add("INFO", "R5 Near-full liquidation",
                f"Sells {qty} of {available} available ({qty / available:.0%}).",
                "Pass. Confirm the client meant a full or near-full exit; check for open orders elsewhere.",
                "FINRA 2090")

        # 4. corporate action around settlement changes the share count
        for ca in corp.get(o["symbol"], []):
            ex = dt.date.fromisoformat(ca["ex_date"])
            if today <= ex <= add_bdays(today, CA_WINDOW_BDAYS):
                add("WARN", "R6 Corporate action near settlement",
                    f"{ca['action']} ({ca['detail']}) goes ex on {ex}. Share count and price basis change around settlement.",
                    "Pass, but confirm the order is on the right basis and watch it through settlement.",
                    "SEA 17a-3(a)(6); FINRA 11000 series")

        # 5. reliance on unsettled buy
        if buys_in and qty > settled - pledged - out - sold_today[key] and qty <= available:
            add("WARN", "R7 Relies on an unsettled buy",
                f"{buys_in} of the shares come from a buy that settles {settle}. If that buy fails, so does this sale.",
                "Pass. Put both trades on the settlement watch list.",
                "Reg SHO 200(g)(1)")

        # 6. repeat advisor
        n = breaks_by_adv.get(o["advisor"], 0)
        if n >= 2 and any(a.order_id == o["order_id"] and a.severity in ("BLOCK", "HOLD") for a in alerts):
            add("WARN", "R8 Repeat advisor",
                f"{o['advisor']} had {n} oversell breaks in the last {REPEAT_LOOKBACK_DAYS} days.",
                "Escalate to the supervising principal. Offer order-entry coaching; review for a pattern.",
                "FINRA 3110(a)")

        # only orders that go out use up the position
        blocked = any(a.order_id == o["order_id"] and a.severity == "BLOCK" for a in alerts)
        if not blocked:
            sold_today[key] += qty

    sells = [o for o in orders if o["side"] == "SELL"]
    flagged = {a.order_id for a in alerts if a.severity in ("BLOCK", "HOLD")}
    metrics = dict(
        run_date=today.isoformat(), settlement_date=settle.isoformat(), sell_orders=len(sells),
        blocked=len({a.order_id for a in alerts if a.severity == "BLOCK"}),
        held=len({a.order_id for a in alerts if a.severity == "HOLD"} - {a.order_id for a in alerts if a.severity == "BLOCK"}),
        warned=len({a.order_id for a in alerts if a.severity == "WARN"} - flagged),
        clean=len(sells) - len({a.order_id for a in alerts if a.severity != "INFO"}),
        breaks_prevented=len(flagged),
    )
    alerts.sort(key=lambda a: (SEV_ORDER[a.severity], a.time))
    return alerts, metrics


# ---------- outputs ----------

def advisor_message(a: Alert) -> str:
    if a.rule.startswith("R1"):
        return (f"Order {a.order_id} for account {a.account} was not sent. The account is restricted. "
                "Compliance will contact you directly; please don't resubmit.")
    if a.rule.startswith("R2"):
        return (f"Order {a.order_id} ({a.qty} {a.symbol}) looks like a repeat of an earlier order. "
                "It's on hold. Reply 'confirm' if you meant to place both.")
    if a.rule.startswith("R3"):
        return (f"Order {a.order_id} needs shares that are still arriving by transfer. It's on hold until Fidelity "
                f"confirms them. You can sell up to {max(a.available or 0, 0)} {a.symbol} now.")
    if a.rule.startswith("R4"):
        return (f"Order {a.order_id} was not sent: it sells {a.qty} {a.symbol} but the account can deliver "
                f"{max(a.available or 0, 0)} by settlement. Resubmit for {max(a.available or 0, 0)} or call Ops.")
    return ""


def write_outputs(alerts: list[Alert], metrics: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "alerts.json").write_text(json.dumps({"metrics": metrics, "alerts": [asdict(a) for a in alerts]}, indent=2))
    lines = [f"# Oversell Guard, {metrics['run_date']} (settles {metrics['settlement_date']})", "",
             f"{metrics['sell_orders']} sell orders checked: {metrics['blocked']} blocked, {metrics['held']} held, "
             f"{metrics['warned']} passed with a warning, {metrics['clean']} clean.", "",
             "| Sev | Order | Time | Acct | Advisor | Order | Rule | Finding | Action |",
             "|---|---|---|---|---|---|---|---|---|"]
    for a in alerts:
        lines.append(f"| {a.severity} | {a.order_id} | {a.time} | {a.account} | {a.advisor} | {a.qty} {a.symbol} | "
                     f"{a.rule} | {a.finding} | {a.action} |")
    msgs = [(a, advisor_message(a)) for a in alerts if advisor_message(a)]
    if msgs:
        lines += ["", "## Advisor messages (sent automatically)", ""]
        lines += [f"- **{a.advisor}**: {m}" for a, m in msgs]
    (out / "alerts.md").write_text("\n".join(lines) + "\n")


def print_table(alerts: list[Alert], metrics: dict) -> None:
    print(f"\nOversell Guard  run {metrics['run_date']}  settles {metrics['settlement_date']}")
    print(f"{metrics['sell_orders']} sells | {metrics['blocked']} blocked | {metrics['held']} held | "
          f"{metrics['warned']} warned | {metrics['clean']} clean\n")
    for a in alerts:
        print(f"{a.severity:<5} {a.order_id}  {a.time}  #{a.account:<6} {a.qty:>4} {a.symbol:<5}  {a.rule}")
        print(f"      {a.finding}")
        print(f"      -> {a.action}  [{a.cites}]")


# ---------- optional AI brief ----------

SYSTEM = """You write the morning brief for a broker-dealer operations supervisor.
You get the output of a rules engine that checks sell orders against deliverable positions.
The rules engine has already decided what is blocked or held. Never change, soften or overturn a decision.
Write in plain English, short sentences, no jargon beyond rule numbers.
Output: (1) a 3-sentence summary, (2) the items a human must act on today, owner and deadline for each,
(3) any pattern across advisors or channels worth a control change. Never mention SARs or AML."""


def ai_brief(alerts: list[Alert], metrics: dict) -> str:
    try:
        import anthropic
    except ImportError:
        return "AI brief skipped: run `pip install anthropic` first."
    client = anthropic.Anthropic()
    payload = json.dumps({"metrics": metrics, "alerts": [asdict(a) for a in alerts]}, indent=1)
    try:
        resp = client.beta.messages.create(
            model="claude-opus-5-5",
            max_tokens=4000,
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=SYSTEM,
            messages=[{"role": "user", "content": f"Today's rules-engine output:\n{payload}"}],
        )
    except anthropic.APIConnectionError:
        return "AI brief skipped: no network."
    except anthropic.AuthenticationError:
        return "AI brief skipped: no Anthropic credentials (set ANTHROPIC_API_KEY or run `ant auth login`)."
    except anthropic.APIStatusError as e:
        return f"AI brief skipped: API error {e.status_code}."
    if resp.stop_reason == "refusal":
        return "AI brief skipped: the model declined."
    return "".join(b.text for b in resp.content if b.type == "text")


def main(argv=None) -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=here / "data")
    ap.add_argument("--out", type=Path, default=here / "out")
    ap.add_argument("--today", type=dt.date.fromisoformat, default=dt.date(2026, 11, 5))
    ap.add_argument("--ai", action="store_true", help="add a Claude-written supervisor brief")
    args = ap.parse_args(argv)

    alerts, metrics = run(args.data, args.today)
    write_outputs(alerts, metrics, args.out)
    print_table(alerts, metrics)
    if args.ai:
        brief = ai_brief(alerts, metrics)
        (args.out / "brief.md").write_text(brief + "\n")
        print("\n--- AI supervisor brief ---\n" + brief)
    print(f"\nWrote {args.out / 'alerts.json'} and {args.out / 'alerts.md'}")
    return 1 if metrics["blocked"] else 0


if __name__ == "__main__":
    sys.exit(main())
