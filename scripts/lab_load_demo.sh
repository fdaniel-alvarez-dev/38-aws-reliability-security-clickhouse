#!/usr/bin/env bash
set -euo pipefail

cid="$(docker compose ps -q clickhouse)"
if [[ -z "${cid}" ]]; then
  echo "ClickHouse container is not running. Run: make lab-up"
  exit 1
fi

python3 pipelines/pipeline_demo.py >/dev/null

echo "Creating table and ingesting demo dataset..."
docker exec -i "${cid}" clickhouse-client --password "demo-password" --query "CREATE DATABASE IF NOT EXISTS demo"
docker exec -i "${cid}" clickhouse-client --password "demo-password" --query "CREATE TABLE IF NOT EXISTS demo.events (event_id UInt64, user_id UInt64, event_type String, event_ts String) ENGINE=MergeTree ORDER BY (event_type, event_id)"
docker exec -i "${cid}" clickhouse-client --password "demo-password" --query "TRUNCATE TABLE demo.events"
docker exec -i "${cid}" bash -lc 'cat /data/processed/events_jsonl/events.jsonl' | docker exec -i "${cid}" clickhouse-client --password "demo-password" --query "INSERT INTO demo.events FORMAT JSONEachRow"

echo "Ingest complete."
