# AIDemoApr26

An IT operations monitoring dataset designed for **AIOps and root-cause analysis (RCA)** research. The dataset captures ~one day of telemetry (~May 25–26 2020 UTC) from a realistic microservices environment with injected faults.

## Dataset Overview

| Layer | Files | Description |
|---|---|---|
| Distributed traces | `call_chain_metrics/*.csv` | Span-level call records (JDBC, CSF, LOCAL, OSB, FlyRemote) — ~9M rows total |
| Business KPIs | `business_metrics/esb.csv` | Per-minute ESB success rate & response time — 378 rows |
| Infrastructure | `platform_metrics/*.csv` | CPU, memory, disk, network, DB, Redis metrics — ~595K rows |
| Ground truth | `data_release_v3.5/0_fault_description.xlsx` | Fault log with timestamps and affected nodes |

## Directory Structure

```
AIDemoApr26/
├── 2020_05_26/
│   ├── call_chain_metrics/
│   │   ├── trace_jdbc.csv          # 4.31M rows — JDBC database calls
│   │   ├── trace_csf.csv           # 828K rows  — CSF service RPC calls
│   │   ├── trace_local.csv         # 3.31M rows — In-process local calls
│   │   ├── trace_remote_process.csv# 828K rows  — Cross-process remote calls
│   │   ├── trace_osb.csv           # 165K rows  — Oracle Service Bus (root spans)
│   │   └── trace_fly_remote.csv    # 166K rows  — FlyRemote lightweight calls
│   ├── business_metrics/
│   │   └── esb.csv
│   └── platform_metrics/
│       ├── os_linux.csv            # 303K rows  — Linux host metrics
│       ├── db_oracle_11g.csv       # 172K rows  — Oracle DB metrics
│       ├── mw_redis.csv            # 95K rows   — Redis metrics
│       ├── dcos_docker.csv         # 24K rows   — Docker container metrics
│       └── dcos_container.csv      # 716 rows   — DCOS container health
└── data_release_v3.5/
    ├── 0_fault_description.xlsx
    ├── 1_application_deployment_architecture_list.xlsx
    ├── 1_data_field_list.xlsx
    ├── 2_database_metrics.xlsx
    ├── 2_operating_system_metrics.xlsx
    ├── 2_middleware_metrics.xlsx
    ├── 2_dcos_metrics.xlsx
    └── 2_business_metrics_description/
```

## Key Schema Concepts

**`cmdb_id`** — node identifier, present in every file. Prefix encodes node type:

| Prefix | Type |
|---|---|
| `os_NNN` | Linux OS host |
| `docker_NNN` | Docker container |
| `container_NNN` | DCOS container |
| `db_NNN` | Oracle 11g database |
| `redis_NNN` | Redis instance |

**Trace join keys:**
- `traceId` — links all spans of a single end-to-end request
- `id` / `pid` — span ID / parent span ID, reconstructs the call tree (DAG)

All timestamps are **Unix milliseconds**.

## Use Cases

- **Root-cause analysis** — correlate fault events from `0_fault_description.xlsx` with anomalies in platform and trace metrics
- **Anomaly detection** — detect degradation in `succee_rate` / `avg_time` in ESB KPIs
- **Call graph reconstruction** — group by `traceId`, build span trees via `id`/`pid`
- **Multimodal AIOps** — fuse trace, metric, and business signal streams for end-to-end RCA

## Documentation

See [INDEX.md](INDEX.md) for full column-level schema documentation across all files.
