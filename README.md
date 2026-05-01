# SimGuard

SimGuard is a prototype-stage fraud prevention platform for African mobile money agents. It combines Nokia CAMARA trust signals with deterministic or live AI decisioning to help agents decide whether to approve, flag, or block a transaction in real time.

## Why this prototype fits the hackathon

- Theme: Financial Inclusion, Secure Payments & Anti-Fraud
- CAMARA APIs surfaced in the workflow: SIM Swap, Device Swap, Number Verification
- Bonus layer: agentic AI decisioning with a reliable simulation fallback
- Prototype format covered: live demo, architecture story, business model, screenshots/video notes, and team positioning docs under `docs/`

## Demo modes

SimGuard now supports:

- `SIMULATION`: default and recommended for judging; all showcase scenarios are deterministic
- `AUTO`: attempts live Nokia or Anthropic integrations, then falls back safely
- `LIVE`: prefers live integrations when configured

Set this in `.env` with:

```env
INTEGRATION_MODE=SIMULATION
```

## Guided demo scenarios

The UI and backend expose three repeatable scenarios:

- `block_sim_swap`: salary-day SIM swap drain attempt
- `flag_device_takeover`: suspicious device change before withdrawal
- `approve_verified_customer`: clean returning customer

For a fast judged demo:

1. Open the app.
2. Click `Run 3-step showcase`.
3. Watch the result panel, signal cards, live feed, and alert feed update.
4. Call out the `source` badges to explain simulation versus live provenance.

## Architecture

```text
React/Vite prototype surface
  -> Guided scenarios
  -> Agent transaction check
  -> Live feed and risk dashboard

FastAPI backend
  -> Transactions API
  -> Fraud quick check API
  -> Verification API
  -> Demo/showcase API
  -> WebSocket broadcast channel

Decision services
  -> CAMARA trust signal adapter
  -> Risk scoring engine
  -> AI decision engine with deterministic fallback

Storage
  -> SQLite in local prototype mode
```

## Local run

### Backend

```bash
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

Recomended:
cd backend
C:\Users\Thando\AppData\Local\Programs\Python\Python312\python.exe -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
pip install fastapi uvicorn sqlalchemy pydantic pydantic-settings python-dotenv httpx
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on [http://localhost:5173](http://localhost:5173) and proxies API traffic to port `8000`.

## Main API surfaces

- `POST /api/transactions`
- `GET /api/transactions`
- `POST /api/fraud/check`
- `GET /api/verification/full-check/{phone}`
- `GET /api/demo/scenarios`
- `POST /api/demo/run-scenario/{scenario_id}`
- `POST /api/demo/showcase`
- `POST /api/demo/reset`
- `WS /ws/alerts`

## Submission assets

Supporting prototype-round materials live in `docs/`:

- `prototype-deck.md`
- `api-usage-synopsis.md`
- `commercial-summary.md`
- `judge-script.md`
- `demo-evidence.md`

## Recommended judging script

- Start in `SIMULATION` mode for certainty.
- Run the 3-step showcase.
- Explain how each transaction uses telecom trust signals before money moves.
- Point out how the same contract supports `AUTO` or `LIVE` mode when keys are configured.
- Close on scalability: mobile money agents, PSPs, and MNO fraud teams can all consume the same decision surface.
