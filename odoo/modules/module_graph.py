import functools
import logging
import typing
from typing import Literal

from odoo.db.schema import column_exists
from odoo.libs.debug_log import DebugLog
from odoo.tools import OrderedSet, reset_cached_properties

from ._protocols import GraphSqlReader
from .module import Manifest

if typing.TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Iterator, Mapping

    STATES = Literal[
        "uninstallable",
        "uninstalled",
        "installed",
        "to upgrade",
        "to remove",
        "to install",
    ]

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class ModuleNode:
    def __init__(self, name: str, module_graph: ModuleGraph) -> None:
        self.name: str = name
        manifest = Manifest.for_addon(name, display_warning=False)
        if manifest is not None:
            manifest._force_parse()
        else:
            _debug.logic("module_graph.manifest_missing", module=name)
        self.manifest: Mapping = manifest or {}

        self.id: int = 0
        self.state: STATES = "uninstalled"
        self.demo: bool = False
        self.db_version: str | None = None

        self.load_state: STATES = "uninstalled"
        self.load_version: str | None = None

        self.depends: OrderedSet[ModuleNode] = OrderedSet()
        self.module_graph: ModuleGraph = module_graph

    @functools.cached_property
    def order_name(self) -> str:
        if self.name.startswith("test_"):
            last_installed_dependency = max(
                self.depends, key=lambda m: (m.depth, m.order_name)
            )
            return last_installed_dependency.order_name + " " + self.name

        return self.name

    @functools.cached_property
    def depth(self) -> int:
        if self.name.startswith("test_"):
            last_installed_dependency = max(
                self.depends, key=lambda m: (m.depth, m.order_name)
            )
            return last_installed_dependency.depth

        return max(module.depth for module in self.depends) + 1 if self.depends else 0

    @functools.cached_property
    def phase(self) -> int:
        if self.name == "base":
            return 0

        if self.module_graph.mode == "load":
            return 1

        def is_in_a_different_phase(module: ModuleNode, dependency: ModuleNode) -> bool:
            return (module.state == "to install") ^ (dependency.state == "to install")

        return max(
            dependency.phase
            + (1 if is_in_a_different_phase(self, dependency) else 0)
            + (1 if dependency.name == "base" else 0)
            for dependency in self.depends
        )

    @property
    def demo_installable(self) -> bool:
        return all(p.demo for p in self.depends)


