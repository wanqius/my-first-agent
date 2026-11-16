"""跑完 20 条用例，自动判分，输出表格 + 分类统计。

运行：.venv\\Scripts\\python.exe graph\\eval_run.py
"""

import asyncio
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_core import run_agent          # noqa: E402
from eval_cases import CASES              # noqa: E402


async def run_one(case):
    r = await run_agent(case["q"])
    calls_ok = r["calls"] == case["calls"]
    # 去掉所有空白再比对：模型常写「11 月 16 日」，与「11月16日」是同一个答案
    norm = "".join(r["answer"].split())
    any_ok = (not case["any"]) or any("".join(s.split()) in norm for s in case["any"])
    ok = calls_ok and any_ok and not r["error"]
    return {
        "id": case["id"], "type": case["type"], "q": case["q"],
        "expect_calls": case["calls"], "actual_calls": r["calls"],
        "answer": r["answer"], "ok": ok,
        "calls_ok": calls_ok, "any_ok": any_ok,
    }


async def main():
    rows = []
    for i, case in enumerate(CASES, 1):
        row = await run_one(case)
        rows.append(row)
        flag = "PASS" if row["ok"] else "FAIL"
        print(f"[{i:02d}/{len(CASES)}] {row['id']} {flag:4s} calls={row['actual_calls']} 期望={row['expect_calls']}")
        if not row["ok"]:
            print(f"         回答: {row['answer'][:70]}")

    passed = sum(1 for r in rows if r["ok"])
    total = len(rows)

    by_type = defaultdict(lambda: [0, 0])
    for r in rows:
        by_type[r["type"]][1] += 1
        if r["ok"]:
            by_type[r["type"]][0] += 1

    print("\n" + "=" * 56)
    print(f"总通过率：{passed}/{total} = {passed / total:.0%}")
    print("-" * 56)
    print(f"{'类型':<10}{'通过':>6}{'总数':>6}{'通过率':>8}")
    for t, (p, n) in by_type.items():
        print(f"{t:<10}{p:>6}{n:>6}{p / n:>8.0%}")
    print("=" * 56)

    out = {"passed": passed, "total": total, "by_type": {k: v for k, v in by_type.items()}, "rows": rows}
    with open("eval_result.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\n详细结果已写入 eval_result.json")


if __name__ == "__main__":
    asyncio.run(main())
