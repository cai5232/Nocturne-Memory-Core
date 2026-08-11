import ast
from pathlib import Path


def test_server_does_not_import_posix_fcntl_unconditionally():
    source = Path("server.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    unconditional = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            unconditional.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            unconditional.append(node.module)
    assert "fcntl" not in unconditional
    assert "def _file_lock" in source
