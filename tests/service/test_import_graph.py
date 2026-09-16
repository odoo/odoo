"""The layering of `odoo.service`, read off its imports rather than its text.

`doc/architecture/module.md` states which way the package reads; this
derives the module-level import graph with `ast` and asserts the same
rules, so a refactor that crosses a boundary fails here and not in review.
Function-level imports are deliberately excluded: they are the documented
escape for the two addon reaches and the lazy registry import.
"""

import ast
import pathlib

import pytest

import odoo.service

PKG = pathlib.Path(odoo.service.__file__).parent
ROOT = "odoo.service"


def _module_name(path: pathlib.Path) -> str:
    rel = path.relative_to(PKG).with_suffix("")
    parts = [ROOT, *rel.parts]
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _resolve(module: str, node: ast.ImportFrom) -> str:
    if not node.level:
        return node.module or ""
    base = module.split(".")
    if not (PKG / pathlib.Path(*module.split(".")[2:])).is_dir():
        base = base[:-1]
    base = base[: len(base) - (node.level - 1)]
    return ".".join([*base, node.module] if node.module else base)


def _top_level_imports(path: pathlib.Path) -> set[str]:
    module = _module_name(path)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.If) and "TYPE_CHECKING" in ast.dump(node.test):
            continue
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            target = _resolve(module, node)
            found.add(target)
            found.update(f"{target}.{alias.name}" for alias in node.names)
    return found


@pytest.fixture(scope="module")
def graph() -> dict[str, set[str]]:
    return {
        _module_name(p): _top_level_imports(p)
        for p in sorted(PKG.rglob("*.py"))
        if "tests" not in p.parts
    }


def _imports(graph, module, prefix):
    return sorted(i for i in graph[module] if i == prefix or i.startswith(prefix + "."))


class TestTheServersReadInOneDirection:
    def test_the_two_flavours_do_not_import_each_other(self, graph):
        assert not _imports(graph, f"{ROOT}._threaded", f"{ROOT}._prefork")
        assert not _imports(graph, f"{ROOT}._prefork", f"{ROOT}._threaded")

    def test_only_the_factory_and_the_facade_know_every_flavour(self, graph):
        flavours = (f"{ROOT}._threaded", f"{ROOT}._prefork")
        knowing = {
            m
            for m, imports in graph.items()
            if all(any(i.startswith(f) for i in imports) for f in flavours)
        }
        assert knowing == {f"{ROOT}._factory", f"{ROOT}.server"}

    def test_the_leaves_import_no_server(self, graph):
        for leaf in (
            "settings",
            "_env",
            "_limits",
            "_base_server",
            "_cron",
            "_census",
            "_reload",
        ):
            for flavour in ("_threaded", "_prefork", "_worker", "httpd", "_factory"):
                assert not _imports(graph, f"{ROOT}.{leaf}", f"{ROOT}.{flavour}"), (
                    f"{leaf} reads upward into {flavour}"
                )


class TestTheTierBoundaries:
    def test_the_transaction_primitive_is_transport_agnostic(self, graph):
        assert not _imports(graph, f"{ROOT}.transaction", "odoo.http")

    def test_no_module_imports_an_addon_at_module_level(self, graph):
        # `odoo.addons` itself is the namespace whose __path__ the watcher
        # walks; an addon is anything below it.
        offenders = {
            m: [i for i in imports if i.startswith("odoo.addons.")]
            for m, imports in graph.items()
        }
        assert not {m: i for m, i in offenders.items() if i}

    def test_no_module_imports_the_orm_package_directly(self, graph):
        offenders = {m: _imports(graph, m, "odoo.orm") for m in graph}
        assert not {m: i for m, i in offenders.items() if i}, (
            "the serving tier goes through the facades (odoo.api, odoo.models, "
            "odoo.modules.registry)"
        )


class TestTheDatabaseManagementService:
    def test_checks_is_the_bottom(self, graph):
        assert not _imports(graph, f"{ROOT}.db._checks", f"{ROOT}.db")

    def test_listing_reads_nothing_above_itself(self, graph):
        for above in ("lifecycle", "dump", "restore", "rpc"):
            assert not _imports(graph, f"{ROOT}.db.listing", f"{ROOT}.db.{above}")

    def test_rpc_is_the_top(self, graph):
        assert not any(
            _imports(graph, m, f"{ROOT}.db.rpc")
            for m in graph
            if m.startswith(f"{ROOT}.db.") and m != f"{ROOT}.db"
        )


class TestTheGraphReadsWhatIsThere:
    """The rules above are only as good as the resolver; three edges that
    exist and one that must not (a TYPE_CHECKING import) pin it."""

    def test_relative_imports_resolve_across_the_subpackage(self, graph):
        assert f"{ROOT}._dispatch.dispatch_through_table" in graph[f"{ROOT}.db.rpc"]
        assert f"{ROOT}.db._checks.check_super" in graph[f"{ROOT}.db.rpc"]

    def test_absolute_imports_are_kept_whole(self, graph):
        assert "odoo.libs.debug_log.DebugLog" in graph[f"{ROOT}._worker"]

    def test_a_type_checking_import_is_not_an_edge(self, graph):
        assert not _imports(graph, f"{ROOT}._worker", f"{ROOT}.server")
        assert f"{ROOT}._transport.ServerIdentity" in graph[f"{ROOT}._worker"]
