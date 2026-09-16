import ast
import pathlib

import pytest

import odoo.http

_PACKAGE = pathlib.Path(odoo.http.__file__).parent

FOUNDATION = frozenset({"constants", "exceptions", "_protocols", "settings"})
FEATURES = frozenset({"openapi", "_params", "geoip"})


def _modules() -> dict[str, pathlib.Path]:
    return {
        path.stem: path
        for path in sorted(_PACKAGE.glob("*.py"))
        if path.stem != "__init__"
    }


def _runtime_imports(source: str) -> set[str]:
    tree = ast.parse(source)
    found: set[str] = set()

    def visit(nodes, guarded):
        for node in nodes:
            if isinstance(node, ast.If) and _is_type_checking(node.test):
                visit(node.orelse, guarded)
                continue
            if isinstance(node, ast.Import):
                found.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    if node.module:
                        found.add(f".{node.module}")
                    else:
                        found.update(f".{alias.name}" for alias in node.names)
                elif node.module:
                    found.add(node.module)
            elif isinstance(node, ast.If | ast.Try | ast.With):
                for field in ("body", "orelse", "finalbody", "handlers"):
                    children = getattr(node, field, None) or []
                    for child in children:
                        visit(getattr(child, "body", [child]), guarded)

    visit(tree.body, False)
    return found


def _is_type_checking(test: ast.expr) -> bool:
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


def _sibling_imports(name: str) -> set[str]:
    imports = _runtime_imports(_modules()[name].read_text())
    siblings = set()
    for imported in imports:
        if imported.startswith("."):
            siblings.add(imported[1:].split(".")[0])
        elif imported.startswith("odoo.http."):
            siblings.add(imported.split(".")[2])
    return siblings - {name}


def _tier(name: str) -> str:
    if name in FOUNDATION:
        return "foundation"
    if name in FEATURES:
        return "features"
    return "serving"


@pytest.mark.parametrize("name", sorted(FOUNDATION))
def test_foundation_imports_only_foundation(name):
    below = {s for s in _sibling_imports(name) if _tier(s) != "foundation"}
    assert below == set(), f"{name} ([foundation]) reaches {sorted(below)}"


@pytest.mark.parametrize("name", sorted(FEATURES))
def test_features_stay_below_serving(name):
    above = {s for s in _sibling_imports(name) if _tier(s) == "serving"}
    assert above == set(), f"{name} ([features]) reaches [serving] {sorted(above)}"


def test_every_module_is_filed_in_a_tier():
    filed = FOUNDATION | FEATURES
    unknown = filed - set(_modules())
    assert unknown == set(), f"tier lists name modules that do not exist: {unknown}"


@pytest.mark.parametrize("name", sorted(_modules()))
def test_the_core_package_reaches_no_addon(name):
    reached = {
        imported
        for imported in _runtime_imports(_modules()[name].read_text())
        if imported.startswith("odoo.addons")
    }
    assert reached == set(), f"{name} imports {sorted(reached)}"


def test_the_scanner_sees_runtime_reaches_and_spares_type_checking_ones():
    source = (
        "from typing import TYPE_CHECKING\n"
        "from . import constants\n"
        "if TYPE_CHECKING:\n"
        "    from . import dispatcher\n"
        "def f():\n"
        "    from . import routing\n"
    )
    found = _runtime_imports(source)
    assert ".constants" in found
    assert ".dispatcher" not in found
    assert ".routing" not in found, "a deferred import does not weigh on load"
