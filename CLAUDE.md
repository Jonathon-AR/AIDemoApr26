# AIDemoApr26 — Dataset Index

## Overview

IT operations monitoring dataset for **AIOps / root-cause analysis** research.
Covers approximately **one day of telemetry** (Unix ms range `1590422400000`–`1590443999000`, i.e. ~May 25–26 2020 UTC).
Data is split into raw time-series CSVs (`2020_05_26/`) and reference/documentation Excel files (`data_release_v3.5/`).

---

## Directory Structure

```
AIDemoApr26/
├── 2020_05_26/                          # Raw time-series data
│   ├── call_chain_metrics/              # Distributed trace spans (per call type)
│   ├── business_metrics/               # Aggregated ESB service KPIs
│   └── platform_metrics/               # Infrastructure resource metrics
└── data_release_v3.5/                  # Reference Excel files (schema, labels, architecture)
```

---

## CMDB Node ID Conventions

All CSVs reference infrastructure nodes via `cmdb_id`. The prefix encodes the node type:

| Prefix       | Node Type                   | Examples                        |
|--------------|-----------------------------|---------------------------------|
| `os_NNN`     | Linux OS host               | `os_007`, `os_021`              |
| `docker_NNN` | Docker container            | `docker_003`, `docker_008`      |
| `container_NNN` | DCOS container           | `container_001`, `container_002`|
| `db_NNN`     | Oracle 11g database         | `db_003`, `db_007`, `db_009`    |
| `redis_NNN`  | Redis middleware instance   | `redis_003`, `redis_009`        |

---

## `2020_05_26/call_chain_metrics/` — Distributed Trace Spans

All trace files share a **common base schema** plus call-type-specific extra columns.

### Shared Columns

| Column        | Type    | Description                                                        | Sample Value              |
|---------------|---------|--------------------------------------------------------------------|---------------------------|
| `callType`    | string  | Category of call (matches filename)                                | `JDBC`, `CSF`, `LOCAL`    |
| `startTime`   | int     | Span start time (Unix milliseconds)                                | `1590422400102`           |
| `elapsedTime` | float   | Duration of the span in **milliseconds**                           | `3.0`, `2171.0`           |
| `success`     | bool    | Whether the call succeeded                                         | `True`, `False`           |
| `traceId`     | string  | End-to-end trace identifier (links all spans of one request)       | `fe17145f6943534247dd`    |
| `id`          | string  | Unique ID for this individual span                                 | `fe1716b11331366647dd`    |
| `pid`         | string  | Parent span ID (forms the call tree; `None` = root span)          | `fe1713df1601365647dd`    |
| `cmdb_id`     | string  | Node where this span executed                                      | `docker_008`, `os_021`    |

### Per-File Extra Columns & Row Counts

| File                     | Extra Columns                       | Rows (~) | Notes                                         |
|--------------------------|-------------------------------------|----------|-----------------------------------------------|
| `trace_jdbc.csv`         | `dsName` — target DB node           | 4.31 M   | JDBC database calls; dsName e.g. `db_003`     |
| `trace_csf.csv`          | `serviceName` — CSF service called  | 828 K    | CSF service framework RPC calls; 5 services   |
| `trace_local.csv`        | `serviceName`, `dsName`             | 3.31 M   | In-process local method calls with DB context |
| `trace_remote_process.csv` | `serviceName`                     | 828 K    | Cross-process remote calls                    |
| `trace_osb.csv`          | `serviceName`                       | 165 K    | Oracle Service Bus calls; pid is always `None`|
| `trace_fly_remote.csv`   | `serviceName`                       | 166 K    | "FlyRemote" lightweight remote calls          |

**Sample row (`trace_jdbc.csv`):**
```
JDBC,1590422400102,2.0,True,fe17145f6943534247dd,fe1716b11331366647dd,fe1713df1601365647dd,docker_008,db_003
```

