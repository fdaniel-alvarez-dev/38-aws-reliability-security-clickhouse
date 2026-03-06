#!/usr/bin/env bash
set -euo pipefail

cid="$(docker compose ps -q clickhouse)"
if [[ -z "${cid}" ]]; then
  echo "ClickHouse container is not running. Run: make lab-up"
  exit 1
fi

echo "Row count:"
docker exec -i "${cid}" clickhouse-client --password "demo-password" --query "SELECT count() FROM demo.events"

echo
echo "Event types:"
docker exec -i "${cid}" clickhouse-client --password "demo-password" --query "SELECT event_type, count() AS c FROM demo.events GROUP BY event_type ORDER BY c DESC"
