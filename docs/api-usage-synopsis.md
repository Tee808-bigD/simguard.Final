# API Usage Synopsis

## CAMARA APIs in the SimGuard flow

- `SIM Swap`
  - Used to detect recent subscriber identity changes.
  - High weighting because it is directly associated with account takeover attempts.

- `Device Swap`
  - Used to detect movement of the SIM to a different handset.
  - Strengthens suspicion when paired with SIM swap or abnormal value.

- `Number Verification`
  - Used to verify trust in the active number-to-device relationship.
  - Helpful for reducing false trust in compromised sessions.

## How the APIs are orchestrated

1. Agent submits a transaction.
2. SimGuard runs telecom trust checks.
3. Risk scoring combines raw signal outcomes with transaction value.
4. AI produces a plain-language operational decision.
5. Dashboard and alert feed update in real time.

## Demo reliability strategy

- Default mode is `SIMULATION` for a deterministic hackathon demo.
- `AUTO` and `LIVE` allow the same app to demonstrate real integrations when keys and network access are available.
- Every signal exposes its `source` so judges can distinguish simulation from live data cleanly.
