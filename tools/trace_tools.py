"""
Trace-level queries across all call_chain_metrics CSVs.

Three tools:
  - get_error_summary  : failure counts grouped by node + call type
  - get_slow_traces    : slowest root-level OSB spans above a threshold
  - get_trace          : full reconstructed call tree for one traceId
"""
import pandas as pd
from config import TRACE_FILES

_cache: dict = {}

_BASE_COLS   = ["callType", "startTime", "elapsedTime", "success", "traceId", "id", "pid", "cmdb_id"]
_EXTRA_COLS  = {
    "osb":            ["serviceName"],
    "csf":            ["serviceName"],
    "remote_process": ["serviceName"],
    "fly_remote":     ["serviceName"],
    "local":          ["serviceName", "dsName"],
    "jdbc":           ["dsName"],
}


def _load(key: str) -> pd.DataFrame:
    if key not in _cache:
        extra = _EXTRA_COLS.get(key, [])
        _cache[key] = pd.read_csv(TRACE_FILES[key], usecols=_BASE_COLS + extra)
    return _cache[key]


# ---------------------------------------------------------------------------
# get_error_summary
# ---------------------------------------------------------------------------

def get_error_summary(start_ts: int, end_ts: int, cmdb_id: str | None = None) -> dict:
    """
    Scans all trace files for failed spans in the time window.

    Args:
        start_ts: Window start (Unix ms, UTC).
        end_ts:   Window end   (Unix ms, UTC).
        cmdb_id:  Optional — filter to a specific node.

    Returns:
        Dict with:
          - window_start / window_end
          - total_failures: int
          - by_node: list of {cmdb_id, call_type, failure_count, total_count, error_rate}
            sorted by failure_count desc
    """
    frames = []
    for key in TRACE_FILES:
        df = _load(key)
        mask = (df["startTime"] >= start_ts) & (df["startTime"] <= end_ts)
        if cmdb_id:
            mask &= df["cmdb_id"] == cmdb_id
        frames.append(df[mask][["callType", "cmdb_id", "success"]])

    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    if combined.empty:
        return {"window_start": start_ts, "window_end": end_ts, "total_failures": 0, "by_node": []}

    grouped = combined.groupby(["cmdb_id", "callType"]).agg(
        total_count=("success", "count"),
        failure_count=("success", lambda s: (s == False).sum()),  # noqa: E712
    ).reset_index()
    grouped = grouped[grouped["failure_count"] > 0].copy()
    grouped["error_rate"] = (grouped["failure_count"] / grouped["total_count"]).round(4)
    grouped = grouped.sort_values("failure_count", ascending=False)

    return {
        "window_start":  start_ts,
        "window_end":    end_ts,
        "total_failures": int(grouped["failure_count"].sum()),
        "by_node": [
            {
                "cmdb_id":       row["cmdb_id"],
                "call_type":     row["callType"],
                "failure_count": int(row["failure_count"]),
                "total_count":   int(row["total_count"]),
                "error_rate":    float(row["error_rate"]),
            }
            for _, row in grouped.iterrows()
        ],
    }


# ---------------------------------------------------------------------------
# get_slow_traces
# ---------------------------------------------------------------------------

def get_slow_traces(
    start_ts: int,
    end_ts: int,
    threshold_ms: float = 500.0,
    limit: int = 10,
) -> dict:
    """
    Finds the slowest root-level OSB spans (pid is None) above threshold_ms.

    Args:
        start_ts:     Window start (Unix ms, UTC).
        end_ts:       Window end   (Unix ms, UTC).
        threshold_ms: Minimum elapsedTime to include (default 500 ms).
        limit:        Max results to return (default 10).

    Returns:
        Dict with:
          - threshold_ms, limit
          - traces: list of {trace_id, elapsed_ms, start_ts, cmdb_id, service_name}
            sorted by elapsed_ms desc
    """
    osb = _load("osb")
    mask = (
        (osb["startTime"] >= start_ts)
        & (osb["startTime"] <= end_ts)
        & (osb["elapsedTime"] >= threshold_ms)
        & (osb["pid"].isna() | (osb["pid"] == "None"))
    )
    hits = osb[mask].nlargest(limit, "elapsedTime")

    return {
        "threshold_ms": threshold_ms,
        "limit":        limit,
        "traces": [
            {
                "trace_id":     row["traceId"],
                "elapsed_ms":   float(row["elapsedTime"]),
                "start_ts":     int(row["startTime"]),
                "cmdb_id":      row["cmdb_id"],
                "service_name": row.get("serviceName", None),
            }
            for _, row in hits.iterrows()
        ],
    }


# ---------------------------------------------------------------------------
# get_trace
# ---------------------------------------------------------------------------

def get_trace(trace_id: str) -> dict:
    """
    Reconstructs the full call tree for a single trace across all trace files.

    Args:
        trace_id: The traceId to look up.

    Returns:
        Dict with:
          - trace_id
          - total_spans: int
          - spans: list of span dicts sorted by startTime, each with:
              id, pid, call_type, cmdb_id, start_ts, elapsed_ms,
              success, service_name (if present), ds_name (if present)
          - critical_path: spans where success=False or elapsed_ms is in top 20%
    """
    spans = []
    for key in TRACE_FILES:
        df = _load(key)
        hits = df[df["traceId"] == trace_id]
        for _, row in hits.iterrows():
            span = {
                "id":           row["id"],
                "pid":          None if pd.isna(row["pid"]) or row["pid"] == "None" else row["pid"],
                "call_type":    row["callType"],
                "cmdb_id":      row["cmdb_id"],
                "start_ts":     int(row["startTime"]),
                "elapsed_ms":   float(row["elapsedTime"]),
                "success":      bool(row["success"]),
            }
            if "serviceName" in row.index and not pd.isna(row.get("serviceName")):
                span["service_name"] = row["serviceName"]
            if "dsName" in row.index and not pd.isna(row.get("dsName")):
                span["ds_name"] = row["dsName"]
            spans.append(span)

    if not spans:
        return {"trace_id": trace_id, "total_spans": 0, "spans": [], "critical_path": []}

    spans.sort(key=lambda s: s["start_ts"])

    elapsed_vals = [s["elapsed_ms"] for s in spans]
    p80 = sorted(elapsed_vals)[int(len(elapsed_vals) * 0.8)] if elapsed_vals else 0
    critical = [s for s in spans if not s["success"] or s["elapsed_ms"] >= p80]

    return {
        "trace_id":      trace_id,
        "total_spans":   len(spans),
        "spans":         spans,
        "critical_path": critical,
    }
