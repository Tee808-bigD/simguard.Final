# SimGuard Prototype Deck

## 1. Problem statement and context

- SIM swap fraud lets attackers take over a subscriber identity, intercept OTPs, and drain mobile money wallets.
- Agents are often the last human checkpoint before value leaves the system.
- Existing checks are slow, fragmented, or invisible to the frontline operator.

## 2. Proposed solution and API usage

- SimGuard gives an agent a single decision surface: `APPROVE`, `FLAG_FOR_REVIEW`, or `BLOCK`.
- CAMARA signals used:
  - SIM Swap
  - Device Swap
  - Number Verification
- AI layer turns raw trust signals into a clear operational recommendation.

## 3. Technical architecture

- React frontend with scenario controls, decision panel, live feed, and dashboard.
- FastAPI backend with transaction, fraud, verification, and showcase APIs.
- WebSocket updates for live demo movement.
- Integration mode switch:
  - `SIMULATION`
  - `AUTO`
  - `LIVE`

## 4. Business model and monetization

- B2B SaaS for mobile money providers, PSPs, and banks.
- Pricing can blend per-check API fees with seat-based dashboard access.
- Fraud savings, lower manual review load, and better customer trust drive ROI.

## 5. Demo evidence

- Guided 3-step showcase built into the UI.
- Deterministic scenarios for `BLOCK`, `FLAG_FOR_REVIEW`, and `APPROVE`.
- Live transaction feed and alert list show each decision in context.

## 6. Team bios and roles

- Founder / builder: product, backend, frontend, and demo orchestration.
- Mentor ask: refine operator workflow, partner positioning, and rollout assumptions.
