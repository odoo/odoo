import ast
import pathlib

import pytest

import odoo.http

_PACKAGE = pathlib.Path(odoo.http.__file__).parent
_WITHOUT_LOGGER = frozenset({"__init__", "_protocols"})


def _modules():
    return sorted(p for p in _PACKAGE.glob("*.py") if p.stem not in _WITHOUT_LOGGER)


def _reports(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        root = sub.func
        while isinstance(root, ast.Attribute):
            root = root.value
        if isinstance(root, ast.Name) and root.id in ("_debug", "_logger"):
            return True
    return False


def _reraises(node: ast.AST) -> bool:
    return any(isinstance(sub, ast.Raise) for sub in ast.walk(node))


def _is_broad(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    names = (
        [handler.type]
        if not isinstance(handler.type, ast.Tuple)
        else list(handler.type.elts)
    )
    return any(
        isinstance(n, ast.Name) and n.id in ("Exception", "BaseException")
        for n in names
    )


@pytest.mark.parametrize("path", _modules(), ids=lambda p: p.stem)
def test_every_module_owns_a_debug_logger(path):
    assert "_debug = DebugLog(__name__)" in path.read_text(), (
        f"{path.name} emits on no channel; every serving or feature module does"
    )


@pytest.mark.parametrize("path", _modules(), ids=lambda p: p.stem)
def test_a_broad_handler_that_swallows_says_so(path):
    tree = ast.parse(path.read_text())
    silent = [
        f"{path.name}:{node.lineno}"
        for node in ast.walk(tree)
        if isinstance(node, ast.ExceptHandler)
        and _is_broad(node)
        and not _reraises(node)
        and not _reports(node)
    ]
    assert silent == [], (
        "a broad except that neither re-raises nor emits an event or a log "
        f"line hides the failure it caught: {silent}"
    )


def test_the_scanner_sees_a_silent_broad_handler():
    tree = ast.parse(
        "try:\n    pass\nexcept Exception:\n    return None\n"
        "try:\n    pass\nexcept Exception:\n    _debug.logic('x')\n"
        "try:\n    pass\nexcept ValueError:\n    return None\n"
    )
    handlers = [n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)]
    verdicts = [_is_broad(h) and not _reraises(h) and not _reports(h) for h in handlers]
    assert verdicts == [True, False, False]
