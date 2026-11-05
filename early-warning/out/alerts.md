# Oversell Guard, 2026-11-05 (settles 2026-11-06)

10 sell orders checked: 5 blocked, 1 held, 2 passed with a warning, 2 clean.

| Sev | Order | Time | Acct | Advisor | Order | Rule | Finding | Action |
|---|---|---|---|---|---|---|---|---|
| BLOCK | ORD-1001 | 09:31:04 | 12345 | A. Patel | 500 AAPL | R4 Sell exceeds deliverable position | Sells 500, can deliver 450 by 2026-11-06. 50 shares short; the excess is not in the account. | Block pre-trade. Advisor resubmits for the available amount, or Ops confirms incoming shares first. |
| BLOCK | ORD-1003 | 09:35:12 | 30442 | L. Chen | 300 TSLA | R4 Sell exceeds deliverable position | Sells 300, can deliver 200 by 2026-11-06. 100 shares short; the excess is pledged as collateral. | Block pre-trade. Advisor resubmits for the available amount, or Ops confirms incoming shares first. |
| BLOCK | ORD-1006 | 09:47:30 | 12345 | A. Patel | 150 MSFT | R4 Sell exceeds deliverable position | Sells 150, can deliver 0 by 2026-11-06. 150 shares short; the excess is committed to an outgoing transfer. | Block pre-trade. Advisor resubmits for the available amount, or Ops confirms incoming shares first. |
| BLOCK | ORD-1007 | 09:52:18 | 78901 | K. Brooks | 900 VTI | R1 Restricted account | Account carries LEGAL_HOLD. No sells until Legal releases it. | Reject the order. Notify Compliance and Legal the same day; log the attempt. |
| BLOCK | ORD-1009 | 10:03:41 | 55120 | J. Moreno | 75 GOOGL | R4 Sell exceeds deliverable position | Sells 75, can deliver 5 by 2026-11-06. 70 shares short; the excess is already sold earlier today. | Block pre-trade. Advisor resubmits for the available amount, or Ops confirms incoming shares first. |
| HOLD | ORD-1005 | 09:44:01 | 41907 | A. Patel | 220 AMZN | R3 Depends on unconfirmed transfer | Covers only if the incoming transfer arrives. Without it, 70 shares short at T+1 (2026-11-06). | Hold until Fidelity confirms the ACATS shares, or reduce the order to the available amount. |
| HOLD | ORD-1009 | 10:03:41 | 55120 | J. Moreno | 75 GOOGL | R2 Possible duplicate | Same account, symbol and quantity as ORD-1008 32s earlier. | Hold. Ask the advisor to confirm both orders are intended before release. |
| WARN | ORD-1001 | 09:31:04 | 12345 | A. Patel | 500 AAPL | R8 Repeat advisor | A. Patel had 2 oversell breaks in the last 30 days. | Escalate to the supervising principal. Offer order-entry coaching; review for a pattern. |
| WARN | ORD-1004 | 09:41:55 | 22018 | J. Moreno | 110 NVDA | R6 Corporate action near settlement | SPLIT (4-for-1 forward split) goes ex on 2026-11-06. Share count and price basis change around settlement. | Pass, but confirm the order is on the right basis and watch it through settlement. |
| WARN | ORD-1004 | 09:41:55 | 22018 | J. Moreno | 110 NVDA | R7 Relies on an unsettled buy | 40 of the shares come from a buy that settles 2026-11-06. If that buy fails, so does this sale. | Pass. Put both trades on the settlement watch list. |
| WARN | ORD-1005 | 09:44:01 | 41907 | A. Patel | 220 AMZN | R8 Repeat advisor | A. Patel had 2 oversell breaks in the last 30 days. | Escalate to the supervising principal. Offer order-entry coaching; review for a pattern. |
| WARN | ORD-1006 | 09:47:30 | 12345 | A. Patel | 150 MSFT | R8 Repeat advisor | A. Patel had 2 oversell breaks in the last 30 days. | Escalate to the supervising principal. Offer order-entry coaching; review for a pattern. |
| WARN | ORD-1008 | 10:03:09 | 55120 | J. Moreno | 75 GOOGL | R7 Relies on an unsettled buy | 20 of the shares come from a buy that settles 2026-11-06. If that buy fails, so does this sale. | Pass. Put both trades on the settlement watch list. |
| INFO | ORD-1004 | 09:41:55 | 22018 | J. Moreno | 110 NVDA | R5 Near-full liquidation | Sells 110 of 120 available (92%). | Pass. Confirm the client meant a full or near-full exit; check for open orders elsewhere. |
| INFO | ORD-1008 | 10:03:09 | 55120 | J. Moreno | 75 GOOGL | R5 Near-full liquidation | Sells 75 of 80 available (94%). | Pass. Confirm the client meant a full or near-full exit; check for open orders elsewhere. |

## Advisor messages (sent automatically)

- **A. Patel**: Order ORD-1001 was not sent: it sells 500 AAPL but the account can deliver 450 by settlement. Resubmit for 450 or call Ops.
- **L. Chen**: Order ORD-1003 was not sent: it sells 300 TSLA but the account can deliver 200 by settlement. Resubmit for 200 or call Ops.
- **A. Patel**: Order ORD-1006 was not sent: it sells 150 MSFT but the account can deliver 0 by settlement. Resubmit for 0 or call Ops.
- **K. Brooks**: Order ORD-1007 for account 78901 was not sent. The account is restricted. Compliance will contact you directly; please don't resubmit.
- **J. Moreno**: Order ORD-1009 was not sent: it sells 75 GOOGL but the account can deliver 5 by settlement. Resubmit for 5 or call Ops.
- **A. Patel**: Order ORD-1005 needs shares that are still arriving by transfer. It's on hold until Fidelity confirms them. You can sell up to 150 AMZN now.
- **J. Moreno**: Order ORD-1009 (75 GOOGL) looks like a repeat of an earlier order. It's on hold. Reply 'confirm' if you meant to place both.
