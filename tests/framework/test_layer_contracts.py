"""The dependency rules of doc/architecture/module.md, as a test.

The table there marked most of them "held by review" since tooling/ went on
2026-09-11. A rule is a direct module-scope import edge: `if TYPE_CHECKING:`
bodies and imports inside a function are outside every rule, which is how a
cycle is broken on purpose. Test files are outside the rules; `odoo/tests/`
is the shipped test framework and is not.
"""

import ast
import unittest
from collections.abc import Callable, Iterator
from pathlib import Path

import odoo

ROOT = Path(odoo.__file__).parent
CHECKOUT = ROOT.parent

Edge = tuple[str, int, str]  # relative path, line, imported module


def _is_type_checking(test: ast.expr) -> bool:
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


def _module_scope_imports(source: str, package: str) -> Iterator[tuple[int, str]]:
    def walk(nodes: list[ast.stmt]) -> Iterator[tuple[int, str]]:
        for node in nodes:
            if isinstance(node, ast.If) and _is_type_checking(node.test):
                yield from walk(node.orelse)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    yield node.lineno, alias.name
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    parts = package.split(".")
                    base = ".".join(parts[: len(parts) - node.level + 1])
                    target = f"{base}.{node.module}" if node.module else base
                    if node.module:
                        yield node.lineno, target
                    else:
                        for alias in node.names:
                            yield node.lineno, f"{target}.{alias.name}"
                elif node.module:
                    # `from odoo.db import schema` reaches odoo.db.schema
                    for alias in node.names:
                        yield node.lineno, f"{node.module}.{alias.name}"
            elif isinstance(node, ast.If | ast.Try | ast.With):
                for field in ("body", "orelse", "finalbody"):
                    yield from walk(getattr(node, field, []))
                for handler in getattr(node, "handlers", []):
                    yield from walk(handler.body)

    yield from walk(ast.parse(source).body)


def _is_test_file(path: Path) -> bool:
    relative = path.relative_to(CHECKOUT)
    if relative.parts[:2] == ("odoo", "tests"):
        return path.name == "conftest.py" or path.name.startswith("test_")
    return (
        "tests" in relative.parts
        or path.name == "conftest.py"
        or path.name.startswith("test_")
    )


def _edges(*subtrees: str) -> Iterator[Edge]:
    for subtree in subtrees:
        root = CHECKOUT / subtree
        paths = sorted(root.rglob("*.py")) if root.is_dir() else [root]
        for path in paths:
            if _is_test_file(path):
                continue
            relative = path.relative_to(CHECKOUT)
            package = ".".join(relative.with_suffix("").parts)
            if path.name == "__init__.py":
                package = ".".join(relative.parts[:-1])
            else:
                package = ".".join(relative.parts[:-1] + (path.stem,))
            for line, imported in _module_scope_imports(path.read_text(), package):
                yield str(relative), line, imported


def _reaches(imported: str, *targets: str) -> bool:
    return any(imported == t or imported.startswith(t + ".") for t in targets)


ORM_LAYER0 = (
    "odoo.orm.primitives",
    "odoo.orm.parsing",
    "odoo.orm.validation",
    "odoo.orm.constants",
    "odoo.orm._typing",
    "odoo.orm._protocols",
)
ORM_HIGHER = (
    "odoo.orm.fields",
    "odoo.orm.domain",
    "odoo.orm.models",
    "odoo.orm.runtime",
    "odoo.orm.components",
)
FACADES = ("odoo.fields", "odoo.models", "odoo.api")


