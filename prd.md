# PRD: CodeQA — Hybrid Retrieval RAG for Codebase Q&A

## 1. Overview

CodeQA is a question-answering system for source code repositories. A user points it at a
codebase and can then ask natural-language questions ("Where is rate limiting implemented?",
"How does the retry logic work?") and receive an answer grounded in the actual source, with
citations to specific files and line ranges.

The project is being built as a portfolio piece for SWE/MLE job applications. The primary
success criterion is not raw accuracy — it's demonstrating sound engineering and ML practices
that hold up under interview scrutiny.

## 2. Problem statement

Generic RAG (chunk text → embed → top-k retrieval) underperforms on source code specifically:

- Identifiers (function/variable names) carry meaning that dense embedding models capture
  poorly, since they're trained mostly on natural language.
- A single "most similar" chunk is often not the most useful one — call sites, definitions,
  and related usages are frequently lexically linked but semantically distant in embedding
  space.
- Naive fixed-size chunking splits functions/classes mid-body, destroying the unit of meaning
  that a developer actually reasons about.

CodeQA addresses this with hybrid retrieval (lexical + semantic) and reranking, and — critically
— measures whether each added component actually earns its complexity, rather than assuming it.

## 3. Goals

1. Answer natural-language questions about a given codebase, grounded in real source with
   citations.
2. Demonstrate, with numbers, that hybrid retrieval + reranking outperforms naive dense-only
   retrieval on code-specific queries.
3. Present as a real engineering artifact: proper structure, tests, containerized, servable
   via an API — not a single notebook.
4. Produce a clear, interview-ready narrative: what was tried, what was measured, what the
   tradeoffs were.

## 4. Non-goals

- Not aiming for production-scale performance (millions of files, sub-100ms latency) — this
  is a portfolio project, not an internal tool at a company with a large codebase.
- Not building a custom-trained embedding or reranking model — using off-the-shelf
  open models is fine; the differentiation is in the retrieval architecture and evaluation,
  not in model training.
- Not supporting every programming language on day one — Python-first, with a generic
  fallback chunker for other file types.
- No authentication/multi-tenancy — single-user, local or personal-deployment scope.

## 5. Target users

- **Primary**: hiring managers / interviewers reviewing a GitHub portfolio project.
- **Secondary**: the author, using the tool themselves to explore unfamiliar codebases
  (a genuine use case that makes the demo credible rather than contrived).

## 6. User stories

- As a reviewer, I can read the README and understand in under 2 minutes what problem this
  solves and why the approach is non-trivial.
- As a reviewer, I can see a results table comparing retrieval configurations with actual
  numbers, not just claims.
- As a user, I can point the tool at any local Python repo and ask it questions without
  needing custom setup for that repo.
- As a user, I get answers that cite exact file/line locations I can go verify.
- As a user, I can query the system either via CLI or a simple API endpoint.

## 7. Functional requirements

| #   | Requirement                                                                                           | Priority   |
| --- | ----------------------------------------------------------------------------------------------------- | ---------- |
| 1   | Ingest a local repo path and produce chunks from source files                                         | Must       |
| 2   | AST-aware chunking for Python (function/class-level units)                                            | Must       |
| 3   | Fallback line-window chunking for non-Python text files                                               | Must       |
| 4   | Build a BM25 lexical index over chunks                                                                | Must       |
| 5   | Build a dense embedding index (sentence-transformers + vector search) over chunks                     | Must       |
| 6   | Fuse BM25 + dense scores into a single ranked list (hybrid retrieval)                                 | Must       |
| 7   | Rerank fused top-N candidates with a cross-encoder                                                    | Must       |
| 8   | Generate a natural-language answer from top retrieved chunks via an LLM, with citations               | Must       |
| 9   | CLI commands to index a repo and query it                                                             | Must       |
| 10  | Fixed eval set of (question, relevant chunk) pairs for a target repo                                  | Must       |
| 11  | Eval script reporting recall@k and MRR across 4 configs: BM25-only, dense-only, hybrid, hybrid+rerank | Must       |
| 12  | Serve query functionality over a REST API                                                             | Should     |
| 13  | Dockerized setup for one-command reproducibility                                                      | Should     |
| 14  | Unit tests for chunking logic and score fusion logic                                                  | Should     |
| 15  | Support for incremental re-indexing on file changes                                                   | Won't (v1) |
| 16  | Query decomposition for multi-hop questions                                                           | Won't (v1) |
| 17  | Web frontend UI                                                                                       | Won't (v1) |

