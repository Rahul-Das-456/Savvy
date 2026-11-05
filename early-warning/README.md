# Oversell Guard

Early-warning check for Exception 1 of the Savvy take-home: a sell order larger than what the account can deliver at T+1.

- Runs pre-trade on every sell, and again across the day's order flow.
- Deterministic rules decide what is blocked or held. AI never releases an order.
- Optional `--ai` flag: Claude (`claude-opus-5-5`) turns the alerts into a supervisor brief.

```bash
python3 oversell_guard.py            # rules only, standard library
pip install anthropic && python3 oversell_guard.py --ai
```

| Rule | Trigger | Result |
|---|---|---|
| R1 | Account restricted (legal hold, freeze) | Block |
| R2 | Same account, symbol, quantity within 10 minutes | Hold |
| R3 | Order covered only by an unconfirmed incoming ACATS transfer | Hold |
| R4 | Sell > settled − pledged + confirmed buys settling by T+1 − outgoing transfers − earlier sells today | Block |
| R5 | Sell is 90%+ of available | Info |
| R6 | Split or other corporate action goes ex within 2 business days | Warn |
| R7 | Sale relies on an unsettled buy | Warn |
| R8 | Advisor had 2+ oversell breaks in 30 days | Escalate to principal |

All data in `data/` is fake. Output lands in `out/alerts.json` and `out/alerts.md`.