**Known services:**
- CSF: `csf_001` – `csf_005`
- OSB / ESB: `osb_001`
- FlyRemote: `fly_remote_001`
- Local methods: `local_method_011` (and others)

---

## `2020_05_26/business_metrics/` — Business KPIs

### `esb.csv` — ESB Service Aggregated Metrics
**Granularity:** 1-minute buckets. **Rows:** 378 (6 hours of data for one service).

| Column       | Type   | Description                                                   | Sample Value      |
|--------------|--------|---------------------------------------------------------------|-------------------|
| `serviceName`| string | ESB service identifier                                        | `osb_001`         |
| `startTime`  | int    | Bucket start time (Unix milliseconds)                         | `1590422400000`   |
| `avg_time`   | float  | Average response time for calls in this minute (ms)           | `0.6224`          |
| `num`        | int    | Total number of calls in this minute                          | `340`             |
| `succee_num` | int    | Number of successful calls                                    | `340`             |
| `succee_rate`| float  | Success rate (0.0–1.0)                                        | `1.0`             |

**Sample row:**
```
osb_001,1590422400000,0.6224,340,340,1.0
```

---

## `2020_05_26/platform_metrics/` — Infrastructure Metrics

All five platform files share the **same schema** (narrow/long format — one row per metric per node per timestamp):

| Column     | Type   | Description                                                                 | Sample Value              |
|------------|--------|-----------------------------------------------------------------------------|---------------------------|
| `itemid`   | int    | Unique monitoring item ID (maps to a specific metric on a specific node)    | `999999996487800`         |
| `name`     | string | Metric name (see per-file lists below)                                      | `CPU_util_pct`            |
| `bomc_id`  | string | BOMC monitoring point ID (`ZJ-XXX-NNN` format)                              | `ZJ-001-074`              |
| `timestamp`| int    | Measurement time (Unix milliseconds)                                        | `1590422400000`           |
| `value`    | float  | Metric value (units depend on metric name — see below)                      | `0.125978`                |
| `cmdb_id`  | string | Node this measurement belongs to                                            | `os_010`                  |

### `os_linux.csv` — Linux OS Host Metrics (~303 K rows)

Key metric names observed:

| Metric Name              | Description                              |
|--------------------------|------------------------------------------|
| `CPU_util_pct`           | CPU utilisation %                        |
| `CPU_idle_pct`           | CPU idle %                               |
| `CPU_user_time`          | CPU time in user space                   |
| `CPU_system_time`        | CPU time in kernel space                 |
| `CPU_iowait_time`        | CPU time waiting on I/O                  |
| `Disk_io_util`           | Disk I/O utilisation %                   |
| `Disk_rd_ios` / `Disk_wr_ios` | Disk read/write IOPS               |
| `Disk_rd_kbs`            | Disk read throughput (KB/s)              |
| `Disk_await` / `Disk_svctm` | Disk avg wait / service time (ms)   |
| `Disk_avgqu_sz`          | Disk average queue size                  |
| `Incoming_network_traffic` | Inbound network bytes                  |
| `Sent_errors_packets`    | Outbound error packet count              |
| `Buffers_used` / `Cache_used` | Memory buffer/cache usage          |
| `Agent_ping`             | Monitoring agent heartbeat               |

### `db_oracle_11g.csv` — Oracle Database Metrics (~172 K rows)

Key metric names observed:

| Metric Name          | Description                                        |
|----------------------|----------------------------------------------------|
| `CPU_free_pct`       | CPU free %                                         |
| `CPU_Used_Pct`       | CPU used %                                         |
| `MEM_real_util`      | Memory real utilisation %                          |
| `DbTime`             | Oracle DB Time stat                                |
| `Exec_Per_Sec`       | SQL executions per second                          |
| `Call_Per_Sec`       | DB calls per second                                |
| `Logic_Read_Per_Sec` | Logical reads per second                           |
| `Login_Per_Sec`      | Logins per second                                  |
| `ACS` / `AIOS`       | Oracle internal stats (Active Call/IO Sessions)    |
| `AWS`                | Oracle Active Wait Sessions                        |
| `Hang`               | Hang detection flag                                |
| `Asm_Free_Tb`        | ASM disk group free space (TB)                     |

