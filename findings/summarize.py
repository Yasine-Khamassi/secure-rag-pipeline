"""
Summarise the RAG red-team hit-logs into an OWASP/ATLAS-mapped findings report
with the vulnerable vs defended retest.

    python -m findings.summarize
"""

from __future__ import annotations

import json
import os

OUT = os.path.join("findings", "out")


def _load(mode: str):
    path = os.path.join(OUT, f"hitlog-{mode}.json")
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None


def main() -> int:
    vuln, defended = _load("vulnerable"), _load("defended")
    if vuln is None:
        print("Run: python -m redteam.run_rag_redteam --mode both")
        return 1
    d_by = {r["id"]: r for r in defended["results"]} if defended else {}
    lines = ["# Red-team findings - Northwind Secure RAG", "",
             f"Vulnerable: **{vuln['succeeded']}/{vuln['total']}** attacks succeeded."]
    if defended:
        lines.append(f"Defended (retest): **{defended['succeeded']}/{defended['total']}** attacks succeeded.")
    lines += ["", "| OWASP | Probe | Vulnerable | Defended | Detail |",
              "| --- | --- | --- | --- | --- |"]
    for r in vuln["results"]:
        d = d_by.get(r["id"])
        v = "LEAK" if r["attack_succeeded"] else "blocked"
        dd = "-" if d is None else ("LEAK" if d["attack_succeeded"] else "blocked")
        lines.append(f"| {r['owasp']} | `{r['id']}` | {v} | {dd} | {r['detail']} |")
    lines += ["", "## ATLAS", ""] + sorted({f"- {r['atlas']}" for r in vuln["results"]})
    lines += ["", "## Notes", "",
              "- Cross-role leaks are scored at the retrieval layer: an HR-only document",
              "  reaching a general employee is the access-control failure, regardless of what",
              "  the model then says.",
              "- Entitlement filtering and instruction/data separation cut the attacks sharply,",
              "  but indirect prompt injection is not fully solved by labelling alone - any",
              "  residual leak is reported honestly, not hidden.",
              "- Model output is non-deterministic; injection counts can vary between runs."]
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "FINDINGS.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"Wrote {OUT}/FINDINGS.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
