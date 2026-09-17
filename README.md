# CodeQA

CodeQA is a codebase question-answering project. The first implemented component
reads Python repositories and splits source into functions and classes, preserving
file paths and line numbers for future answer citations.

## Try the chunker

Use Python 3.10 or newer. The chunker uses only the Python standard library.
Run this from the project root, replacing `.` with a repository path if desired:

```python
from codeqa.chunker import chunk_repository

chunks = chunk_repository(".")
for chunk in chunks:
    print(f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line} ({chunk.chunk_type})")
    print(chunk.text)
```

The chunker includes decorators, async functions, and nested definitions. Classes
and their methods intentionally produce overlapping chunks. Files without any
definitions produce a single module chunk. Repository scans skip symlinks and
common dependency/build directories, and report errors for invalid Python.

Current limitations: only Python files are scanned; `.gitignore` rules are not
interpreted; module-level code outside definitions is not separately chunked when
definitions exist; oversized definitions are not yet split.

## Tests

Install `pytest` in your environment, then run:

```sh
python -m pytest -q
```

## Next steps

Add fallback text chunking and chunk-size limits, then build BM25 and FAISS
indexes. Retrieval, reranking, answer generation, and the CLI/API are planned in
[prd.md](prd.md).
