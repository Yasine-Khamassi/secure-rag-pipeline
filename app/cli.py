"""
Ask the RAG assistant a question as a given role.

    python -m app.cli --role employee "what are the exec salary bands?"
    python -m app.cli --role employee --defended "summarise the vendor note"
"""

from __future__ import annotations

import argparse

from app.config import ROLE_EMPLOYEE, ROLE_HR
from app.rag import build_index, answer
from app.embed import OllamaError


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--role", choices=[ROLE_EMPLOYEE, ROLE_HR], default=ROLE_EMPLOYEE)
    ap.add_argument("--defended", action="store_true")
    args = ap.parse_args()
    try:
        store = build_index()
        ans = answer(store, args.question, args.role, args.defended)
    except OllamaError as exc:
        print(f"[error] {exc}")
        return 2
    print("retrieved:", [r["id"] for r in ans.retrieved])
    print("answer:", ans.text)
    if ans.hr_dlp_redacted:
        print("(DLP redacted an HR canary from the output)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
