"""
Queries infrastructure metrics from platform_metrics CSVs.
Routes to the right file based on cmdb_id prefix.
"""
import pandas as pd
from config import PLATFORM_FILES

_cache: dict = {}

_PREFIX_MAP = {
    "os_":        "os",
    "db_":        "db",
    "redis_":     "redis",
    "docker_":    "docker",
    "container_": "container",
}


def _file_key(cmdb_id: str) -> str | None:
    for prefix, key in _PREFIX_MAP.items():
        if cmdb_id.startswith(prefix):
            return key
    return None


def _load(key: str) -> pd.DataFrame:
    if key not in _cache:
        _cache[key] = pd.read_csv(PLATFORM_FILES[key])
    return _cache[key]


def get_node_metrics(
    cmdb_id: str,
    metric_names: list[str],
    start_ts: int,
    end_ts: int,
) -> dict:
    """
    Returns time-series values for requested metrics on a specific node.

    Args:
        cmdb_id:      Node identifier, e.g. "db_003", "os_017", "docker_008".
        metric_names: List of metric names to fetch, e.g. ["CPU_Used_Pct", "AWS"].
                      Pass ["*"] to return all available metrics for the node.
        start_ts:     Window start (Unix ms, UTC).
        end_ts:       Window end   (Unix ms, UTC).

    Returns:
        Dict with:
          - cmdb_id, window_start, window_end
          - available_metrics: all metric names present for this node in the window
          - series: dict of metric_name → list of {timestamp_ms, value}
          - stats: dict of metric_name → {min, max, mean, latest}
    """
    key = _file_key(cmdb_id)
    if key is None:
        return {"error": f"Unknown cmdb_id prefix for '{cmdb_id}'"}

    df = _load(key)
    mask = (
        (df["cmdb_id"] == cmdb_id)
        & (df["timestamp"] >= start_ts)
        & (df["timestamp"] <= end_ts)
    )
    window = df[mask].copy()

    if window.empty:
        return {
            "cmdb_id":           cmdb_id,
            "window_start":      start_ts,
            "window_end":        end_ts,
            "available_metrics": [],
            "series":            {},
            "stats":             {},
        }

    available = sorted(window["name"].unique().tolist())

    targets = available if metric_names == ["*"] else [
        m for m in metric_names if m in available
    ]

    series: dict = {}
    stats:  dict = {}
    for metric in targets:
        rows = window[window["name"] == metric].sort_values("timestamp")
        points = [
            {"timestamp_ms": int(r["timestamp"]), "value": round(float(r["value"]), 6)}
            for _, r in rows.iterrows()
        ]
        series[metric] = points
        vals = [p["value"] for p in points]
        stats[metric] = {
            "min":    round(min(vals), 6),
            "max":    round(max(vals), 6),
            "mean":   round(sum(vals) / len(vals), 6),
            "latest": vals[-1] if vals else None,
        }

    missing = [m for m in metric_names if m != "*" and m not in available]

    return {
        "cmdb_id":           cmdb_id,
        "window_start":      start_ts,
        "window_end":        end_ts,
        "available_metrics": available,
        "series":            series,
        "stats":             stats,
        **({"missing_metrics": missing} if missing else {}),
    }


def get_topology() -> dict:
    """
    Returns the service-to-node topology from the architecture reference file.
    Useful for understanding which Docker containers run which CSF services,
    which OS hosts which Redis instances, etc.
    """
    import pandas as pd
    from config import ARCH_FILE

    df = pd.read_excel(ARCH_FILE)
    df.columns = ["category", "count", "host_os", "name", "container"]

    topology: dict[str, dict] = {}
    current_category = None

    for _, row in df.iterrows():
        if pd.notna(row["category"]):
            current_category = str(row["category"]).strip()
        name = str(row["name"]).strip() if pd.notna(row["name"]) else None
        if not name:
            continue
        topology[name] = {
            "type": current_category,
            "host_os":   str(row["host_os"]).strip() if pd.notna(row["host_os"]) else None,
            "container": str(row["container"]).strip() if pd.notna(row["container"]) else None,
        }

    return {"nodes": topology}
