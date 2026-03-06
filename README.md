# 38-aws-reliability-security-clickhouse

A portfolio-grade **ClickHouse reliability and security** toolkit:
deterministic offline demos, operational guardrails, and production-safe validation paths.

## The top pains this repo addresses
1) Keeping analytical databases dependable: safe schemas, predictable ingest, and fast failure detection.
2) Reducing operational risk: repeatable drills and guardrails instead of “run it and hope”.
3) Enforcing security and governance without blocking delivery: explicit validation modes and clean documentation.

## Quick demo (local)
```bash
make demo-offline
make test-demo
```

What you get:
- offline demo data conversion to `JSONEachRow`-friendly output
- deterministic guardrails report (`artifacts/clickhouse_guardrails.json`)
- explicit `TEST_MODE=demo|production` tests with safe production gating

## Local ClickHouse lab (optional)
If you have Docker available, you can run a local ClickHouse server and ingest the demo dataset:

```bash
make lab-up
make lab-load-demo
make lab-query
make lab-down
```

## Tests (two explicit modes)

- `TEST_MODE=demo` (default): offline-only checks, deterministic artifacts
- `TEST_MODE=production`: real integrations (requires explicit opt-in + configuration)

Run production mode:

```bash
make test-production
```

Production integration options:
- Set `CLICKHOUSE_HTTP_URL` (example: `http://localhost:8123`) to run a real `/ping` + `SELECT 1` check.
- Optional write validation: set `CLICKHOUSE_WRITE_TESTS=1` and `CLICKHOUSE_TEST_DB` to run an isolated ingest/query drill.
- Or set `TERRAFORM_VALIDATE=1` to validate the included Terraform example (requires `terraform`).

## Sponsorship and contact

Sponsored by:
CloudForgeLabs  
https://cloudforgelabs.ainextstudios.com/  
support@ainextstudios.com

Built by:
Freddy D. Alvarez  
https://www.linkedin.com/in/freddy-daniel-alvarez/

For job opportunities, contact:
it.freddy.alvarez@gmail.com

## License

Personal, educational, and non-commercial use is free. Commercial use requires paid permission.
See `LICENSE` and `COMMERCIAL_LICENSE.md`.
