import pytest

from codeqa.chunker import chunk_python_file, chunk_repository


def test_definitions_preserve_decorators_async_and_citations(tmp_path):
    source = (
        "@decorate\n"
        "class Client:\n"
        "    @staticmethod\n"
        "    async def fetch():\n"
        "        return 'result'\n"
        "\n"
        "def outer():\n"
        "    def inner():\n"
        "        return 1\n"
        "    return inner()\n"
    )
    path = tmp_path / "client.py"
    path.write_text(source)
    chunks = chunk_python_file(path)
    assert [(c.chunk_type, c.start_line, c.end_line) for c in chunks] == [
        ("class", 1, 5), ("function", 3, 5),
        ("function", 7, 10), ("function", 8, 9),
    ]
    for chunk in chunks:
        assert chunk.text == "".join(
            source.splitlines(keepends=True)[chunk.start_line - 1:chunk.end_line]
        )
        assert chunk.file_path == str(path)


def test_module_fallback_and_empty_file(tmp_path):
    path = tmp_path / "config.py"
    path.write_text("TIMEOUT = 30\nRETRIES = 3")
    chunk, = chunk_python_file(path)
    assert (chunk.chunk_type, chunk.start_line, chunk.end_line) == ("module", 1, 2)
    assert chunk.text == path.read_text()
    path.write_text("\n  \n")
    assert chunk_python_file(path) == []


def test_python_encoding_cookie(tmp_path):
    path = tmp_path / "legacy.py"
    path.write_bytes("# coding: latin-1\nLABEL = 'café'\n".encode("latin-1"))
    assert "café" in chunk_python_file(path)[0].text


def test_invalid_python_reports_filename(tmp_path):
    path = tmp_path / "broken.py"
    path.write_text("def unfinished(")
    with pytest.raises(SyntaxError) as error:
        chunk_python_file(path)
    assert error.value.filename == str(path)


def test_repository_scanning(tmp_path):
    (tmp_path / "app.py").write_text("def run():\n    pass\n")
    package = tmp_path / "package"
    package.mkdir()
    (package / "config.py").write_text("LIMIT = 10\n")
    (tmp_path / "README.md").write_text("Documentation")
    for name in (".venv", ".git", "__pycache__", "build"):
        excluded = tmp_path / name
        excluded.mkdir()
        (excluded / "broken.py").write_text("invalid python!")
    (tmp_path / "linked.py").symlink_to(tmp_path / "app.py")
    (tmp_path / "linked_package").symlink_to(package, target_is_directory=True)
    chunks = chunk_repository(tmp_path)
    assert [chunk.file_path for chunk in chunks] == ["app.py", "package/config.py"]
    assert chunks == chunk_repository(tmp_path)


def test_missing_repository(tmp_path):
    with pytest.raises(NotADirectoryError):
        chunk_repository(tmp_path / "missing")
