# 38-aws-reliability-security

A reference data platform blueprint with pragmatic governance: quality checks, lineage, access controls, and CI for data assets.

## The top pains this repo addresses
1) Replacing manual, risky changes with automated delivery—repeatable infrastructure, safe deployments, and drift-free environments (IaC + CI/CD + GitOps).
2) Designing a resilient, scalable cloud platform foundation—Kubernetes/container orchestration, networking, and standard patterns teams can reuse.
3) Building a data platform people trust—reliable pipelines, clear ownership, data quality checks, and governance that scales without slowing delivery.

## Quick demo (local)
```bash
make setup
make demo
make test
```

What you get:
- a tiny ETL pipeline (CSV → Parquet)
- schema validation with `pandera`
- a basic “trust contract” (docs + tests + CI)
