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
    uses_rag = trace.get("path") != "faq_direct"

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
        "rag_success": (not uses_rag) or rag.get("status") == "success",
        "rag_has_items": (not uses_rag) or (rag.get("item_count") or 0) > 0,
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
        "path": trace.get("path", "rag_llm"),
        "expected_behavior": case.get("expected_behavior"),
        "passed": eval_result["passed"],
        "checks": eval_result["checks"],
        "required_results": eval_result["required_results"],
        "forbidden_hits": eval_result["forbidden_hits"],
        "answer": trace.get("llm", {}).get("answer", ""),
        "rag": {
            "status": trace.get("rag", {}).get("status"),
            "item_count": trace.get("rag", {}).get("item_count"),
            "candidate_item_count": trace.get("rag", {}).get("candidate_item_count"),
            "used_blocks": trace.get("rag", {}).get("used_blocks"),
            "context_length": trace.get("rag", {}).get("context_length"),
            "duration_ms": trace.get("rag", {}).get("duration_ms"),
            "cache_hit": trace.get("rag", {}).get("cache_hit", False),
            "rerank": trace.get("rag", {}).get("rerank"),
        },
        "llm": {
            "first_token_ms": trace.get("llm", {}).get("first_token_ms"),
            "duration_ms": trace.get("llm", {}).get("duration_ms"),
            "chunk_count": trace.get("llm", {}).get("chunk_count"),
            "usage": trace.get("llm", {}).get("usage"),
        },
        "total_duration_ms": trace.get("total_duration_ms", duration_ms),
    }


def average(values: list[float | int | None]) -> float | None:
    clean_values = [value for value in values if isinstance(value, (int, float))]
    if not clean_values:
        return None
    return round(sum(clean_values) / len(clean_values), 2)


def percentile(values: list[float | int | None], p: float) -> float | None:
    clean_values = sorted(value for value in values if isinstance(value, (int, float)))
    if not clean_values:
        return None

    index = int(round((len(clean_values) - 1) * p))
    return round(clean_values[index], 2)


def count_by(results: list[dict], key: str) -> dict:
    counts = {}
    for result in results:
        value = result.get(key) or "unknown"
        counts[value] = counts.get(value, 0) + 1
    return counts


def build_summary(results: list[dict]) -> dict:
    passed_count = sum(1 for result in results if result["passed"])
    cache_hits = sum(1 for result in results if result.get("rag", {}).get("cache_hit"))
    rag_runs = sum(1 for result in results if result.get("path") != "faq_direct")

    return {
        "total": len(results),
        "passed": passed_count,
        "failed": len(results) - passed_count,
        "pass_rate": round(passed_count / len(results), 4) if results else 0,
        "path_counts": count_by(results, "path"),
        "rag_cache": {
            "eligible_runs": rag_runs,
            "hits": cache_hits,
            "hit_rate": round(cache_hits / rag_runs, 4) if rag_runs else 0,
        },
        "latency_ms": {
            "avg_rag": average([result.get("rag", {}).get("duration_ms") for result in results]),
            "avg_first_token": average([result.get("llm", {}).get("first_token_ms") for result in results]),
            "avg_total": average([result.get("total_duration_ms") for result in results]),
            "p95_total": percentile([result.get("total_duration_ms") for result in results], 0.95),
        },
    }


def write_markdown_report(path: Path, report: dict) -> None:
    summary = report["summary"]
    lines = [
        "# RAG Evaluation Report",
        "",
        f"- Created at: `{report['created_at']}`",
        f"- Total cases: `{summary['total']}`",
        f"- Passed: `{summary['passed']}`",
        f"- Failed: `{summary['failed']}`",
        f"- Pass rate: `{summary['pass_rate']}`",
        f"- Path counts: `{json.dumps(summary['path_counts'], ensure_ascii=False)}`",
        f"- RAG cache hit rate: `{summary['rag_cache']['hit_rate']}`",
        f"- Avg RAG latency: `{summary['latency_ms']['avg_rag']}` ms",
        f"- Avg first token latency: `{summary['latency_ms']['avg_first_token']}` ms",
        f"- Avg total latency: `{summary['latency_ms']['avg_total']}` ms",
        f"- P95 total latency: `{summary['latency_ms']['p95_total']}` ms",
        "",
        "| Case | Category | Path | Pass | Cache | Candidates | RAG ms | First token ms | Total ms | Answer |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]

    for result in report["results"]:
        answer = (result.get("answer") or "").replace("\n", " ")
        if len(answer) > 80:
            answer = answer[:77] + "..."
        lines.append(
            "| {id} | {category} | {path} | {passed} | {cache_hit} | {candidates} | {rag_ms} | {first_ms} | {total_ms} | {answer} |".format(
                id=result["id"],
                category=result.get("category") or "",
                path=result.get("path") or "",
                passed="PASS" if result["passed"] else "FAIL",
                cache_hit=result.get("rag", {}).get("cache_hit", False),
                candidates=result.get("rag", {}).get("candidate_item_count"),
                rag_ms=result.get("rag", {}).get("duration_ms"),
                first_ms=result.get("llm", {}).get("first_token_ms"),
                total_ms=result.get("total_duration_ms"),
                answer=answer.replace("|", "\\|"),
            )
        )

    path.write_text("\n".join(lines), encoding="utf-8")


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
        "--repeat",
        type=int,
        default=1,
        help="Repeat the selected case set. Use 2+ to verify RAG cache hits.",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Also write a human-readable Markdown report.",
    )
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
    total_runs = len(cases) * max(1, args.repeat)
    print(f"[eval] running {len(cases)} case(s), repeat={max(1, args.repeat)}")
    run_index = 0
    for round_index in range(1, max(1, args.repeat) + 1):
        for case in cases:
            run_index += 1
            print(f"[eval] {run_index}/{total_runs} round={round_index} {case['id']} - {case['question']}")
            result = run_case(client, case)
            result["round"] = round_index
            results.append(result)
            mark = "PASS" if result["passed"] else "FAIL"
            print(
                f"[eval] {mark} path={result['path']} "
                f"cache_hit={result['rag']['cache_hit']} "
                f"rag_ms={result['rag']['duration_ms']} "
                f"first_token_ms={result['llm']['first_token_ms']} "
                f"answer={result['answer'][:80]}"
            )

    report = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "summary": build_summary(results),
        "results": results,
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"eval_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.markdown:
        markdown_path = output_path.with_suffix(".md")
        write_markdown_report(markdown_path, report)
        print(f"[eval] markdown={markdown_path}")

    print(f"[eval] summary={report['summary']}")
    print(f"[eval] report={output_path}")
    return 0 if report["summary"]["passed"] == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