class TestLayerContracts(unittest.TestCase):
    def assertNoEdge(
        self,
        contract: str,
        edges: Iterator[Edge],
        forbidden: Callable[[str, str], bool],
    ) -> None:
        violations = [
            f"{path}:{line} imports {imported}"
            for path, line, imported in edges
            if forbidden(path, imported)
        ]
        self.assertEqual(violations, [], f"{contract} is broken")

    def test_libs_is_dependency_free(self):
        self.assertNoEdge(
            "libs-is-dependency-free",
            _edges("odoo/libs"),
            lambda _p, m: _reaches(m, "odoo") and not _reaches(m, "odoo.libs"),
        )

    def test_db_imports_only_libs(self):
        self.assertNoEdge(
            "db-imports-only-libs",
            _edges("odoo/db"),
            lambda _p, m: (
                _reaches(m, "odoo")
                and not _reaches(
                    m, "odoo.libs", "odoo.exceptions", "odoo.release", "odoo.db"
                )
            ),
        )

    def test_tools_does_not_reach_the_orm_runtime_or_http(self):
        self.assertNoEdge(
            "tools-does-not-reach-the-orm-runtime / tools-stays-below-the-serving-tier",
            _edges("odoo/tools"),
            lambda _p, m: _reaches(m, "odoo.orm.runtime", "odoo.http"),
        )

    def test_orm_helpers_and_registration_stay_below_runtime(self):
        self.assertNoEdge(
            "orm-helpers-and-registration-stay-below-runtime",
            _edges("odoo/orm/helpers.py", "odoo/orm/registration.py"),
            lambda _p, m: _reaches(m, "odoo.orm.runtime"),
        )

    def test_orm_components_are_pure_python(self):
        self.assertNoEdge(
            "orm-components-are-pure-python",
            _edges("odoo/orm/components"),
            lambda _p, m: (
                _reaches(m, "odoo")
                and not _reaches(m, "odoo.libs", "odoo.orm.components")
            ),
        )

    def test_orm_layer0_is_foundational(self):
        self.assertNoEdge(
            "orm-layer0-is-foundational",
            _edges(*(f"odoo/orm/{name.rsplit('.', 1)[1]}.py" for name in ORM_LAYER0)),
            lambda _p, m: _reaches(m, *ORM_HIGHER, *FACADES),
        )

    def test_orm_layer1_below_models_and_runtime(self):
        self.assertNoEdge(
            "orm-layer1-below-models-and-runtime",
            _edges("odoo/orm/fields", "odoo/orm/domain"),
            lambda p, m: (
                _reaches(
                    m, "odoo.orm.models", "odoo.orm.runtime", "odoo.orm.components"
                )
                or (
                    _reaches(m, "odoo.db")
                    and not (
                        p == "odoo/orm/fields/_field_ddl.py" and m == "odoo.db.schema"
                    )
                )
            ),
        )

    def test_orm_models_below_runtime(self):
        self.assertNoEdge(
            "orm-models-below-runtime",
            _edges("odoo/orm/models"),
            lambda _p, m: _reaches(m, "odoo.orm.runtime"),
        )

    def test_orm_seams_stay_below_models_and_runtime(self):
        self.assertNoEdge(
            "orm-seams-stay-below-models-and-runtime",
            _edges("odoo/orm/_recordset.py", "odoo/orm/decorators.py"),
            lambda _p, m: _reaches(m, "odoo.orm.models", "odoo.orm.runtime"),
        )

    def test_orm_below_the_serving_tier(self):
        self.assertNoEdge(
            "orm-below-the-serving-tier",
            _edges("odoo/orm"),
            lambda _p, m: _reaches(m, "odoo.service", "odoo.http", "odoo.cli"),
        )

    def test_core_does_not_depend_on_addons(self):
        self.assertNoEdge(
            "core-does-not-depend-on-addons",
            _edges(
                "odoo/orm",
                "odoo/db",
                "odoo/http",
                "odoo/service",
                "odoo/modules",
                "odoo/libs",
                "odoo/tools",
                "odoo/cli",
            ),
            lambda _p, m: _reaches(m, "odoo.addons") and m != "odoo.addons",
        )

    def test_transaction_primitive_is_transport_agnostic(self):
        self.assertNoEdge(
            "transaction-primitive-is-transport-agnostic",
            _edges("odoo/service/transaction.py"),
            lambda _p, m: _reaches(m, "odoo.http"),
        )

    def test_root_modules_are_foundational(self):
        self.assertNoEdge(
            "root-modules-are-foundational",
            _edges("odoo/exceptions.py", "odoo/release.py"),
            lambda _p, m: _reaches(m, "odoo") and not _reaches(m, "odoo.libs"),
        )
