#!/usr/bin/env python3
"""
ForgeOps Lite — CLI entry point.

Usage:
  python cli.py "The ESB service is showing elevated latency around 18:10 UTC"
  python cli.py --scenario 1
  python cli.py --list-scenarios
"""
import argparse
import json
import sys
from pathlib import Path

from orchestrator.agent import investigate


def load_scenarios() -> list[dict]:
    path = Path(__file__).parent / "scenarios" / "scenarios.json"
    return json.loads(path.read_text())


def print_result(result: dict) -> None:
    print("\n" + "=" * 60)
    print("INVESTIGATION COMPLETE")
    print("=" * 60)

    print(f"\nTool calls made: {len(result['tool_calls'])}")
    for i, call in enumerate(result["tool_calls"], 1):
        print(f"  {i:>2}. {call['tool']}  →  {call['result_summary']}")

    print("\n" + "-" * 60)
    print("ROOT CAUSE ANALYSIS")
    print("-" * 60)
    print(result["rca"])

    if result.get("truncated"):
        print("\n[Warning: tool call limit reached — analysis may be incomplete]")


def main() -> None:
    parser = argparse.ArgumentParser(description="ForgeOps Lite incident investigator")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("query", nargs="?", help="Free-text incident description")
    group.add_argument("--scenario", type=int, metavar="N", help="Run pre-baked scenario N")
    group.add_argument("--list-scenarios", action="store_true", help="List available scenarios")
    parser.add_argument("--verbose", action="store_true", help="Print each tool call live")
    args = parser.parse_args()

    if args.list_scenarios:
        scenarios = load_scenarios()
        print(f"\n{len(scenarios)} pre-baked scenarios:\n")
        for s in scenarios:
            print(f"  [{s['id']}] {s['title']}")
            print(f"       {s['query']}\n")
        return

    if args.scenario is not None:
        scenarios = load_scenarios()
        match = next((s for s in scenarios if s["id"] == args.scenario), None)
        if match is None:
            print(f"Scenario {args.scenario} not found. Run --list-scenarios to see options.")
            sys.exit(1)
        query = match["query"]
        print(f"\nRunning scenario [{match['id']}]: {match['title']}")
    elif args.query:
        query = args.query
    else:
        query = input("Describe the incident: ").strip()
        if not query:
            print("No query provided.")
            sys.exit(1)

    print(f"\nInvestigating: {query}\n")
    result = investigate(query, verbose=args.verbose)
    print_result(result)


if __name__ == "__main__":
    main()
