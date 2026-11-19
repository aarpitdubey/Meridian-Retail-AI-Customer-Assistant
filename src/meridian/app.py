from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .config import CASES_PATH, DEMO_OUTPUTS_PATH, POLICY_PATH, load_policy_text
from .euri_client import EuriClient, EuriError

load_dotenv()

VALID_STATUSES = frozenset({"ok", "unavailable"})
REQUIRED_KEY_BY_STATUS = {"ok": "draft", "unavailable": "reason"}
PAYLOAD_TYPE_BY_STATUS = {"ok": str, "unavailable": str}
VALID_DECISIONS = frozenset({"eligible_for_review", "not_eligible", "needs_more_info", "unavailable"})


def _require_object(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be a JSON object, got {type(value).__name__}.")
    return value


def _validate_demo_result(case_id: str, result: Any) -> dict[str, str]:
    entry = _require_object(result, f"Demo result for {case_id!r}")
    status = entry.get("status")
    if status not in VALID_STATUSES:
        raise ValueError(f"Demo result for {case_id!r} has invalid status {status!r}.")
    required_key = REQUIRED_KEY_BY_STATUS[status]
    if required_key not in entry:
        raise ValueError(f"Demo result for {case_id!r} with status {status!r} must include {required_key!r}.")
    payload = entry[required_key]
    expected_type = PAYLOAD_TYPE_BY_STATUS[status]
    if not isinstance(payload, expected_type) or not payload.strip():
        raise ValueError(f"Demo result for {case_id!r}: {required_key!r} must be a non-empty string.")
    extra = set(entry) - {"status", required_key}
    if extra:
        raise ValueError(f"Demo result for {case_id!r} has unexpected keys: {sorted(extra)}.")
    return {"status": status, required_key: payload.strip()}


def load_demo_results(path: Path = DEMO_OUTPUTS_PATH) -> dict[str, dict[str, str]]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise OSError(f"Could not read demo results from {path}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name} is not valid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno}).") from exc
    root = _require_object(data, f"Expected {path.name} to contain a JSON object")
    if not root:
        raise ValueError(f"{path.name} contains no cases.")
    return {case_id: _validate_demo_result(case_id, result) for case_id, result in root.items()}


def load_cases(path: Path = CASES_PATH) -> dict[str, dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise OSError(f"Could not read cases from {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name} is not valid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno}).") from exc
    cases = _require_object(raw, f"Expected {path.name} to contain a JSON object")
    if not cases:
        raise ValueError(f"{path.name} contains no cases.")
    for case_id, case in cases.items():
        _require_object(case, f"Case {case_id!r}")
        for key in ("case_id", "customer_question", "issue_status"):
            if not isinstance(case.get(key), str) or not case[key].strip():
                raise ValueError(f"Case {case_id!r} must have a non-empty {key!r}.")
    return cases


def _result(case_id: str, decision: str, policy_lines: list[str], draft: str, reason: str = "") -> dict[str, Any]:
    return {
        "case_id": case_id,
        "decision": decision,
        "policy_lines": policy_lines,
        "draft_reply": draft,
        "needs_human_review": True,
        "reason": reason,
    }


def _synthetic_result(case_id: str, case: dict[str, Any], demo: dict[str, str], policy_lines: list[str]) -> dict[str, Any]:
    status = demo["status"]
    if status == "unavailable":
        return _result(case_id, "unavailable", policy_lines, "", demo["reason"])
    draft = demo["draft"].strip()
    if not draft:
        return _result(case_id, "unavailable", policy_lines, "", "The configured demo draft is empty.")
    # A case remains a draft for human review; this tool never authorizes a transaction.
    decision = "needs_more_info" if case.get("delivery_date") is None else "eligible_for_review"
    return _result(case_id, decision, policy_lines, draft)


def run_case(case_id: str, *, offline_demo: bool = False, simulate_timeout: bool = False) -> dict[str, Any]:
    cases = load_cases()
    if case_id not in cases:
        raise KeyError(f"Unknown case {case_id!r}. Available cases: {', '.join(cases)}")
    case = cases[case_id]
    policy_lines = [line.strip() for line in load_policy_text().splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if simulate_timeout:
        return _result(case_id, "unavailable", policy_lines, "", "Simulated request timeout.")
    if offline_demo:
        demo_root = json.loads(DEMO_OUTPUTS_PATH.read_text(encoding="utf-8"))
        results = demo_root.get("results") if isinstance(demo_root, dict) else None
        if not isinstance(results, dict) or case_id not in results:
            raise ValueError(f"No offline demo result exists for {case_id!r}.")
        entry = _require_object(results[case_id], f"Demo result for {case_id!r}")
        draft = entry.get("draft_reply")
        if not isinstance(draft, str) or not draft.strip():
            raise ValueError(f"Offline demo result for {case_id!r} has no valid draft_reply.")
        missing = entry.get("missing_information", [])
        if not isinstance(missing, list) or any(not isinstance(item, str) for item in missing):
            raise ValueError(f"Offline demo result for {case_id!r} has invalid missing_information.")
        decision = "needs_more_info" if missing else ("not_eligible" if entry.get("review_status") == "BLOCKED" else "eligible_for_review")
        return _result(case_id, decision, policy_lines, draft)
    client = EuriClient.from_env()
    if not client.configured:
        return _result(case_id, "unavailable", policy_lines, "", "API key is not configured. Run python setup_env.py or use --offline-demo.")
    try:
        draft = client.draft(load_policy_text(), case)
    except EuriError as exc:
        return _result(case_id, "unavailable", policy_lines, "", str(exc))
    if not draft.strip():
        return _result(case_id, "unavailable", policy_lines, "", "The API returned an empty draft.")
    decision = "needs_more_info" if case.get("delivery_date") is None else "eligible_for_review"
    return _result(case_id, decision, policy_lines, draft.strip())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Draft a Meridian support reply for human review.")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--case", help="Case ID to process, for example C1.")
    selection.add_argument("--list-cases", action="store_true", help="List available case IDs and summaries.")
    parser.add_argument("--offline-demo", action="store_true", help="Use the prerecorded synthetic output; makes no network request.")
    parser.add_argument("--simulate-timeout", action="store_true", help="Print a safe unavailable result without making a request.")
    parser.add_argument("--format", choices=("json", "text"), default="json", help="Output format (default: json).")
    return parser


def _print_cases() -> None:
    for case_id, case in load_cases().items():
        question = " ".join(case["customer_question"].split())
        print(f"{case_id}: {case.get('product', 'Item')} | {question}")


def _print_text(result: dict[str, Any]) -> None:
    print(f"Case: {result['case_id']}")
    print(f"Decision: {result['decision']}")
    print("Human review required: yes")
    print("\nDraft reply:")
    print(result["draft_reply"] or "(No draft available.)")
    if result["reason"]:
        print(f"\nNote: {result['reason']}")
    print("\nPolicy references:")
    for line in result["policy_lines"]:
        print(f"  {line}")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.list_cases:
        try:
            _print_cases()
        except (OSError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        return 0
    if not args.case:
        parser.error("provide --case CASE_ID or --list-cases")
    if args.offline_demo and args.simulate_timeout:
        parser.error("--offline-demo and --simulate-timeout cannot be used together")
    try:
        result = run_case(args.case, offline_demo=args.offline_demo, simulate_timeout=args.simulate_timeout)
    except KeyError as exc:
        print(f"Error: {exc.args[0]}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    if args.format == "text":
        _print_text(result)
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["decision"] != "unavailable" else 1


if __name__ == "__main__":
    raise SystemExit(main())
