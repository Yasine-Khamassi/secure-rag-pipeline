# Secure RAG Application

A retrieval-augmented assistant over fictional Northwind Retail documents, built to
show where a RAG pipeline leaks and which controls stop it. Real embeddings from a
local model, a role-aware vector store, and attacks scored by ground truth.

> **Safety.** Runs locally against a model you own, on synthetic documents with
> planted canaries. Never point this at data or systems you do not control.

## Headline result

Live run against `llama3.2:3b` + `nomic-embed-text` (deterministic retrieval; model
output varies slightly between runs):

| | Vulnerable | Defended |
| --- | --- | --- |
| Attacks succeeded | **4 / 4** | **1 / 4** |

Entitlement filtering removes both cross-role leaks; instruction/data separation
stops one of two indirect injections. The remaining injection is reported honestly:
labelling retrieved content as untrusted raises the bar but does not by itself solve
indirect prompt injection. See [findings/FINDINGS.md](findings/FINDINGS.md).

## Scenario & trust boundaries

Two roles with different entitlements — a general **employee** and an **HR** user —
query company documents. The corpus has public docs, one HR-only document with a
confidential canary, and one untrusted **uploaded** document carrying an indirect
prompt-injection payload.

```mermaid
flowchart TB
    Emp([Employee]) --> Q[Query handler]
    HR([HR user]) --> Q
    Q --> R["Retriever<br/>(entitlement filter when defended)"]
    R --> V[("Vector store<br/>role metadata")]
    V --> R
    R --> P["Prompt builder<br/>(labels retrieved text as untrusted when defended)"]
    P --> M[("LLM via Ollama")]
    M --> O["Output DLP backstop"]
    O --> Emp
    Upload[/Untrusted uploaded doc<br/>poisoned with injection/] -->|ingest| V
```

Boundaries: user→app (role decided), document→ingestion (untrusted content enters),
retriever→store (entitlement filtering must happen here), model output→user (DLP).

## Attacks (OWASP LLM Top 10 / MITRE ATLAS)

| Probe | Class | OWASP | ATLAS |
| --- | --- | --- | --- |
| `xrole-exec-salary` | cross-role retrieval | LLM02 Sensitive Information Disclosure | AML.T0057 |
| `xrole-hr-comp` | cross-role retrieval | LLM02 Sensitive Information Disclosure | AML.T0024 |
| `inject-vendor-note` | indirect prompt injection | LLM01 Prompt Injection | AML.T0051 |
| `inject-summarise-all` | injection via poisoned chunk | LLM08 Vector & Embedding Weaknesses | AML.T0051 |

Cross-role failures are scored at the **retrieval** layer: an HR-only document
reaching an employee is the access-control failure, whatever the model then says.
Injection is scored by a canary appearing in the answer.

## Controls (defended mode)

- **Entitlement filtering at retrieval** (`defenses/controls.py`): a user only
  retrieves document roles they are entitled to — enforced in the store, not the model.
- **Instruction/data separation**: retrieved chunks are labelled untrusted and the
  system prompt tells the model to treat them as data, never instructions.
- **Output DLP**: a backstop that redacts the HR canary if it ever reaches output.

## Run it

```sh
ollama pull llama3.2:3b && ollama pull nomic-embed-text
python -m redteam.run_rag_redteam --mode both   # attack + score (both modes)
python -m findings.summarize                     # findings report
python -m app.cli --role employee "what are the exec salary bands?"
python -m unittest discover -s tests             # control tests (no model)
```

## Portfolio checklist

- [x] Real RAG pipeline: embeddings, role-metadata vector store, retrieval, generation
- [x] Cross-role and indirect-injection attacks with ground-truth scoring
- [x] Entitlement filtering + instruction/data separation + output DLP
- [x] OWASP LLM Top 10 + MITRE ATLAS mapping, vulnerable→defended retest
- [x] Honest residual finding (one injection survives labelling)
- [x] CI control tests (no model) + committed live findings
