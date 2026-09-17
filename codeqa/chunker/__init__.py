"""Split Python source into searchable chunks with exact source locations."""

import ast
import os
import tokenize
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Chunk:
    # Keep the code together with its location so answers can cite the source.
    # Line numbers are 1-based, and both start_line and end_line are included.
    text: str
    file_path: str
    start_line: int
    end_line: int
    chunk_type: str


def chunk_python_file(file_path: str | Path) -> list[Chunk]:
    """Extract definitions, including nested definitions, in source order.

    Classes and their methods intentionally overlap to support both class-level
    and method-level questions. Decorators are included in each definition.
    Files without definitions are returned as one module chunk.
    """
    file_path = Path(file_path) 
    # Respect Python encoding declarations, including files that are not UTF-8.
    with tokenize.open(file_path) as source_file:
        source = source_file.read()
    # An abstract syntax tree (AST) identifies code structures such as functions
    # and classes without relying on text patterns or fixed-size splits.
    tree = ast.parse(source, filename=str(file_path))
    # Preserve newlines so each chunk retains the original code formatting.
    lines = source.splitlines(keepends=True)
    chunks = []

    # Visit nested structures too: methods and inner functions get their own chunks.
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        # A definition's line number excludes its decorators, so start at the
        # earliest decorator when one is present (for example, @staticmethod).
        start_line = min([node.lineno] + [item.lineno for item in node.decorator_list])
        end_line = node.end_lineno
        assert end_line is not None
        chunks.append(Chunk(
            # Convert 1-based source lines to a 0-based slice. The exclusive
            # slice endpoint naturally includes the definition's last line.
            text="".join(lines[start_line - 1:end_line]),
            file_path=str(file_path),
            start_line=start_line,
            end_line=end_line,
            chunk_type="class" if isinstance(node, ast.ClassDef) else "function",
        ))

    # Keep useful files containing only imports or constants; skip blank files.
    if not chunks and source.strip():
        chunks.append(Chunk(source, str(file_path), 1, len(lines), "module"))
    # AST traversal is not source order. Sort by location, putting a larger
    # enclosing definition first if two chunks start on the same line.
    return sorted(chunks, key=lambda chunk: (chunk.start_line, -chunk.end_line))


# Avoid indexing installed dependencies, version-control data, and build output.
EXCLUDED_DIRECTORIES = {
    ".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "node_modules", "build", "dist",
}


def chunk_repository(repo_path: str | Path) -> list[Chunk]:
    """Chunk Python files deterministically, using repository-relative paths.

    Skip symlinks and common dependency/build directories. Invalid Python or
    unreadable files raise an error rather than silently omitting source code.
    """
    root = Path(repo_path).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Repository directory does not exist: {root}")

    chunks = []
    for directory, directories, filenames in os.walk(root, followlinks=False):
        # Modify the list in place so os.walk never enters excluded folders.
        # Sorting folders and files makes repeated scans use the same order.
        directories[:] = sorted(
            name for name in directories
            if name not in EXCLUDED_DIRECTORIES
            and not (Path(directory) / name).is_symlink()
        )
        for filename in sorted(filenames):
            path = Path(directory) / filename
            # Only Python is supported here. Skip file symlinks as well as
            # directory symlinks to avoid duplicate or external source files.
            if path.suffix != ".py" or path.is_symlink():
                continue
            for chunk in chunk_python_file(path):
                # Store portable paths such as "codeqa/cli.py" instead of a
                # machine-specific absolute path. Use forward slashes consistently.
                chunk.file_path = path.relative_to(root).as_posix()
                chunks.append(chunk)
    return chunks
