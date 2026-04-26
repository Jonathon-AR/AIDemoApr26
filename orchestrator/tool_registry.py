"""
Defines the Claude tool schemas and dispatches calls to the tool layer.
"""
import json
from tools.fault_log      import get_fault_log
from tools.service_health import get_service_health
from tools.trace_tools    import get_error_summary, get_slow_traces, get_trace
from tools.node_metrics   import get_node_metrics, get_topology

# ---------------------------------------------------------------------------
# Tool schemas (Anthropic API format)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "get_fault_log",
        "description": (
            "Returns known fault incidents from the ground-truth incident log. "
            "All timestamps in output are UTC Unix milliseconds. "
            "Call this first to anchor the investigation to a specific fault window."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "fault_id": {
                    "type": "integer",
                    "description": "Optional. Return only this specific fault ID. Omit to return all faults.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_service_health",
        "description": (
            "Returns per-minute ESB business KPIs (success rate, avg latency, call volume) "
            "for a service in a time window. Flags anomalous buckets. "
            "Use this to confirm service degradation and find the exact degraded minute."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "ESB service identifier, e.g. 'osb_001'.",
                },
                "start_ts": {
                    "type": "integer",
                    "description": "Window start as Unix milliseconds (UTC).",
                },
                "end_ts": {
                    "type": "integer",
                    "description": "Window end as Unix milliseconds (UTC).",
                },
            },
            "required": ["service_name", "start_ts", "end_ts"],
        },
    },
    {
        "name": "get_error_summary",
        "description": (
            "Scans all trace files for failed spans in the time window. "
            "Groups failures by node (cmdb_id) and call type. "
            "Use this to identify which nodes are generating errors."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "start_ts": {
                    "type": "integer",
                    "description": "Window start as Unix milliseconds (UTC).",
                },
                "end_ts": {
                    "type": "integer",
                    "description": "Window end as Unix milliseconds (UTC).",
                },
                "cmdb_id": {
                    "type": "string",
                    "description": "Optional. Restrict scan to a specific node.",
                },
            },
            "required": ["start_ts", "end_ts"],
        },
    },
    {
        "name": "get_slow_traces",
        "description": (
            "Finds the slowest root-level OSB request traces above a latency threshold. "
            "Returns trace IDs you can drill into with get_trace. "
            "OSB spans are the entry point of the call chain."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "start_ts": {
                    "type": "integer",
                    "description": "Window start as Unix milliseconds (UTC).",
                },
                "end_ts": {
                    "type": "integer",
                    "description": "Window end as Unix milliseconds (UTC).",
                },
                "threshold_ms": {
                    "type": "number",
                    "description": "Minimum elapsed time in ms to include. Default 500.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return. Default 10.",
                },
            },
            "required": ["start_ts", "end_ts"],
        },
    },
    {
        "name": "get_trace",
        "description": (
            "Reconstructs the full span call tree for a single trace ID across all trace files. "
            "Shows the complete OSB → CSF → RemoteProcess → FlyRemote → LOCAL → JDBC chain. "
            "Use this to pinpoint which hop in the call chain is slow or failing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "trace_id": {
                    "type": "string",
                    "description": "The traceId to reconstruct.",
                }
            },
            "required": ["trace_id"],
        },
    },
    {
        "name": "get_node_metrics",
        "description": (
            "Returns infrastructure time-series metrics for a specific node. "
            "Supports OS hosts (CPU, disk, memory, network), Oracle DBs, Redis, and Docker containers. "
            "Use this to confirm resource-level root causes on suspect nodes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cmdb_id": {
                    "type": "string",
                    "description": "Node identifier, e.g. 'db_003', 'os_017', 'docker_008'.",
                },
                "metric_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Metrics to fetch, e.g. ['CPU_Used_Pct', 'AWS']. "
                        "Pass ['*'] to return all available metrics for this node."
                    ),
                },
                "start_ts": {
                    "type": "integer",
                    "description": "Window start as Unix milliseconds (UTC).",
                },
                "end_ts": {
                    "type": "integer",
                    "description": "Window end as Unix milliseconds (UTC).",
                },
            },
            "required": ["cmdb_id", "metric_names", "start_ts", "end_ts"],
        },
    },
    {
        "name": "get_topology",
        "description": (
            "Returns the service-to-node topology map: which Docker containers host which CSF services, "
            "which OS hosts which Redis instances, etc. "
            "Call this when you need to navigate from a service name to its underlying infrastructure node."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]

# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_DISPATCH = {
    "get_fault_log":      lambda args: get_fault_log(**args),
    "get_service_health": lambda args: get_service_health(**args),
    "get_error_summary":  lambda args: get_error_summary(**args),
    "get_slow_traces":    lambda args: get_slow_traces(**args),
    "get_trace":          lambda args: get_trace(**args),
    "get_node_metrics":   lambda args: get_node_metrics(**args),
    "get_topology":       lambda args: get_topology(),
}


def dispatch(tool_name: str, tool_input: dict) -> str:
    """
    Calls the tool function and returns the result as a JSON string.
    Returns a JSON error string if the tool name is unknown or the call raises.
    """
    fn = _DISPATCH.get(tool_name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
    try:
        result = fn(tool_input)
        return json.dumps(result, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})
