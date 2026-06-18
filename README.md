# Visit Tracker 

A small web service that receives shop visit events from a physical device, tracks per-customer visits and trees planted, and exposes a dashboard with hourly visit aggregation.

## How to run

### Local development

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

- Dashboard: http://localhost:8000
- API docs (Swagger): http://localhost:8000/docs

### Docker

```bash
docker compose up --build
```

### Tests

```bash
pytest -v
```

### Seed dummy data

With the server running, populate the in-memory store with sample visits for the dashboard:

```bash
python scripts/seed_dummy_data.py
```

The script posts visit events via the API, spreads them across the last 24 hours, and assigns each customer a random `visits_per_tree` between 3 and 10.

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `--base-url` | `http://localhost:8000` | URL of the running service |
| `--customers` | `12` | Number of distinct customers |
| `--hours` | `24` | Hours of history to fill (matches dashboard window) |
| `--min-visits-per-hour` | `0` | Minimum visits per hour bucket |
| `--max-visits-per-hour` | `8` | Maximum visits per hour bucket |
| `--seed` | `42` | Random seed for reproducible data |

Example with a heavier load:

```bash
python scripts/seed_dummy_data.py --customers 20 --max-visits-per-hour 15
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VISITS_PER_TREE` | `5` | Number of visits required to plant one tree (X) |
| `PORT` | `8000` | Used by Docker/local run scripts |

## Assumptions

- The device provides a `customer_id` with each visit event; there is no authentication in this version.
- If `timestamp` is omitted, the server uses the current UTC time.
- Hourly aggregation buckets use UTC.
- `VISITS_PER_TREE` is read at startup; changing it does not retroactively recalculate existing tree counts.
- Each event counts as one visit (no deduplication or debouncing).
- Data is stored in memory and is lost when the process restarts.

## API usage

### Record a visit (device → service)

```bash
curl -X POST http://localhost:8000/api/visits \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "cust-123", "timestamp": "2025-06-18T14:32:00Z"}'
```

Response (`201`):

```json
{
  "customer_id": "cust-123",
  "total_visits": 5,
  "trees_planted": 1,
  "last_connection_at": "2025-06-18T14:32:00Z",
  "tree_just_planted": true
}
```

### Get customer stats

```bash
curl http://localhost:8000/api/customers/cust-123
```

### Get hourly visit aggregation (dashboard)

```bash
curl "http://localhost:8000/api/stats/hourly?hours=24"
```

Returns one bucket per hour in the window, including hours with zero visits.

### Get configuration

```bash
curl http://localhost:8000/api/config
```

## Project structure

```
app/           FastAPI backend
scripts/       Utilities (e.g. seed_dummy_data.py)
static/        Frontend dashboard
tests/         pytest suite
DECISIONS.md   Technical choices and architecture notes
```
