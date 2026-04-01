# Hospital Bulk Processing System

A FastAPI service that accepts CSV uploads containing hospital records and pushes them into the [Hospital Directory API](https://hospital-directory.onrender.com/docs) in atomic batches.

## How it works

1. You upload a CSV file (columns: `name`, `address`, `phone`) to `POST /hospitals/bulk`.
2. The service validates the CSV, generates a unique batch ID, and creates each hospital via the upstream API.
3. If every row succeeds, the batch is activated (all hospitals go live at once). If any row fails, activation is skipped so you don't end up with a half-baked dataset.
4. You get back a JSON summary with the batch ID, per-row results, and timing info.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/hospitals/bulk` | Upload a CSV and process it |
| `GET` | `/hospitals/bulk/{batch_id}/status` | Poll batch progress |
| `POST` | `/hospitals/bulk/validate` | Dry-run CSV validation |
| `GET` | `/health` | Health check |

## Quick start (local)

```bash
# clone and cd into the repo
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# run the server
uvicorn app.main:app --reload
```

Then open http://localhost:8000/docs to play with the interactive Swagger UI.

### Try it with curl

```bash
curl -X POST http://localhost:8000/hospitals/bulk \
  -F "file=@sample.csv"
```

## Running with Docker

```bash
docker-compose up --build
```

The app will be available at http://localhost:8000.

## Running tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Tests mock the upstream API so they run fast and don't create real records.

## Deploying to Render

1. Push this repo to GitHub.
2. Create a new **Web Service** on Render pointing at the repo.
3. Set the build command to `pip install -r requirements.txt`.
4. Set the start command to `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
5. Add the environment variable `HOSPITAL_API_BASE=https://hospital-directory.onrender.com` (this is the default, but being explicit doesn't hurt).

## Project structure

```
├── app/
│   ├── main.py            # FastAPI app, middleware, health check
│   ├── config.py          # env-driven settings
│   ├── schemas.py         # pydantic models
│   ├── csv_parser.py      # CSV reading and validation
│   ├── hospital_client.py # async HTTP client for upstream API
│   ├── processor.py       # orchestration: fan-out, activate, track
│   └── routes.py          # endpoint definitions
├── tests/
│   ├── test_csv_parser.py # unit tests for parsing
│   └── test_api.py        # integration tests (mocked upstream)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── sample.csv
└── README.md
```

## Design decisions

**Why asyncio with a semaphore?** The upstream API is on a free Render tier, so hammering it with 20 concurrent requests would probably time out. The semaphore (default 5) keeps things moving without being rude.

**Why not celery / background tasks?** The spec says max 20 rows. At ~1-2 seconds per API call with concurrency=5, the whole thing finishes in under 10 seconds. Background processing adds complexity that isn't justified at this scale. The polling endpoint is there if you want to extend this later.

**Why in-memory batch storage?** The spec says in-memory is acceptable. For a production system you'd swap `batch_store` for Redis or a database — the interface is just a dict, so the change is trivial.

**Error handling approach**: If some rows fail, we don't activate the batch. This avoids partial state in the directory. The caller can inspect the per-row results, fix the CSV, and retry.