### `mw_redis.csv` — Redis Middleware Metrics (~95 K rows)

Key metric names observed:

| Metric Name                  | Description                                    |
|------------------------------|------------------------------------------------|
| `redis_ping`                 | Ping response (1 = alive)                      |
| `redis_load`                 | Redis server load                              |
| `connected_clients`          | Current client connections                     |
| `blocked_clients`            | Clients blocked on BLPOP/BRPOP etc.            |
| `maxmemory`                  | Configured max memory (bytes)                  |
| `mem_fragmentation_ratio`    | Memory fragmentation ratio                     |
| `instantaneous_ops_per_sec`  | Commands processed per second                  |
| `instantaneous_input_kbps`   | Input bandwidth (KB/s)                         |
| `instantaneous_output_kbps`  | Output bandwidth (KB/s)                        |
| `keyspace_hits` / `keyspace_misses` | Cache hit/miss counts                 |
| `evicted_keys` / `expired_keys`     | Key eviction and expiry counts        |
| `rejected_connections`       | Connections rejected due to max limit          |
| `Redis_key_count`            | Total number of keys in keyspace               |

### `dcos_docker.csv` — Docker Container Metrics (~24 K rows)

| Metric Name                | Description                                      |
|----------------------------|--------------------------------------------------|
| `container_cpu_used`       | Container CPU used %                             |
| `container_mem_used`       | Container memory used (MB or %)                  |
| `container_thread_total`   | Total threads in container JVM                   |
| `container_thread_running` | Running threads                                  |
| `container_thread_idle`    | Idle threads                                     |
| `container_thread_used_pct`| Thread pool utilisation %                        |
| `container_session_used`   | Active HTTP/DB sessions                          |
| `container_fgc`            | Full GC count (JVM)                              |
| `container_fgct`           | Full GC cumulative time (JVM, ms)                |

### `dcos_container.csv` — DCOS Container Health (~716 rows)~

| Metric Name              | Description                                        |
|--------------------------|----------------------------------------------------|
| `container_fail_percent` | Container failure rate (0.0–1.0)                   |

---

## `data_release_v3.5/` — Reference & Documentation Files

| File                                          | Contents                                                                                      |
|-----------------------------------------------|-----------------------------------------------------------------------------------------------|
| `0_fault_description.xlsx`                    | **Fault/incident log** — ground-truth labels for anomalies; links faults to timestamps/nodes |
| `1_application_deployment_architecture_list.xlsx` | Inventory of deployed applications and their infra topology                              |
| `1_data_field_list.xlsx`                      | Data dictionary — field names, types, descriptions across all files                          |
| `2_database_metrics.xlsx`                     | Reference descriptions for all Oracle DB metric names                                        |
| `2_operating_system_metrics.xlsx`             | Reference descriptions for all OS metric names                                               |
| `2_middleware_metrics.xlsx`                   | Reference descriptions for all Redis metric names                                            |
| `2_dcos_metrics.xlsx`                         | Reference descriptions for all Docker/DCOS container metric names                            |
| `2_business_metrics_description/`             | Reference descriptions for ESB/OSB business KPI metrics                                      |

---

## Key Relationships

```
fault event (0_fault_description.xlsx)
    └── timestamp + cmdb_id
            ├── platform_metrics/    → resource signals (CPU, mem, disk, etc.)
            ├── business_metrics/    → service degradation signals (success_rate, avg_time)
            └── call_chain_metrics/  → span-level traces (latency, failures, call tree)
                    traceId links spans across: OSB → CSF → RemoteProcess → FlyRemote → LOCAL → JDBC
```

The `traceId` field is the primary join key for reconstructing full request call trees across all trace files. The `id`/`pid` parent-child relationship within a trace reconstructs the span tree (DAG).