## 8. Non-functional requirements

- **Reproducibility**: a fresh clone + `pip install -r requirements.txt` + one command should
  reproduce indexing and eval results.
- **Explainability**: retrieved chunks and their scores are visible/loggable at every stage,
  not hidden inside a black-box call.
- **Modularity**: retrieval and generation are decoupled so the embedding model, reranker, or
  LLM can each be swapped independently.
- **Cost awareness**: default to a small local embedding model and small reranker to keep
  the project runnable without significant API spend; LLM generation is the only paid-API
  dependency.

## 9. System architecture (high level)

```
Codebase → Chunker (AST-aware) → [BM25 index, Dense index]
                                          |
Query → BM25 retrieval ─┐
                         ├─→ Score fusion → Cross-encoder rerank → Top-k chunks → LLM → Answer w/ citations
Query → Dense retrieval ─┘
```

## 10. Evaluation plan

This is the section that most differentiates the project — it's what turns "I built a RAG
demo" into "I built and measured a retrieval system."

- Build a fixed eval set of 30–50 (question, ground-truth relevant chunk) pairs against one
  target repo (ideally a real, moderately complex open-source repo, not a toy).
- For each of the 4 configurations (BM25-only, dense-only, hybrid, hybrid+rerank), compute:
  - **Recall@5 / Recall@10** — is the relevant chunk in the top-k?
  - **MRR** (mean reciprocal rank) — how high does the relevant chunk rank?
- Report results in a table in the README with a short written interpretation (where hybrid
  helped, where reranking helped or didn't, and why).
- Optionally, spot-check generated answer quality qualitatively (a handful of example Q&A
  pairs shown in the README) — this is not the primary metric but helps show the end-to-end
  system works.

## 11. Success metrics (for the project itself)

- Hybrid + rerank measurably outperforms dense-only on the eval set (this is the core
  hypothesis being tested; if it's _not_ true, that's still a valid and reportable finding).
- README is clear enough that a technical reviewer understands the architecture and results
  without needing to read the code.
- Project can be set up and run by someone else from a fresh clone in under 15 minutes.

## 12. Milestones

| Milestone | Deliverable                                                       |
| --------- | ----------------------------------------------------------------- |
| M1        | Ingestion + AST-aware chunking working on a real target repo      |
| M2        | BM25 index + dense index both built and independently queryable   |
| M3        | Hybrid fusion + reranking implemented                             |
| M4        | Eval set created; eval script produces the 4-way comparison table |
| M5        | LLM generation wired in with citation formatting                  |
| M6        | API + Docker + tests; README finalized with results and narrative |

## 13. Risks / open questions

- **Eval set quality**: a small, self-authored eval set risks being biased toward cases the
  author already knows the system handles well. Mitigation: write eval questions before
  looking at retrieval results, and include some intentionally hard/ambiguous questions.
- **Chunk size variance**: AST-based chunks vary a lot in size (a one-line function vs. a
  200-line class), which affects both embedding quality and LLM context budget. May need a
  max-size split-within-function fallback.
- **Reranking latency**: cross-encoders are slower than bi-encoder similarity; worth
  measuring and reporting latency alongside accuracy, since "hybrid+rerank is best" is only
  a complete story if the cost is also quantified.
- **Target repo choice**: needs to be complex enough to make naive retrieval meaningfully
  worse, but small enough to index and eval quickly during development.

## 14. What ships in the portfolio (deliverables checklist)

- [ ] Public GitHub repo with clean structure and commit history
- [ ] README with architecture diagram, setup instructions, and results table
- [ ] Eval harness + results comparing 4 retrieval configurations
- [ ] Working CLI (index + query)
- [ ] API endpoint (stretch)
- [ ] Short write-up or demo video/GIF (stretch, high value for recruiters skimming)
