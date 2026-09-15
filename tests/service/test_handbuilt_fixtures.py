import ast
import inspect
import pathlib
import re

import pytest

from odoo.service import _prefork, _threaded, _watcher, _worker, httpd, server

HERE = pathlib.Path(__file__).resolve().parent

_CONSTRUCTED = re.compile(r"__new__\(\s*(?:[\w.]*\.)?(\w+)\s*\)")

_BUILD_WINDOW = 30


def _classes() -> dict:
    out = {}
    for module in (server, _prefork, _threaded, _worker, _watcher, httpd):
        for name, value in vars(module).items():
            if inspect.isclass(value):
                out.setdefault(name, value)
    return out


def _known_attributes(cls) -> set[str]:
    names = set(dir(cls))
    for base in cls.__mro__:
        try:
            source = inspect.getsource(base)
        except OSError, TypeError:
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id in ("self", "cls")
                and isinstance(node.ctx, ast.Store)
            ):
                names.add(node.attr)
    return names


def _handbuilt():
    classes = _classes()
    for path in sorted(HERE.glob("*.py")):
        text = path.read_text()
        lines = text.splitlines()
        for match in _CONSTRUCTED.finditer(text):
            cls = classes.get(match.group(1))
            if cls is None:
                continue
            start = text[: match.start()].count("\n")
            var = lines[start].split("=")[0].strip()
            if not var.isidentifier():
                continue
            assign = re.compile(rf"\s*{re.escape(var)}\.(\w+)\s*=")
            for offset, line in enumerate(
                lines[start + 1 : start + 1 + _BUILD_WINDOW], start + 2
            ):
                found = assign.match(line)
                if found:
                    yield path, offset, cls, found.group(1)


def test_no_fixture_sets_an_attribute_its_class_does_not_have():
    stale = []
    for path, line, cls, attribute in _handbuilt():
        if attribute not in _known_attributes(cls):
            stale.append(f"{path.name}:{line} -> {cls.__name__}.{attribute}")
    assert not stale, (
        "a hand-built fixture assigns an attribute the class hierarchy never "
        "defines. Either production dropped it and the double kept it — in "
        "which case every assertion about it is about nothing — or it is a "
        "typo that has been silently creating a new field:\n  " + "\n  ".join(stale)
    )


def test_the_gate_would_notice_a_dropped_attribute():
    known = _known_attributes(server.Worker)
    assert "alive" in known, "set in Worker.__init__"
    assert "check_limits" in known, "defined as a method"
    assert "no_such_attribute_at_all" not in known

    subclass = _classes()["WorkerHTTP"]
    inherited = _known_attributes(subclass)
    for name in ("alive", "watchdog_pipe"):
        assert name in inherited, (
            f"{name} is assigned only in the Worker base; if the MRO walk stops "
            f"resolving base-class assignments, this gate turns into false positives"
        )


@pytest.mark.parametrize("cls_name", ["PreforkServer", "Worker", "ThreadedServer"])
def test_every_hand_built_class_is_one_this_gate_resolves(cls_name):
    assert cls_name in _classes(), (
        f"{cls_name} is built by hand in this suite but is no longer reachable "
        f"from the modules scanned here, so its fixtures are unchecked"
    )
