"""
Pull public Kalshi market data and load it into BigQuery as raw JSON.

Creates three tables in the raw_kalshi dataset, each with two columns:
  loaded_at  TIMESTAMP  - when this script ran
  payload    STRING     - one API object (a series, event or market) as JSON text

Every run replaces the tables with a fresh snapshot. All parsing and renaming
happens later, in the dbt staging models.

Run from the repo root with the kalshi environment active:
    python ingest/load_kalshi.py
"""

import json
import time
from datetime import datetime, timedelta, timezone

import requests
from google.cloud import bigquery

# --- Settings ----------------------------------------------------------------

PROJECT_ID = "kalshi-explorer"
DATASET = "raw_kalshi"
LOCATION = "US"
BASE_URL = "https://external-api.kalshi.com/trade-api/v2"

LOOKBACK_DAYS = 3    # pull markets settled in the last N days
MAX_PAGES = 500      # safety cap per endpoint, so a bug can't loop forever


# --- Kalshi API --------------------------------------------------------------

def get_with_retry(url, params, attempts=5):
    """GET a URL, backing off and retrying if rate-limited (429) or on server errors."""
    for attempt in range(attempts):
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 429 or resp.status_code >= 500:
            wait = 2 ** attempt
            print(f"  got {resp.status_code}, retrying in {wait}s")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()  # still failing after all attempts: stop with the error
    return resp.json()


def fetch_all(path, key, params=None, page_size=1000):
    """Follow Kalshi's cursor pagination and return every item from an endpoint."""
    params = dict(params or {})
    if page_size:
        params["limit"] = page_size

    items, cursor, pages = [], None, 0
    while True:
        if cursor:
            params["cursor"] = cursor
        data = get_with_retry(f"{BASE_URL}{path}", params)
        batch = data.get(key) or []
        items.extend(batch)
        pages += 1
        print(f"  {path}: page {pages}, {len(items):,} rows so far")

        cursor = data.get("cursor")
        if not cursor or not batch or pages >= MAX_PAGES:
            break
        time.sleep(0.1)  # be polite to the API
    return items


# --- BigQuery ----------------------------------------------------------------

def load_raw(client, table, rows):
    """Replace a raw table with one row per API object, stored as JSON text."""
    loaded_at = datetime.now(timezone.utc).isoformat()
    records = [{"loaded_at": loaded_at, "payload": json.dumps(r)} for r in rows]

    table_id = f"{PROJECT_ID}.{DATASET}.{table}"
    job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("loaded_at", "TIMESTAMP"),
            bigquery.SchemaField("payload", "STRING"),
        ],
        write_disposition="WRITE_TRUNCATE",  # full refresh each run
    )
    client.load_table_from_json(records, table_id, job_config=job_config).result()
    print(f"Loaded {len(records):,} rows into {table_id}\n")


# --- Main --------------------------------------------------------------------

def main():
    client = bigquery.Client(project=PROJECT_ID)  # project named explicitly, not taken from gcloud's default

    dataset = bigquery.Dataset(f"{PROJECT_ID}.{DATASET}")
    dataset.location = LOCATION
    client.create_dataset(dataset, exists_ok=True)

    since = int((datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).timestamp())

    print("Fetching series...")
    series = fetch_all("/series", "series", page_size=None)
    load_raw(client, "series", series)

    print(f"Fetching events that closed in the last {LOOKBACK_DAYS} days...")
    events = fetch_all(
        "/events",
        "events",
        {"status": "settled", "min_close_ts": since},
        page_size=200,  # /events allows at most 200 per page
    )

    print(f"Fetching markets settled in the last {LOOKBACK_DAYS} days...")
    markets = fetch_all(
        "/markets",
        "markets",
        {"status": "settled", "min_settled_ts": since, "mve_filter": "exclude"},
    )

    # A market can settle while other markets in its event are still open, so its
    # event isn't "settled" yet and the /events call above misses it. Fetch those
    # events one by one so every market has its event (and therefore a category).
    have = {e["event_ticker"] for e in events}
    missing = sorted({m["event_ticker"] for m in markets} - have)
    print(f"Fetching {len(missing)} events for markets whose event hasn't fully settled...")
    for ticker in missing:
        events.append(get_with_retry(f"{BASE_URL}/events/{ticker}", {})["event"])
        time.sleep(0.1)

    load_raw(client, "events", events)
    load_raw(client, "markets", markets)

    print("Done.")


if __name__ == "__main__":
    main()