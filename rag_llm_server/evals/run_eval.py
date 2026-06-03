import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import app  # noqa: E402


def load_cases(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def group_passed(answer: str, group: list[str]) -> bool:
    return any(term in answer for term in group)


def evaluate_answer(case: dict, trace: dict) -> dict:
    answer = trace.get("llm", {}).get("answer", "") or ""
    rag = trace.get("rag", {}) or {}

    required_results = []
    for group in case.get("required_any_groups", []):
        required_results.append(
            {
                "terms": group,
                "passed": group_passed(answer, group),
            }
        )

    forbidden_hits = [
        term for term in case.get("forbidden_terms", []) if term and term in answer
    ]

    checks = {
        "answer_not_empty": bool(answer.strip()),
        "rag_success": rag.get("status") == "success",
        "rag_has_items": (rag.get("item_count") or 0) > 0,
        "required_terms_passed": all(item["passed"] for item in required_results),
        "forbidden_terms_absent": not forbidden_hits,
    }

    passed = all(checks.values())
    return {
        "passed": passed,
        "checks": checks,
        "required_results": required_results,
        "forbidden_hits": forbidden_hits,
    }


def run_case(client: TestClient, case: dict) -> dict:
    started = time.time()
    response = client.post(
        "/debug/chat/full",
        json={"history": [], "question": case["question"]},
    )
    duration_ms = round((time.time() - started) * 1000, 2)
    response.raise_for_status()
    trace = response.json()
    eval_result = evaluate_answer(case, trace)

    return {
        "id": case["id"],
        "category": case.get("category"),
        "question": case["question"],
        "expected_behavior": case.get("expected_behavior"),
        "passed": eval_result["passed"],
        "checks": eval_result["checks"],
        "required_results": eval_result["required_results"],
        "forbidden_hits": eval_result["forbidden_hits"],
        "answer": trace.get("llm", {}).get("answer", ""),
        "rag": {
            "status": trace.get("rag", {}).get("status"),
            "item_count": trace.get("rag", {}).get("item_count"),
            "used_blocks": trace.get("rag", {}).get("used_blocks"),
            "context_length": trace.get("rag", {}).get("context_length"),
            "duration_ms": trace.get("rag", {}).get("duration_ms"),
        },
        "llm": {
            "first_token_ms": trace.get("llm", {}).get("first_token_ms"),
            "duration_ms": trace.get("llm", {}).get("duration_ms"),
            "chunk_count": trace.get("llm", {}).get("chunk_count"),
            "usage": trace.get("llm", {}).get("usage"),
        },
        "total_duration_ms": trace.get("total_duration_ms", duration_ms),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run RAG/LLM evaluation cases.")
    parser.add_argument(
        "--cases",
        default=str(ROOT / "evals" / "eval_cases.json"),
        help="Path to eval case JSON.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Run only first N cases.")
    parser.add_argument("--case-id", default=None, help="Run one specific case id.")
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "outputs" / "evals"),
        help="Directory for JSON reports. This path is gitignored.",
    )
    args = parser.parse_args()

    cases = load_cases(Path(args.cases))
    if args.case_id:
        cases = [case for case in cases if case["id"] == args.case_id]
        if not cases:
            raise SystemExit(f"case not found: {args.case_id}")
    if args.limit:
        cases = cases[: args.limit]

    client = TestClient(app)
    results = []
    print(f"[eval] running {len(cases)} case(s)")
    for index, case in enumerate(cases, start=1):
        print(f"[eval] {index}/{len(cases)} {case['id']} - {case['question']}")
        result = run_case(client, case)
        results.append(result)
        mark = "PASS" if result["passed"] else "FAIL"
        print(
            f"[eval] {mark} rag_items={result['rag']['item_count']} "
            f"first_token_ms={result['llm']['first_token_ms']} "
            f"answer={result['answer'][:80]}"
        )

    passed_count = sum(1 for result in results if result["passed"])
    report = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total": len(results),
            "passed": passed_count,
            "failed": len(results) - passed_count,
            "pass_rate": round(passed_count / len(results), 4) if results else 0,
        },
        "results": results,
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"eval_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[eval] summary={report['summary']}")
    print(f"[eval] report={output_path}")
    return 0 if passed_count == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