class ModuleGraph:
    def __init__(
        self, cr: GraphSqlReader, mode: Literal["load", "update"] = "load"
    ) -> None:
        self.mode: Literal["load", "update"] = mode
        self._modules: dict[str, ModuleNode] = {}
        self._cr: GraphSqlReader = cr

    def __contains__(self, name: str) -> bool:
        return name in self._modules

    def __getitem__(self, name: str) -> ModuleNode:
        return self._modules[name]

    def __iter__(self) -> Iterator[ModuleNode]:
        with _debug.perf("module_graph.sort", modules=len(self._modules)):
            ordered = sorted(
                self._modules.values(),
                key=lambda p: (p.phase, p.depth, p.order_name),
            )
        return iter(ordered)

    def __len__(self) -> int:
        return len(self._modules)

    def extend(self, names: Collection[str]) -> None:
        with _debug.perf(
            "module_graph.extend", requested=len(names), mode=self.mode
        ) as span:
            for module in self._modules.values():
                reset_cached_properties(module)

            names = [name for name in names if name not in self._modules]
            span.set(new=len(names))

            for name in names:
                module = self._modules[name] = ModuleNode(name, self)
                if not module.manifest.get("installable"):
                    imported = name in self._imported_modules  # debuglog
                    _debug.logic(
                        "module_graph.not_installable",
                        module=name,
                        imported=imported,
                        manifest=bool(module.manifest),
                    )
                    if imported:
                        self._remove(name, log_dependents=False)
                    else:
                        _logger.warning("module %s: not installable, skipped", name)
                        self._remove(name)

            self._update_depends(names)
            self._update_depth(names)
            self._update_from_database(names)
            span.set(kept=sum(1 for name in names if name in self._modules))
        _debug.pipeline(
            "module_graph.extended",
            requested=len(names),
            kept=sum(1 for name in names if name in self._modules),
            total=len(self._modules),
            mode=self.mode,
        )

    def installed_outside(self) -> list[str]:
        self._cr.execute(
            "SELECT name FROM ir_module_module WHERE state IN ('installed', 'to upgrade')"
        )
        outside = [name for (name,) in self._cr.fetchall() if name not in self._modules]
        _debug.perf.count(
            "module_graph.installed_outside", outside=len(outside), graph=len(self)
        )
        return outside

    @functools.cached_property
    def _imported_modules(self) -> OrderedSet[str]:
        result = ["studio_customization"]
        has_column = column_exists(self._cr, "ir_module_module", "imported")
        if has_column:
            self._cr.execute("SELECT name FROM ir_module_module WHERE imported")
            result += [m[0] for m in self._cr.fetchall()]
        _debug.logic(
            "module_graph.imported_modules", column=has_column, modules=len(result)
        )
        return OrderedSet(result)

    def _update_depends(self, names: Iterable[str]) -> None:
        for name in names:
            if module := self._modules.get(name):
                depends = module.manifest["depends"]
                try:
                    module.depends = OrderedSet(self._modules[dep] for dep in depends)
                except KeyError:
                    missing = [dep for dep in depends if dep not in self._modules]
                    _debug.logic(
                        "module_graph.depends_missing",
                        module=name,
                        missing=",".join(missing),
                    )
                    _logger.warning(
                        "module %s: some depends are not loaded (%s), skipped",
                        name,
                        ", ".join(missing),
                    )
                    self._remove(name)

    def _update_depth(self, names: Iterable[str]) -> None:
        with _debug.perf("module_graph.cycle_scan", modules=len(self._modules)) as span:
            cycle_members = self._get_module_names_in_cycles()
            span.set(on_cycle=len(cycle_members))
        for cycle_member in cycle_members:
            if cycle_member in self._modules:
                _debug.logic("module_graph.cycle_member", module=cycle_member)
                _logger.warning(
                    "module %s: in a dependency loop, skipped",
                    cycle_member,
                )
                self._remove(cycle_member)
        for name in names:
            if module := self._modules.get(name):
                _ = module.depth

    def _get_module_names_in_cycles(self) -> set[str]:
        indices: dict[str, int] = {}
        lowlinks: dict[str, int] = {}
        on_scc_stack: set[str] = set()
        scc_stack: list[str] = []
        on_cycle: set[str] = set()
        counter = 0

        def get_dependency_names(name: str) -> list[str]:
            return [
                d.name for d in self._modules[name].depends if d.name in self._modules
            ]

        for root in list(self._modules):
            if root in indices:
                continue
            indices[root] = lowlinks[root] = counter
            counter += 1
            scc_stack.append(root)
            on_scc_stack.add(root)
            work: list[list] = [[root, 0, get_dependency_names(root)]]

            while work:
                name, idx, deps = work[-1]
                if idx < len(deps):
                    work[-1][1] = idx + 1
                    child = deps[idx]
                    if child not in indices:
                        indices[child] = lowlinks[child] = counter
                        counter += 1
                        scc_stack.append(child)
                        on_scc_stack.add(child)
                        work.append([child, 0, get_dependency_names(child)])
                    elif child in on_scc_stack:
                        lowlinks[name] = min(lowlinks[name], indices[child])
                else:
                    if lowlinks[name] == indices[name]:
                        scc: list[str] = []
                        while True:
                            w = scc_stack.pop()
                            on_scc_stack.discard(w)
                            scc.append(w)
                            if w == name:
                                break
                        if len(scc) > 1 or name in get_dependency_names(name):
                            on_cycle.update(scc)
                    work.pop()
                    if work:
                        parent = work[-1][0]
                        lowlinks[parent] = min(lowlinks[parent], lowlinks[name])

        return on_cycle

    def _update_from_database(self, names: Iterable[str]) -> None:
        names = tuple(name for name in names if name in self._modules)
        if not names:
            return
        query = """
            SELECT name, id, state, demo, db_version
            FROM ir_module_module
            WHERE name = ANY(%s)
        """
        self._cr.execute(query, [list(names)])
        rows = self._cr.fetchall()
        states: dict[str, int] = {}  # debuglog
        for name, id_, state, demo, db_version in rows:
            if name not in self._modules:
                continue
            states[state] = states.get(state, 0) + 1  # debuglog
            if state == "uninstallable":
                _debug.logic("module_graph.skipped", module=name, state=state)
                _logger.warning("module %s: not installable, skipped", name)
                self._remove(name)
                continue
            if self.mode == "load" and state in ["to install", "uninstalled"]:
                _debug.logic("module_graph.skipped", module=name, state=state)
                _logger.info("module %s: not installed, skipped", name)
                self._remove(name)
                continue
            module = self._modules[name]
            module.id = id_
            module.state = state
            module.demo = demo
            module.db_version = db_version
            module.load_version = db_version
            module.load_state = state
        _debug.pipeline(
            "module_graph.database_states",
            # one expansion and no fixed keyword beside it: the state names are
            # database values, so a fixed keyword they happened to match would
            # raise TypeError from the call machinery, channels off included
            **{
                "names": len(names),
                "rows": len(rows),
                "mode": self.mode,
                **{
                    f"state_{state.replace(' ', '_')}": count
                    for state, count in states.items()
                },
            },
        )

    def _remove(self, name: str, log_dependents: bool = True) -> None:
        module = self._modules.pop(name)
        _debug.logic("module_graph.removed", module=name, log_dependents=log_dependents)
        for another, another_module in list(self._modules.items()):
            if (
                module in another_module.depends
                and another_module.name in self._modules
            ):
                if log_dependents:
                    _logger.info(
                        "module %s: its direct/indirect dependency is skipped, skipped",
                        another,
                    )
                self._remove(another)
