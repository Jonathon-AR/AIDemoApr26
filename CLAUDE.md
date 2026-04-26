# AIDemoApr26

## What this repo is

IT operations monitoring dataset for **AIOps / root-cause analysis** research. Covers ~May 25–26 2020 UTC (Unix ms `1590422400000`–`1590443999000`).

The data simulates a realistic microservices environment with injected faults — the goal is root-cause analysis: given anomaly signals, identify which node/service caused them.

## Data layout

```
2020_05_26/
├── call_chain_metrics/   # Distributed trace spans (JDBC, CSF, LOCAL, OSB, etc.)
├── business_metrics/     # Aggregated ESB KPIs (success rate, avg response time)
└── platform_metrics/     # Infrastructure metrics (OS, DB, Redis, Docker, DCOS)

data_release_v3.5/        # Reference Excel files: fault labels, schema docs, architecture
```

Full schema reference: [INDEX.md](INDEX.md)

## Key concepts

- **`cmdb_id`** — identifies a node (e.g. `os_007`, `docker_003`, `db_009`). The primary join key across all files.
- **`traceId`** — links all spans of one end-to-end request across trace files.
- **`id` / `pid`** — span ID / parent span ID; reconstructs the call tree within a trace.
- **`0_fault_description.xlsx`** — ground-truth fault labels (timestamps + affected nodes). Use this as the target for RCA tasks.

## Common tasks

- **Root-cause analysis**: join fault timestamps from `0_fault_description.xlsx` against platform/trace metrics to find anomalous nodes.
- **Trace reconstruction**: group by `traceId`, sort by `startTime`, use `id`/`pid` to build the call DAG.
- **Service degradation detection**: monitor `succee_rate` and `avg_time` in `esb.csv` around fault windows.

## Notes

- All timestamps are Unix milliseconds.
- `succee_num` / `succee_rate` are intentional typos in the source data — keep as-is.
- `trace_osb.csv` rows always have `pid = None` (OSB is the entry point / root span).
