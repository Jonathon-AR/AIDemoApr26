"""
ForgeOps investigation agent.
Runs a Claude function-calling loop until the model produces a final RCA.
"""
import os
import json
import anthropic
from dotenv import load_dotenv
from config import DEFAULT_MODEL, MAX_TOOL_ROUNDS

load_dotenv()
from orchestrator.tool_registry import TOOLS, dispatch

_SYSTEM_PROMPT = """\
You are ForgeOps, an AI site reliability engineer. Your job is to investigate production incidents \
by calling tools that query real telemetry data, then produce a grounded root cause analysis.

## Platform overview
- Entry point: osb_001 (Oracle Service Bus / ESB)
- App services: csf_001 – csf_005 (CSF service framework)
- Databases: db_001 – db_013 (Oracle 11g)
- Middleware: redis_001 – redis_012
- Docker containers: docker_001 – docker_008
- OS hosts: os_001 – os_022

## Call chain order (top → bottom)
OSB → CSF → RemoteProcess → FlyRemote → LOCAL → JDBC → DB

## All timestamps are Unix milliseconds (UTC). The telemetry window is:
  Start: 1590422400000  (2020-05-25 16:00:00 UTC)
  End:   1590443975307  (2020-05-25 21:59:35 UTC)

## Investigation strategy
1. Call get_fault_log() to find known incident windows and their UTC timestamps.
2. Call get_service_health() on osb_001 for the incident window to confirm degradation.
3. Call get_error_summary() for the same window to identify failing nodes.
4. Call get_slow_traces() to get representative trace IDs.
5. Call get_trace() on 1–2 traces to see where in the chain latency/failures originate.
6. Call get_node_metrics() on the suspect node (db, os, redis, docker) to confirm resource issues.
7. Call get_topology() if you need to map a service name to its underlying node.

## Output format
When you have enough evidence, respond with a structured report:

**Root Cause:** (1–2 sentences)

**Affected Components:** (comma-separated list of cmdb_ids)

**Evidence:**
- Finding 1
- Finding 2
- ...

**Suggested Remediation:** (1–3 actionable steps)

Do not guess. Every claim in the RCA must be supported by data from a tool call.
"""


def investigate(query: str, verbose: bool = False) -> dict:
    """
    Runs the investigation loop for a given incident query.

    Args:
        query:   Natural-language description of the incident.
        verbose: If True, prints each tool call and result to stdout.

    Returns:
        Dict with keys:
          - rca:        Final RCA text from the model.
          - tool_calls: Ordered list of {tool, input, result_summary} dicts.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    messages = [{"role": "user", "content": query}]
    tool_calls_log: list[dict] = []

    for round_num in range(MAX_TOOL_ROUNDS):
        response = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if verbose:
            print(f"\n[Round {round_num + 1}] stop_reason={response.stop_reason}")

        if response.stop_reason == "end_turn":
            rca_text = next(
                (b.text for b in response.content if b.type == "text"), ""
            )
            return {"rca": rca_text, "tool_calls": tool_calls_log}

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type != "tool_use":
                    continue

                result_json = dispatch(block.name, block.input)
                result_data = json.loads(result_json)

                tool_calls_log.append({
                    "tool":           block.name,
                    "input":          block.input,
                    "result_summary": _summarise(result_data),
                })

                if verbose:
                    print(f"  → {block.name}({json.dumps(block.input, separators=(',', ':'))})")
                    print(f"     {_summarise(result_data)}")

                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": block.id,
                    "content":     result_json,
                })

            messages.append({"role": "user", "content": tool_results})

    # Exceeded max rounds — ask for a partial conclusion
    messages.append({
        "role": "user",
        "content": "You have reached the tool call limit. Summarise your findings so far as an RCA.",
    })
    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
        messages=messages,
    )
    rca_text = next((b.text for b in response.content if b.type == "text"), "")
    return {"rca": rca_text, "tool_calls": tool_calls_log, "truncated": True}


def _summarise(result: dict) -> str:
    """One-line summary of a tool result for verbose logging."""
    if "error" in result:
        return f"ERROR: {result['error']}"
    if "total_failures" in result:
        return f"{result['total_failures']} failures across {len(result['by_node'])} node/call-type pairs"
    if "summary" in result and result["summary"]:
        s = result["summary"]
        return f"success_rate={s.get('overall_success_rate')} peak_latency={s.get('peak_avg_time_ms')}ms"
    if "total_spans" in result:
        return f"{result['total_spans']} spans, {len(result['critical_path'])} on critical path"
    if "traces" in result:
        return f"{len(result['traces'])} slow traces found"
    if "stats" in result:
        metrics = list(result["stats"].keys())
        return f"metrics: {', '.join(metrics[:4])}"
    if "nodes" in result:
        return f"{len(result['nodes'])} topology nodes"
    if isinstance(result, list):
        return f"{len(result)} fault entries"
    return str(result)[:120]
