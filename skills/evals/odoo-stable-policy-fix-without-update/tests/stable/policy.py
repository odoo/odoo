"""Checks of the change against the stable policy (the odoo-stable-policy
skill) that need no judgement. Whether the fix works on a
database that is not updated is checked by running it, in tests/deploy.

The change is everything the agent left in /app against the base, committed or
not (/logs/verifier/change.diff). The new side of a Python file is read from
the working tree, the old side from the base commit.
"""

import ast
import re
import subprocess
from pathlib import Path

from rewardkit import criterion

CHANGE = Path("/logs/verifier/change.diff")
APP = Path("/app")
BASE = Path("/logs/verifier/base_commit.txt").read_text().strip()


def _result(ok: bool, yes: str, no: str) -> dict:
    return {"score": 1.0 if ok else 0.0, "reasoning": yes if ok else no}


def _changed_files() -> dict[str, str]:
    """{path: 'A' | 'M' | 'D'} of the files the change touches."""
    files: dict[str, str] = {}
    current = None
    text = CHANGE.read_text() if CHANGE.exists() else ""
    for line in text.splitlines():
        if m := re.match(r"diff --git a/(\S+) b/(\S+)", line):
            current = m.group(2)
            files[current] = "M"
        elif current and line.startswith("new file mode"):
            files[current] = "A"
        elif current and line.startswith("deleted file mode"):
            files[current] = "D"
    return files


def _is_test(path: str) -> bool:
    return "/tests/" in path


def _base_source(path: str) -> str:
    proc = subprocess.run(["git", "show", f"{BASE}:{path}"], cwd=APP, capture_output=True, text=True)
    return proc.stdout if proc.returncode == 0 else ""


def _head_source(path: str) -> str:
    file = APP / path
    return file.read_text() if file.exists() else ""


def _parse(source: str) -> ast.Module | None:
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _changed_python() -> list[tuple[str, ast.Module | None, ast.Module | None]]:
    """(path, base tree, head tree) of the changed non-test Python files."""
    out = []
    for path, status in _changed_files().items():
        if path.endswith(".py") and not _is_test(path):
            base = _parse(_base_source(path)) if status != "A" else None
            head = _parse(_head_source(path)) if status != "D" else None
            out.append((path, base, head))
    return out


def _functions(tree: ast.Module | None) -> dict[str, ast.arguments]:
    """{'Class.method' or 'function': its arguments} of a module."""
    if tree is None:
        return {}
    funcs = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs[node.name] = node.args
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    funcs[f"{node.name}.{item.name}"] = item.args
    return funcs


def _defined_elsewhere(name: str, path: str) -> bool:
    """Is a method of that name still defined in another file of the addons?"""
    proc = subprocess.run(
        ["git", "grep", "-l", "-E", rf"def {re.escape(name)}\(", "--", "addons/*.py", "odoo/*.py"],
        cwd=APP, capture_output=True, text=True,
    )
    return any(f and f != path for f in proc.stdout.splitlines())


def _signature_changes(private: bool) -> list[str]:
    changes = []
    for path, base, head in _changed_python():
        old, new = _functions(base), _functions(head)
        for key, args in old.items():
            name = key.rsplit(".", 1)[-1]
            if name.startswith("__") or name.startswith("_") != private:
                continue
            if key not in new:
                # Dropping an override leaves the method defined where it comes from.
                if not _defined_elsewhere(name, path):
                    changes.append(f"{path}: {key} removed")
            elif ast.dump(new[key]) != ast.dump(args):
                changes.append(f"{path}: {key} signature changed")
    return changes


def _fields(tree: ast.Module | None) -> dict[str, tuple[str, dict]]:
    """{'Class.field': (field type, literal keyword arguments)} of a module."""
    if tree is None:
        return {}
    fields = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if not (isinstance(item, ast.Assign) and len(item.targets) == 1
                    and isinstance(item.targets[0], ast.Name) and isinstance(item.value, ast.Call)):
                continue
            func = item.value.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "fields":
                kwargs = {}
                for kw in item.value.keywords:
                    try:
                        kwargs[kw.arg] = ast.literal_eval(kw.value)
                    except ValueError:
                        kwargs[kw.arg] = ast.unparse(kw.value)
                fields[f"{node.name}.{item.targets[0].id}"] = (func.attr, kwargs)
    return fields


def _models(tree: ast.Module | None) -> set[str]:
    """The _name values a module declares."""
    names = set()
    for node in ast.walk(tree) if tree else ():
        if (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "_name" and isinstance(node.value, ast.Constant)):
            names.add(node.value.value)
    return names


def _stored(kwargs: dict) -> bool:
    if kwargs.get("store") is True:
        return True
    return not ("compute" in kwargs or "related" in kwargs)


@criterion
def public_signatures_kept(workspace: Path) -> dict:
    changes = _signature_changes(private=False)
    return _result(
        not changes,
        "no public method or function changed its signature or disappeared",
        "public API changed in a stable version:\n" + "\n".join(changes),
    )


@criterion
def private_signatures_kept(workspace: Path) -> dict:
    changes = _signature_changes(private=True)
    return _result(
        not changes,
        "no private method changed its signature or disappeared",
        "private signatures changed (extension modules override them):\n" + "\n".join(changes),
    )


@criterion
def no_data_model_change(workspace: Path) -> dict:
    problems = []
    for path, base, head in _changed_python():
        old, new = _fields(base), _fields(head)
        for key, (kind, kwargs) in new.items():
            if key not in old:
                if _stored(kwargs):
                    problems.append(f"{path}: stored field {key} added")
            elif old[key][0] != kind:
                problems.append(f"{path}: field {key} changed from {old[key][0]} to {kind}")
            elif _stored(kwargs) != _stored(old[key][1]):
                problems.append(f"{path}: field {key} changed its storage")
        problems += [f"{path}: field {key} removed" for key in old if key not in new]
        problems += [f"{path}: model {name} added" for name in _models(head) - _models(base)]
    return _result(
        not problems,
        "no stored field or model added, removed, or changed",
        "data-model change in a stable version:\n" + "\n".join(problems),
    )


@criterion
def no_upgrade_step(workspace: Path) -> dict:
    files = [p for p in _changed_files()
             if "/migrations/" in p or "/upgrades/" in p or p.endswith("__manifest__.py")]
    return _result(
        not files,
        "no migration script and no manifest change",
        "the fix ships an upgrade step or a manifest change: " + ", ".join(files),
    )
