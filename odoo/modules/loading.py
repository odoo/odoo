import datetime
import gc
import itertools
import json
import logging
import sys
import time
import traceback
import types
import typing

import odoo.db
from odoo import api, tools
from odoo.api import Environment
from odoo.db import schema
from odoo.libs.debug_log import DebugLog
from odoo.libs.hashing import cache_hash
from odoo.logutils import RUNBOT
from odoo.tools import OrderedSet
from odoo.tools.convert import ConvertMode as LoadMode
from odoo.tools.convert import IdRef, convert_file

from . import db as modules_db
from .migration import MigrationManager
from .module import (
    adapt_version,
    get_module_content_checksum,
    initialize_sys_path,
    load_odoo_module,
)
from .module_graph import ModuleGraph
from .registry import Registry

LoadKind = typing.Literal["data", "demo"]

if typing.TYPE_CHECKING:
    from collections.abc import Collection, Iterable

    from odoo.db import BaseCursor, Cursor
    from odoo.orm._protocols import IrCronProtocol, IrModuleModuleProtocol
    from odoo.tests.result import OdooTestResult

    from .module_graph import ModuleNode

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_GC_YOUNG_BACKLOG_LIMIT = 100_000
_GC_FULL_CYCLE_EVERY = 16


_DATA_FILE_CHECKSUM_VERSION = 2

_DYNAMIC_XML_MARKERS = (b"<function", b"<delete")


def _get_data_file_digest_and_dynamic_flag(
    filename: str, content: bytes
) -> tuple[str, bool]:
    digest = cache_hash(content)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    dynamic = ext == "sql" or (
        ext == "xml" and any(marker in content for marker in _DYNAMIC_XML_MARKERS)
    )
    return digest, dynamic


_DEPRECATED_MANIFEST_KEYS = {
    "init_xml": "module %s: key 'init_xml' is deprecated in Odoo 19.",
    "demo_xml": "module %s: key 'demo_xml' is deprecated in Odoo 19, use 'demo'.",
}


def _read_stored_checksums(env: Environment, package: ModuleNode) -> dict:
    env.cr.execute(
        "SELECT data_file_checksums FROM ir_module_module WHERE id = %s",
        [package.id],
    )
    row = env.cr.fetchone()
    if not row:
        return {}
    stored = row[0]
    if not isinstance(stored, dict) or stored.get("v") != _DATA_FILE_CHECKSUM_VERSION:
        _debug.logic(
            "modules.checksums.discarded",
            module=package.name,
            reason="absent" if stored is None else "version",
            version=stored.get("v") if isinstance(stored, dict) else None,
        )
        return {}
    files = stored.get("files")
    return files if isinstance(files, dict) else {}


def _write_stored_checksums(
    env: Environment, package: ModuleNode, new_files: dict
) -> None:
    env.cr.execute(
        "UPDATE ir_module_module SET data_file_checksums = %s::jsonb WHERE id = %s",
        [
            json.dumps({"v": _DATA_FILE_CHECKSUM_VERSION, "files": new_files}),
            package.id,
        ],
    )
    env["ir.module.module"].invalidate_model(["data_file_checksums"])
    _debug.lifecycle(
        "modules.checksums.written",
        module=package.name,
        files=len(new_files),
        dynamic=sum(1 for entry in new_files.values() if entry.get("dyn")),
    )


def _is_reusable_checksum_entry(entry: object, digest: str) -> typing.TypeGuard[dict]:
    return (
        isinstance(entry, dict)
        and entry.get("sha") == digest
        and not entry.get("dyn")
        and isinstance(entry.get("xmlids"), list)
    )


def _has_xmlids_of_another_module(entry: dict, module: str) -> bool:
    return any(xmlid.split(".", 1)[0] != module for xmlid in entry["xmlids"])


def _files_missing_records(cr: BaseCursor, stored_files: dict) -> set[str]:
    files_by_xmlid: dict[str, list[str]] = {}
    for filename, entry in stored_files.items():
        if isinstance(entry, dict) and isinstance(entry.get("xmlids"), list):
            for xmlid in entry["xmlids"]:
                files_by_xmlid.setdefault(xmlid, []).append(filename)
    if not files_by_xmlid:
        return set()
    with _debug.perf(
        "modules.checksums.stale_scan",
        cr=cr,
        files=len(stored_files),
        xmlids=len(files_by_xmlid),
    ) as span:
        cr.execute(
            """
            SELECT x.xmlid
              FROM unnest(%s::text[]) AS x(xmlid)
             WHERE NOT EXISTS (
                   SELECT 1 FROM ir_model_data d
                    WHERE d.module = split_part(x.xmlid, '.', 1)
                      AND d.name = substr(x.xmlid, strpos(x.xmlid, '.') + 1)
             )
        """,
            [list(files_by_xmlid)],
        )
        stale: set[str] = set()
        missing = 0  # debuglog
        for [xmlid] in cr.fetchall():
            missing += 1  # debuglog
            stale.update(files_by_xmlid[xmlid])
        span.set(missing=missing, stale=len(stale))
    return stale


def _convert_and_record(
    env: Environment,
    package: ModuleNode,
    filename: str,
    idref: IdRef,
    mode: LoadMode,
    kind: LoadKind,
) -> set[str]:
    registry = env.registry
    recorder: set[str] = set()
    previous_recorder = registry.loading.xmlid_recorder
    registry.loading.xmlid_recorder = recorder
    try:
        with _debug.perf(
            "modules.convert_file",
            cr=env.cr,
            module=package.name,
            file=filename,
            mode=mode,
            kind=kind,
        ) as span:
            convert_file(
                env,
                package.name,
                filename,
                idref,
                mode,
                noupdate=kind == "demo",
            )
            span.set(xmlids=len(recorder))
    finally:
        registry.loading.xmlid_recorder = previous_recorder
    registry.loading.xmlids_written.update(recorder)
    return recorder


def _load_tracked_file(
    env: Environment,
    package: ModuleNode,
    filename: str,
    idref: IdRef,
    mode: LoadMode,
    kind: LoadKind,
    stored_files: dict,
    stale_files: set[str],
) -> dict:
    with tools.file_open(f"{package.name}/{filename}", "rb", env=env) as fp:
        content = fp.read()
    digest, dynamic = _get_data_file_digest_and_dynamic_flag(filename, content)
    registry = env.registry
    entry = stored_files.get(filename)
    reason = "new" if entry is None else "dynamic" if dynamic else "changed"  # debuglog
    if not dynamic and _is_reusable_checksum_entry(entry, digest):
        contended = registry.loading.xmlids_written.intersection(entry["xmlids"])
        if filename in stale_files:
            reason = "stale"  # debuglog
            _logger.info(
                "re-applying unchanged %s/%s: records it declares are gone from "
                "the database, so its digest no longer witnesses their presence",
                package.name,
                filename,
            )
        elif _has_xmlids_of_another_module(entry, package.name):
            reason = "foreign_xmlids"  # debuglog
            _logger.info(
                "re-applying unchanged %s/%s: it writes records another "
                "module declares, so its effect is its place in the load "
                "order, which the digest cannot witness",
                package.name,
                filename,
            )
        elif not contended:
            registry.loaded_xmlids.update(entry["xmlids"])
            _logger.info("skipping unchanged %s/%s", package.name, filename)
            _debug.perf.count(
                "modules.data_file_loaded",
                module=package.name,
                file=filename,
                xmlids=len(entry["xmlids"]),
                dynamic=False,
                reused=True,
            )
            return entry
        else:
            reason = "contended"  # debuglog
            _logger.info(
                "re-applying unchanged %s/%s: it owns %d record(s) already "
                "rewritten in this run (%s)",
                package.name,
                filename,
                len(contended),
                ", ".join(sorted(contended)[:5]),
            )

    _debug.logic(
        "modules.data_file.reapplied",
        module=package.name,
        file=filename,
        reason=reason,
        dynamic=dynamic,
    )
    _logger.info("loading %s/%s", package.name, filename)
    recorder = _convert_and_record(env, package, filename, idref, mode, kind)
    _debug.perf.count(
        "modules.data_file_loaded",
        module=package.name,
        file=filename,
        xmlids=len(recorder),
        dynamic=dynamic,
        reused=False,
    )
    return {"sha": digest, "xmlids": sorted(recorder), "dyn": dynamic}


def load_data(
    env: Environment,
    idref: IdRef,
    mode: LoadMode,
    kind: LoadKind,
    package: ModuleNode,
) -> None:
    keys = ("init_xml", "data") if kind == "data" else ("demo", "demo_xml")

    track = (
        kind == "data"
        and mode == "update"
        and tools.config["skip_unchanged_data_files"]
        and schema.column_exists(env.cr, "ir_module_module", "data_file_checksums")
    )
    stored_files = _read_stored_checksums(env, package) if track else {}
    stale_files = (
        _files_missing_records(env.cr, stored_files) if stored_files else set()
    )
    new_files: dict = {}
    _debug.pipeline(
        "modules.load_data",
        module=package.name,
        kind=kind,
        mode=mode,
        tracked=track,
        stored=len(stored_files),
        stale=len(stale_files),
    )

    files: set[str] = set()
    with _debug.perf(
        "modules.load_data.files",
        cr=env.cr,
        module=package.name,
        kind=kind,
        mode=mode,
    ) as span:
        for k in keys:
            deprecation = _DEPRECATED_MANIFEST_KEYS.get(k)
            if deprecation and package.manifest[k]:
                _debug.logic(
                    "modules.load_data.deprecated_key",
                    module=package.name,
                    key=k,
                    files=len(package.manifest[k]),
                )
                _logger.warning(deprecation, package.name)
            for filename in package.manifest[k]:
                if filename in files:
                    _debug.logic(
                        "modules.load_data.duplicate_file",
                        module=package.name,
                        file=filename,
                        kind=kind,
                    )
                    _logger.warning(
                        "File %s is imported twice in module %s %s",
                        filename,
                        package.name,
                        kind,
                    )
                files.add(filename)

                if not track:
                    _logger.info("loading %s/%s", package.name, filename)
                    _convert_and_record(env, package, filename, idref, mode, kind)
                    continue

                new_files[filename] = _load_tracked_file(
                    env,
                    package,
                    filename,
                    idref,
                    mode,
                    kind,
                    stored_files,
                    stale_files,
                )
        span.set(files=len(files), idrefs=len(idref))

    if track:
        _write_stored_checksums(env, package, new_files)


def load_demo(
    env: Environment, package: ModuleNode, idref: IdRef, mode: LoadMode
) -> bool:

    try:
        if package.manifest.get("demo") or package.manifest.get("demo_xml"):
            _logger.info("Module %s: loading demo", package.name)
            _debug.pipeline(
                "modules.demo.begin",
                module=package.name,
                mode=mode,
                files=len(package.manifest.get("demo") or ())
                + len(package.manifest.get("demo_xml") or ()),
            )
            # A flushing savepoint restores the ORM state on rollback: without it the
            # failed file's pending writes survive and reference the rows the rollback
            # removed, and the next flush fails the whole installation.
            with env.cr.savepoint():
                load_data(env(su=True), idref, mode, kind="demo", package=package)
        return True
    except Exception as exc:  # debuglog
        _logger.warning(
            "Module %s demo data failed to install, installed without demo data",
            package.name,
            exc_info=True,
        )

        todo = env.ref("base.demo_failure_todo", raise_if_not_found=False)
        Failure = env.get("ir.demo_failure")
        _debug.lifecycle(
            "modules.demo.failed",
            module=package.name,
            error=type(exc).__name__,
            recorded=bool(todo and Failure is not None),
        )
        if todo and Failure is not None:
            todo.write({"state": "open"})
            Failure.create({"module_id": package.id, "error": traceback.format_exc()})
        return False


def force_demo(env: Environment) -> None:
    env.cr.execute(
        "SELECT name FROM ir_module_module WHERE state IN ('installed', 'to upgrade', 'to remove')"
    )
    module_list = [name for (name,) in env.cr.fetchall()]
    graph = ModuleGraph(env.cr, mode="load")
    graph.extend(module_list)
    _debug.pipeline(
        "modules.force_demo.begin", modules=len(module_list), graph=len(graph)
    )

    with _debug.perf("modules.force_demo", cr=env.cr, modules=len(graph)) as span:
        loaded = [
            package.name for package in graph if load_demo(env, package, {}, "init")
        ]
        span.set(loaded=len(loaded), failed=len(graph) - len(loaded))

    env.cr.execute(
        "UPDATE ir_module_module SET demo = (name = ANY(%s)) WHERE name = ANY(%s)",
        [loaded, module_list],
    )
    env["ir.module.module"].invalidate_model(["demo"])


def _warn_models_without_access_rules(
    env: Environment,
    module_name: str,
    model_names: Collection[str],
    registry: Registry,
) -> None:
    concrete_models = [model for model in model_names if not registry[model]._abstract]
    if not concrete_models:
        return
    env.cr.execute(
        """
        SELECT m.model FROM ir_model m
        WHERE NOT EXISTS (
            SELECT 1 FROM ir_model_access a WHERE a.model_id = m.id
        ) AND m.model = ANY(%s)
    """,
        [list(concrete_models)],
    )
    models = [model for [model] in env.cr.fetchall()]
    if not models:
        return
    _debug.logic(
        "modules.access_rules.missing",
        module=module_name,
        models=len(models),
        checked=len(concrete_models),
    )
    lines = [
        f"The models {models} have no access rules in module {module_name}, consider adding some, like:",
        "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink",
    ]
    for model in models:
        xmlid = model.replace(".", "_")
        lines.append(
            f"{module_name}.access_{xmlid},access_{xmlid},{module_name}.model_{xmlid},base.group_user,1,0,0,0"
        )
    _logger.warning("\n".join(lines))


UpdateOperation = typing.Literal["install", "upgrade", "reinit"]


class _PackageLoader:
    __slots__ = (
        "cr",
        "cursor_queries_at_start",
        "env",
        "extra_queries_at_start",
        "index",
        "install_demo",
        "log_level",
        "migrations",
        "model_names",
        "models_to_check",
        "models_updated",
        "module",
        "module_count",
        "operation",
        "package",
        "py_module",
        "registry",
        "report",
        "run_tests",
        "started_at",
        "test_queries",
        "test_results",
        "test_time",
        "update_module",
    )

    def __init__(
        self,
        env: Environment,
        cr: Cursor,
        package: ModuleNode,
        *,
        index: int,
        module_count: int,
        migrations: MigrationManager,
        update_module: bool,
        install_demo: bool,
        run_tests: bool,
        report: OdooTestResult | None,
        models_to_check: OrderedSet[str],
        models_updated: set[str],
    ) -> None:
        self.env = env
        self.cr = cr
        self.registry = env.registry
        self.package = package
        self.index = index
        self.module_count = module_count
        self.migrations = migrations
        self.update_module = update_module
        self.install_demo = install_demo
        self.run_tests = run_tests
        self.report = report
        self.models_to_check = models_to_check
        self.models_updated = models_updated

        self.started_at = time.time()
        self.cursor_queries_at_start = cr.sql_log_count
        self.extra_queries_at_start = odoo.db.sql_counter

        self.operation: UpdateOperation | None = None
        self.log_level = logging.DEBUG
        self.model_names: OrderedSet[str] = OrderedSet()
        self.module: IrModuleModuleProtocol = None  # type: ignore[assignment]
        self.py_module: types.ModuleType = None  # type: ignore[assignment]
        self.test_time = 0.0
        self.test_queries = 0
        self.test_results: OdooTestResult | None = None

    @property
    def name(self) -> str:
        return self.package.name

    def update_operation(self) -> None:
        package = self.package
        if self.update_module and package.state == "to install":
            self.adopt_state_set_by_migration()
        if not self.update_module:
            self.operation = None
        elif package.state == "to install":
            self.operation = "install"
        elif package.state == "to upgrade":
            self.operation = "upgrade"
        elif package.name in self.registry.loading.reinit_modules:
            self.operation = "reinit"
        else:
            self.operation = None
        if self.operation:
            self.log_level = logging.INFO
        _debug.logic(
            "modules.package.operation",
            module=self.name,
            state=package.state,
            operation=self.operation,
            index=self.index,
            count=self.module_count,
        )

    def adopt_state_set_by_migration(self) -> None:
        # The graph read this module's state before the modules ahead of it ran
        # their migrations. One whose pre-migrate hands this module records the
        # database already holds marks it "to upgrade": installing would load its
        # data in init mode, which rewrites noupdate records.
        package = self.package
        self.cr.execute(
            "SELECT state, demo FROM ir_module_module WHERE id = %s", [package.id]
        )
        row = self.cr.fetchone()
        _debug.logic(
            "modules.package.state_adopted",
            module=self.name,
            graph_state=package.state,
            db_state=row[0] if row else None,
            adopted=row is not None and row[0] == "to upgrade",
        )
        if not row or row[0] != "to upgrade":
            return
        package.state = package.load_state = "to upgrade"
        package.demo = row[1]
        self.migrations.index_migration_scripts()

    def announce_module(self) -> None:
        _logger.log(
            self.log_level,
            "Loading module %s (%d/%d)",
            self.name,
            self.index,
            self.module_count,
        )

    def run_pre_migration(self) -> None:
        if not self.operation:
            return
        if self.operation == "upgrade":
            if self.name != "base":
                self.registry.setup_models(self.env.cr, [], skip_if_clean=True)
            with _debug.perf(
                "modules.migration", cr=self.cr, module=self.name, stage="pre"
            ):
                self.migrations.migrate_module(self.package, "pre")
        if self.name != "base":
            with _debug.perf("modules.package.pre_flush", cr=self.cr, module=self.name):
                self.env.flush_all()

    def import_python_module(self) -> None:
        load_odoo_module(self.name)
        self.py_module = sys.modules[f"odoo.addons.{self.name}"]

    def run_pre_init_hook(self) -> None:
        if self.operation != "install":
            return
        if pre_init := self.package.manifest.get("pre_init_hook"):
            self.registry.setup_models(self.env.cr, [], skip_if_clean=True)
            with _debug.perf(
                "modules.hook", cr=self.cr, module=self.name, hook=pre_init
            ):
                getattr(self.py_module, pre_init)(self.env)

    def load_models(self) -> None:
        registry, package = self.registry, self.package
        with _debug.perf(
            "modules.package.registry_load", cr=self.cr, module=self.name
        ) as span:
            model_names: OrderedSet[str] = OrderedSet(registry.load(package))
            span.set(models=len(model_names))
        declared = len(model_names)  # debuglog

        if self.operation:
            model_names = registry.get_descendants(model_names, "_inherit", "_inherits")
            self.models_updated.update(model_names)
            self.models_to_check -= model_names
            registry.setup_models(self.cr, [], skip_if_clean=True)
            with _debug.perf(
                "modules.package.init_models",
                cr=self.cr,
                module=self.name,
                models=len(model_names),
                install=self.operation == "install",
            ):
                registry.init_models(
                    self.cr,
                    model_names,
                    {"module": package.name},
                    self.operation == "install",
                )
        elif self.update_module and package.state != "to remove":
            model_names = registry.get_descendants(model_names, "_inherit", "_inherits")
            self.models_to_check |= model_names & self.models_updated
        elif self.update_module and package.state == "to remove":
            self.models_to_check |= model_names

        self.model_names = model_names
        _debug.pipeline(
            "modules.package.models_loaded",
            module=self.name,
            models=len(model_names),
            declared=declared,
            operation=self.operation,
            to_check=len(self.models_to_check),
        )

    def load_data_and_demo(self) -> None:
        if not self.operation:
            return
        env, package = self.env, self.package
        self.module = env["ir.module.module"].browse(package.id)
        with _debug.perf("modules.package.check", cr=env.cr, module=self.name):
            self.module._check()

        idref: dict = {}
        with _debug.perf(
            "modules.package.data",
            cr=env.cr,
            module=self.name,
            operation=self.operation,
        ) as span:
            if self.operation == "install":
                load_data(env, idref, "init", kind="data", package=package)
                if self.install_demo and package.demo_installable:
                    package.demo = load_demo(env, package, idref, "init")
            else:
                self.module.write(self.module.get_values_from_terp(package.manifest))
                mode: LoadMode = "update" if self.operation == "upgrade" else "init"
                load_data(env, idref, mode, kind="data", package=package)
                if package.demo:
                    package.demo = load_demo(env, package, idref, mode)
            span.set(idrefs=len(idref), demo=bool(package.demo))
        env.cr.execute(
            "UPDATE ir_module_module SET demo = %s WHERE id = %s",
            (package.demo, package.id),
        )
        self.module.invalidate_model(["demo"])

    def run_post_migration(self) -> None:
        if not self.operation:
            return
        with _debug.perf(
            "modules.migration", cr=self.cr, module=self.name, stage="post"
        ):
            self.migrations.migrate_module(self.package, "post")
        overwrite = tools.config["overwrite_existing_translations"]
        with _debug.perf(
            "modules.package.translations",
            cr=self.cr,
            module=self.name,
            overwrite=overwrite,
        ):
            self.module._update_translations(overwrite=overwrite)

    def mark_module_loaded(self) -> None:
        self.registry.loaded_modules.add(self.name)
        _debug.lifecycle(
            "modules.package.loaded",
            module=self.name,
            loaded=len(self.registry.loaded_modules),
        )

    def run_post_init_hook(self) -> None:
        if self.operation == "install":
            if post_init := self.package.manifest.get("post_init_hook"):
                with _debug.perf(
                    "modules.hook", cr=self.cr, module=self.name, hook=post_init
                ):
                    getattr(self.py_module, post_init)(self.env)
        elif self.operation == "upgrade":
            with _debug.perf(
                "modules.package.check_views", cr=self.cr, module=self.name
            ):
                self.env["ir.ui.view"]._check_module_views(self.name)

    def mark_module_installed(self) -> None:
        if not self.operation:
            return
        env, registry = self.env, self.registry
        _warn_models_without_access_rules(env, self.name, self.model_names, registry)
        registry.updated_modules.append(self.name)

        values: dict[str, str | None] = {
            "state": "installed",
            "db_version": adapt_version(self.package.manifest["version"]),
        }
        if schema.column_exists(env.cr, "ir_module_module", "content_checksum"):
            values["content_checksum"] = get_module_content_checksum(self.name)
        self.module.write(values)

        self.package.state = "installed"
        with _debug.perf("modules.package.commit", cr=self.cr, module=self.name):
            env.flush_all()
            env.cr.commit()
        _debug.lifecycle(
            "modules.package.installed",
            module=self.name,
            operation=self.operation,
            version=values["db_version"],
            checksum="content_checksum" in values,
        )

    def run_at_install_tests(self) -> None:
        update_from_config = (
            tools.config["update"] or tools.config["init"] or tools.config["reinit"]
        )
        if not (
            self.run_tests
            and tools.config["test_enable"]
            and (self.operation or not update_from_config)
        ):
            return

        from odoo.tests import loader

        suite = loader.prepare_suite([self.name], "at_install")
        if not suite.countTestCases():
            _debug.logic(
                "modules.package.at_install_tests.skipped",
                module=self.name,
                reason="no_tests",
            )
            return
        if pending := self._get_installed_not_yet_loaded():
            # The table already carries those modules' columns -- a NOT NULL
            # one has no field in this registry to give it a value -- so the
            # registry cannot represent the schema the tests would write to.
            # The suite runs once it can, after the graph is loaded.
            _debug.logic(
                "modules.package.at_install_tests.skipped",
                module=self.name,
                reason="deferred",
                tests=suite.countTestCases(),
                pending=len(pending),
            )
            _logger.info(
                "Module %s: %d at_install test(s) deferred until %s are loaded",
                self.name,
                suite.countTestCases(),
                ", ".join(pending),
            )
            self.registry.deferred_at_install_modules.append(self.name)
            return
        if not self.operation:
            self.registry.setup_models(self.cr, [], skip_if_clean=True)
        self.registry.check_null_constraints(self.cr)
        tests_t0, tests_q0 = time.time(), odoo.db.sql_counter
        _debug.pipeline(
            "modules.package.at_install_tests",
            module=self.name,
            tests=suite.countTestCases(),
        )
        self.test_results = loader.run_suite(suite, global_report=self.report)
        if self.report is None:
            raise RuntimeError("Missing report during tests")
        self.report.update(self.test_results)
        self.test_time = time.time() - tests_t0
        self.test_queries = odoo.db.sql_counter - tests_q0
        _debug.perf.count(
            "modules.package.at_install_tests.done",
            module=self.name,
            tests=self.test_results.testsRun,
            failures=self.test_results.failures_count,
            errors=self.test_results.errors_count,
            ms=self.test_time * 1000.0,
            queries=self.test_queries,
        )

    def _get_installed_not_yet_loaded(self) -> list[str]:
        return get_installed_not_yet_loaded(
            self.package.module_graph, self.name, self.registry.loaded_modules
        )

    # odoo.db.sql_counter counts every cursor's statements, this one's included;
    # "other" is what ran elsewhere: registry setup cursors, hooks, the tests.
    def log_cost(self) -> None:
        cursor_queries = self.cr.sql_log_count - self.cursor_queries_at_start
        extra_queries = (
            odoo.db.sql_counter
            - self.extra_queries_at_start
            - cursor_queries
            - self.test_queries
        )
        extras = []
        if self.test_queries:
            extras.append(f"+{self.test_queries} test")
        if extra_queries:
            extras.append(f"+{extra_queries} other")
        _logger.log(
            self.log_level,
            "Module %s loaded in %.2fs%s, %s queries%s",
            self.name,
            time.time() - self.started_at,
            f" (incl. {self.test_time:.2f}s test)" if self.test_time else "",
            cursor_queries,
            f" ({', '.join(extras)})" if extras else "",
        )
        _debug.perf.count(
            "modules.package.cost",
            module=self.name,
            index=self.index,
            operation=self.operation,
            ms=(time.time() - self.started_at) * 1000.0,
            queries=cursor_queries,
            extra_queries=extra_queries,
            test_ms=self.test_time * 1000.0,
            test_queries=self.test_queries,
        )
        results = self.test_results
        if results and not results.wasSuccessful():
            _logger.error(
                "Module %s: %d failures, %d errors of %d tests",
                self.name,
                results.failures_count,
                results.errors_count,
                results.testsRun,
            )

    def run(self) -> None:
        self.update_operation()
        self.announce_module()
        self.run_pre_migration()
        self.import_python_module()
        self.run_pre_init_hook()
        self.load_models()
        self.load_data_and_demo()
        self.run_post_migration()
        self.mark_module_loaded()
        self.run_post_init_hook()
        self.mark_module_installed()
        self.run_at_install_tests()
        self.log_cost()


def get_installed_not_yet_loaded(
    graph: ModuleGraph, name: str, loaded: Collection[str]
) -> list[str]:
    """The graph's installed modules that load after ``name``.

    A fresh install has none: a module marked "to install" has no column in any
    table yet, and its own at_install tests are its own. What makes a module
    count is that its schema is already there -- installed, or installed and
    about to upgrade -- while its models are not. Depending on ``name`` is not
    the criterion: mail puts a NOT NULL column on res_users without depending
    on the module whose tests create a user.
    """
    pending = [
        node.name
        for node in graph
        if node.name not in loaded and node.state in ("installed", "to upgrade")
    ]
    if name == "base":
        # The bootstrap graph holds base alone; the database names the rest.
        pending.extend(
            module
            for module in graph.installed_outside()
            if module not in loaded and module not in pending
        )
    return pending


def _run_gc_cycle(registry: Registry, cycles: int) -> int:
    young = gc.get_count()[0]
    if young <= _GC_YOUNG_BACKLOG_LIMIT:
        return cycles
    registry.clear_all_caches()
    cycles += 1
    with _debug.perf(
        "modules.gc_cycle",
        cycle=cycles,
        full=cycles % _GC_FULL_CYCLE_EVERY == 0,
        young=young,
    ):
        if cycles % _GC_FULL_CYCLE_EVERY == 0:
            gc.unfreeze()
            gc.collect()
        else:
            gc.collect(generation=1)
        gc.freeze()
    return cycles


def load_module_graph(
    env: Environment,
    graph: ModuleGraph,
    update_module: bool = False,
    report: OdooTestResult | None = None,
    models_to_check: OrderedSet[str] | None = None,
    install_demo: bool = True,
    run_tests: bool = True,
    migrations: MigrationManager | None = None,
) -> None:
    if models_to_check is None:
        models_to_check = OrderedSet()

    registry = env.registry
    cr = env.cr
    if not isinstance(cr, odoo.db.Cursor):
        raise TypeError("Need for a real Cursor to load modules")
    if migrations is None:
        migrations = MigrationManager(cr, graph)
    module_count = len(graph)
    _logger.info("loading %d modules...", module_count)
    _debug.pipeline(
        "modules.load_graph.begin",
        modules=module_count,
        already_loaded=len(registry.loaded_modules),
        update_module=update_module,
        run_tests=run_tests,
    )

    t0 = time.time()
    extra_queries_at_start = odoo.db.sql_counter
    cursor_queries_at_start = cr.sql_log_count

    models_updated: set[str] = set()
    gc_cycles = 0
    skipped = 0  # debuglog

    try:
        for index, package in enumerate(graph, 1):
            if package.name in registry.loaded_modules:
                skipped += 1  # debuglog
                continue
            _PackageLoader(
                env,
                cr,
                package,
                index=index,
                module_count=module_count,
                migrations=migrations,
                update_module=update_module,
                install_demo=install_demo,
                run_tests=run_tests,
                report=report,
                models_to_check=models_to_check,
                models_updated=models_updated,
            ).run()
            env.invalidate_all()
            gc_cycles = _run_gc_cycle(registry, gc_cycles)
    finally:
        gc.unfreeze()

    cursor_queries = cr.sql_log_count - cursor_queries_at_start
    extra_queries = odoo.db.sql_counter - extra_queries_at_start - cursor_queries
    _logger.log(
        RUNBOT,
        "%s modules loaded in %.2fs, %s queries (+%s extra)",
        len(graph),
        time.time() - t0,
        cursor_queries,
        extra_queries,
    )
    _debug.perf.count(
        "modules.load_graph.done",
        modules=module_count,
        skipped=skipped,
        ms=(time.time() - t0) * 1000.0,
        queries=cursor_queries,
        extra_queries=extra_queries,
        gc_cycles=gc_cycles,
        models_updated=len(models_updated),
        to_check=len(models_to_check),
    )


def _warn_invalid_module_names(cr: BaseCursor, module_names: Iterable[str]) -> None:
    mod_names = set(module_names)
    mod_names.discard("all")
    if mod_names:
        cr.execute(
            "SELECT count(id) AS count FROM ir_module_module WHERE name = ANY(%s)",
            (list(mod_names),),
        )
        row = cr.fetchone()
        if row is None:
            raise RuntimeError("count(id) over ir_module_module returned no row")
        if row[0] != len(mod_names):
            cr.execute("SELECT name FROM ir_module_module")
            incorrect_names = mod_names.difference(name for [name] in cr.fetchall())
            _debug.logic(
                "modules.invalid_module_names",
                requested=len(mod_names),
                invalid=",".join(sorted(incorrect_names)),
            )
            _logger.warning(
                "invalid module names, ignored: %s", ", ".join(incorrect_names)
            )


def _run_deferred_at_install_tests(
    registry: Registry,
    cr: Cursor,
    env: Environment,
    report: OdooTestResult | None,
) -> None:
    names = registry.deferred_at_install_modules
    if not names:
        return
    from odoo.tests import loader

    _debug.pipeline("modules.deferred_tests.begin", modules=len(names))
    registry.check_null_constraints(cr)
    # The tests open their own connections; anything this transaction still
    # holds -- the module-list update, the upgrade marking, every row it read
    # -- blocks their DDL and their module-state writes for good. The
    # non-deferred path commits in `mark_module_installed` before its tests.
    env.flush_all()
    cr.commit()
    _debug.lifecycle("modules.deferred_tests.committed", modules=len(names))
    for name in names:
        suite = loader.prepare_suite([name], "at_install")
        _logger.info(
            "Module %s: running %d deferred at_install test(s)",
            name,
            suite.countTestCases(),
        )
        tests_t0, tests_q0 = time.time(), odoo.db.sql_counter
        results = loader.run_suite(suite, global_report=report)
        if report is None:
            raise RuntimeError("Missing report during tests")
        report.update(results)
        _logger.info(
            "Module %s: %d deferred at_install test(s) in %.2fs, %s queries",
            name,
            results.testsRun,
            time.time() - tests_t0,
            odoo.db.sql_counter - tests_q0,
        )
        _debug.perf.count(
            "modules.deferred_tests.module",
            module=name,
            tests=results.testsRun,
            failures=results.failures_count,
            errors=results.errors_count,
            ms=(time.time() - tests_t0) * 1000.0,
            queries=odoo.db.sql_counter - tests_q0,
        )
        if not results.wasSuccessful():
            _logger.error(
                "Module %s: %d failures, %d errors of %d tests",
                name,
                results.failures_count,
                results.errors_count,
                results.testsRun,
            )
        env.invalidate_all()
    names.clear()


def _drop_not_null_on_removed_columns(
    env: Environment, cr: BaseCursor, models: list[str]
) -> None:
    tables = {env[model]._table for model in models if not env[model]._abstract}
    if not tables:
        return
    with _debug.perf(
        "modules.removed_columns", cr=cr, models=len(models), tables=len(tables)
    ) as span:
        cr.execute(
            """
            SELECT c.relname AS table_name,
                   a.attname AS column_name,
                   CASE WHEN a.attnotnull THEN 'NO' ELSE 'YES' END AS is_nullable
              FROM pg_attribute a
              JOIN pg_class c ON a.attrelid = c.oid
             WHERE c.relname = ANY(%s)
               AND c.relnamespace = current_schema::regnamespace
               AND a.attnum > 0
               AND NOT a.attisdropped
            """,
            [list(tables)],
        )
        columns_by_table: dict[str, dict[str, str]] = {}
        for table_name, column_name, is_nullable in cr.fetchall():
            columns_by_table.setdefault(table_name, {})[column_name] = is_nullable

        orphans = dropped = 0  # debuglog
        for model in models:
            Model = env[model]
            if Model._abstract:
                continue
            cols = {name for name, field in Model._fields.items() if field.is_column}
            for col_name, is_nullable in columns_by_table.get(Model._table, {}).items():
                if col_name in cols:
                    continue
                orphans += 1  # debuglog
                _logger.debug(
                    "column %s is in the table %s but not in the corresponding object %s",
                    col_name,
                    Model._table,
                    model,
                )
                if is_nullable == "NO":
                    dropped += 1  # debuglog
                    _debug.lifecycle(
                        "modules.removed_column.not_null_dropped",
                        model=model,
                        table=Model._table,
                        column=col_name,
                    )
                    schema.drop_not_null(cr, Model._table, col_name)
        span.set(orphans=orphans, dropped=dropped)


class _UninstallRequiresReload(Exception):
    pass


class _ModuleLoader:
    __slots__ = (
        "cr",
        "env",
        "graph",
        "install_modules",
        "migrations",
        "models_to_check",
        "new_db_demo",
        "registry",
        "reinit_modules",
        "report",
        "run_tests",
        "update_module",
        "upgrade_modules",
    )

    def __init__(
        self,
        registry: Registry,
        cr: Cursor,
        *,
        update_module: bool,
        upgrade_modules: Collection[str],
        install_modules: Collection[str],
        reinit_modules: Collection[str],
        new_db_demo: bool,
        models_to_check: OrderedSet[str],
        run_tests: bool = True,
    ) -> None:
        self.registry = registry
        self.cr = cr
        self.run_tests = run_tests
        self.update_module = update_module
        self.upgrade_modules = upgrade_modules
        self.install_modules = install_modules
        self.reinit_modules = reinit_modules
        self.new_db_demo = new_db_demo
        self.models_to_check = models_to_check
        self.graph: ModuleGraph = None  # type: ignore[assignment]
        self.env: Environment = None  # type: ignore[assignment]
        self.report: OdooTestResult | None = None
        self.migrations: MigrationManager = None  # type: ignore[assignment]

    def bootstrap(self) -> bool:
        cr = self.cr
        cr.execute("SET SESSION lock_timeout = '15s'")
        initialized = modules_db.is_initialized(cr)
        _debug.logic(
            "modules.bootstrap.decision",
            db=cr.dbname,
            initialized=initialized,
            update_module=self.update_module,
            base_upgrade="base" in self.upgrade_modules,
            base_reinit="base" in self.reinit_modules,
        )
        if not initialized:
            if not self.update_module:
                _logger.info(
                    "Database %s not initialized, skipping (use `-i base` to bootstrap).",
                    cr.dbname,
                )
                return False
            _logger.info("Initializing database %s", cr.dbname)
            with _debug.perf("modules.bootstrap.initialize", cr=cr, db=cr.dbname):
                modules_db.initialize(cr)
        elif "base" in self.reinit_modules:
            self.registry.loading.reinit_modules.add("base")

        if "base" in self.upgrade_modules:
            cr.execute(
                "update ir_module_module set state=%s where name=%s and state=%s",
                ("to upgrade", "base", "installed"),
            )
            _debug.lifecycle(
                "modules.bootstrap.base_marked_to_upgrade", marked=cr.rowcount == 1
            )

        self.graph = ModuleGraph(cr, mode="update" if self.update_module else "load")
        self.graph.extend(["base"])
        _debug.pipeline(
            "modules.bootstrap",
            db=cr.dbname,
            update_module=self.update_module,
            upgrade=len(self.upgrade_modules),
            install=len(self.install_modules),
            reinit=len(self.reinit_modules),
        )
        if not self.graph:
            _logger.critical("module base cannot be loaded! (hint: verify addons-path)")
            msg = "Module `base` cannot be loaded! (hint: verify addons-path)"
            raise ImportError(msg)
        return True

    def run_pre_upgrade_scripts(self) -> None:
        if not (self.update_module and self.upgrade_modules):
            return
        scripts = tools.config["pre_upgrade_scripts"]
        _debug.pipeline(
            "modules.pre_upgrade_scripts",
            scripts=len(scripts),
            base_version=self.graph["base"].db_version,
        )
        for pyfile in scripts:
            odoo.modules.migration.run_migration_script(
                self.cr, self.graph["base"].db_version or "", pyfile, "base", "pre"
            )

    def capture_database_field_metadata(self) -> None:
        if not (self.update_module and schema.table_exists(self.cr, "ir_model_fields")):
            return
        with _debug.perf("modules.reflect_database_fields", cr=self.cr):
            self.registry.reflect_database_fields(self.cr)

    def open_environment_and_load_base(self) -> None:
        self.report = None
        if tools.config["test_enable"]:
            from odoo.tests.result import assertion_report

            self.report = assertion_report(self.registry.db_name)
        self.env = api.Environment(self.cr, api.SUPERUSER_ID, {})
        self.env.transaction.default_env = self.env
        self.migrations = MigrationManager(self.cr, self.graph)
        _debug.lifecycle(
            "modules.environment_opened",
            db=self.registry.db_name,
            test_report=self.report is not None,
            migrations=len(self.migrations.migrations),
        )
        load_module_graph(
            self.env,
            self.graph,
            update_module=self.update_module,
            report=self.report,
            models_to_check=self.models_to_check,
            install_demo=self.new_db_demo,
            run_tests=self.run_tests,
            migrations=self.migrations,
        )

    def load_languages(self) -> None:
        load_lang = tools.config.get("load_language")
        lang_pending = bool(load_lang) and not self.registry.loading.load_language_done
        _debug.logic(
            "modules.load_languages",
            requested=load_lang or None,
            pending=lang_pending,
            update_module=self.update_module,
        )
        if lang_pending or self.update_module:
            self.registry.setup_models(self.cr, [], skip_if_clean=True)

        if lang_pending:
            for lang in load_lang.split(","):
                with _debug.perf("modules.load_language", cr=self.cr, lang=lang):
                    tools.translate.load_language(self.cr, lang)
            self.registry.loading.load_language_done = True

    def apply_module_requests(self) -> None:
        if not self.update_module:
            return
        env = self.env
        cr = self.cr
        Module = env["ir.module.module"]
        _logger.info("updating modules list")
        with _debug.perf("modules.update_list", cr=cr):
            Module.update_list()

        _warn_invalid_module_names(
            cr, itertools.chain(self.install_modules, self.upgrade_modules)
        )

        if self.install_modules:
            modules = Module.search(
                [
                    ("state", "=", "uninstalled"),
                    ("name", "in", tuple(self.install_modules)),
                ]
            )
            _debug.logic(
                "modules.request",
                kind="install",
                requested=len(self.install_modules),
                matched=len(modules),
            )
            if modules:
                with _debug.perf("modules.button_install", cr=cr, modules=len(modules)):
                    modules.button_install()

        if self.upgrade_modules:
            modules = Module.search(
                [
                    ("state", "in", ("installed", "to upgrade")),
                    ("name", "in", tuple(self.upgrade_modules)),
                ]
            )
            _debug.logic(
                "modules.request",
                kind="upgrade",
                requested=len(self.upgrade_modules),
                matched=len(modules),
            )
            if modules:
                with _debug.perf("modules.button_upgrade", cr=cr, modules=len(modules)):
                    modules.button_upgrade()

        if self.reinit_modules:
            modules = Module.search(
                [
                    ("state", "in", ("installed", "to upgrade")),
                    ("name", "in", tuple(self.reinit_modules)),
                ]
            )
            reinit_records = (
                modules.downstream_dependencies(
                    exclude_states=(
                        "uninstalled",
                        "uninstallable",
                        "to remove",
                        "to install",
                    )
                )
                + modules
            )
            self.registry.loading.reinit_modules.update(
                m
                for m in reinit_records.mapped("name")
                if m not in self.graph._imported_modules
            )
            _debug.logic(
                "modules.request",
                kind="reinit",
                requested=len(self.reinit_modules),
                matched=len(modules),
                downstream=len(reinit_records) - len(modules),
                marked=len(self.registry.loading.reinit_modules),
            )

        env.flush_all()
        cr.execute(
            "update ir_module_module set state=%s where name=%s",
            ("installed", "base"),
        )
        Module.invalidate_model(["state"])
        _debug.pipeline(
            "modules.requests_applied",
            install=len(self.install_modules),
            upgrade=len(self.upgrade_modules),
            reinit=len(self.registry.loading.reinit_modules),
        )

    def converge_module_graph(self) -> None:
        env = self.env
        iteration = 0  # debuglog
        while True:
            iteration += 1  # debuglog
            states: tuple[str, ...] = ("installed", "to upgrade", "to remove")
            if self.update_module:
                states += ("to install",)
            env.cr.execute(
                "SELECT name from ir_module_module WHERE state = ANY(%s)",
                [list(states)],
            )
            module_list = [
                name for (name,) in env.cr.fetchall() if name not in self.graph
            ]
            _debug.pipeline(
                "modules.converge",
                iteration=iteration,
                new=len(module_list),
                graph=len(self.graph),
                updated=len(self.registry.updated_modules),
            )
            if not module_list:
                _debug.logic(
                    "modules.converge.stop",
                    iteration=iteration,
                    reason="no_new_modules",
                    graph=len(self.graph),
                )
                break
            self.graph.extend(module_list)
            _logger.debug("Updating graph with %d more modules", len(module_list))
            updated_modules_count = len(self.registry.updated_modules)
            self.migrations.index_migration_scripts()
            load_module_graph(
                env,
                self.graph,
                update_module=self.update_module,
                report=self.report,
                models_to_check=self.models_to_check,
                run_tests=self.run_tests,
                migrations=self.migrations,
            )
            if len(self.registry.updated_modules) == updated_modules_count:
                _debug.logic(
                    "modules.converge.stop",
                    iteration=iteration,
                    reason="no_progress",
                    graph=len(self.graph),
                    requested=len(module_list),
                    kept=sum(1 for name in module_list if name in self.graph),
                )
                break

    def untranslate_dropped_fields(self) -> None:
        if not self.update_module:
            return
        registry = self.registry
        database_translated_fields = registry.take_database_translated_fields()
        registry.setup_models(self.cr, [], skip_if_clean=True)
        models_to_untranslate = set()
        for full_name in database_translated_fields:
            model_name, field_name = full_name.rsplit(".", 1)
            if model_name in registry:
                field = registry[model_name]._fields.get(field_name)
                if field and not field.translate:
                    _logger.debug("Making field %s non-translated", field)
                    models_to_untranslate.add(model_name)
        _debug.logic(
            "modules.untranslate_dropped_fields",
            candidates=len(database_translated_fields),
            models=len(models_to_untranslate),
        )
        registry.init_models(
            self.cr, list(models_to_untranslate), {"models_to_check": True}
        )

    def finalize_registry_setup(self) -> None:
        self.registry.loaded = True
        with _debug.perf(
            "modules.finalize_registry_setup", cr=self.cr, models=len(self.registry)
        ):
            self.registry.setup_models(self.cr)

    def run_deferred_at_install_tests(self) -> None:
        _run_deferred_at_install_tests(self.registry, self.cr, self.env, self.report)

    def log_modules_that_never_loaded(self) -> None:
        Module = self.env["ir.module.module"]
        modules = Module.search_fetch(
            Module._get_domain_modules_to_load(), ["name"], order="name"
        )
        missing = [name for name in modules.mapped("name") if name not in self.graph]
        _debug.logic(
            "modules.never_loaded",
            to_load=len(modules),
            graph=len(self.graph),
            missing=len(missing),
        )
        if missing:
            _logger.error(
                "Some modules are not loaded, some dependencies or manifest may be missing: %s",
                missing,
            )

    def run_end_migrations(self) -> None:
        if not self.update_module:
            return
        with _debug.perf("modules.end_migrations", cr=self.cr, modules=len(self.graph)):
            for package in self.graph:
                self.migrations.migrate_module(package, "end")

    def restore_relations_dropped_by_migrations(self) -> None:
        if not self.registry.updated_modules:
            return
        self.registry.check_tables_exist(self.cr)
        env = self.env
        queried = {
            model._table: name
            for name, model in self.registry.items()
            if not model._abstract and env[name]._table_query
        }
        missing = set(queried).difference(schema.get_tables_existing(self.cr, queried))
        for table in sorted(missing):
            env[queried[table]].init()
        env.flush_all()

    def log_pending_module_states(self) -> None:
        cr = self.cr
        cr.execute(
            "SELECT name, state FROM ir_module_module WHERE state IN ('to install', 'to upgrade')"
        )
        pending = cr.fetchall()
        _debug.logic(
            "modules.pending_states",
            update_module=self.update_module,
            to_install=sum(1 for _name, state in pending if state == "to install"),
            to_upgrade=sum(1 for _name, state in pending if state == "to upgrade"),
        )
        if pending and self.update_module:
            _logger.error(
                "Some modules have inconsistent states after upgrade, "
                "some dependencies may be missing: %s",
                sorted(name for name, _state in pending),
            )
        elif pending:
            to_install = sorted(
                name for name, state in pending if state == "to install"
            )
            to_upgrade = sorted(
                name for name, state in pending if state == "to upgrade"
            )
            if to_upgrade:
                _logger.warning(
                    "Modules pending upgrade (restart with -u to process): %s",
                    to_upgrade,
                )
            if to_install:
                _logger.info(
                    "Modules pending installation (restart with -i or -u to process): %s",
                    to_install,
                )

    def finalize_constraints(self) -> None:
        with _debug.perf("modules.finalize_constraints", cr=self.cr):
            self.registry.finalize_constraints(self.cr)

    def _check_removed_columns(self, models: list[str]) -> None:
        _drop_not_null_on_removed_columns(self.env, self.cr, models)

    def run_post_update_model_checks(self) -> None:
        if not self.registry.updated_modules:
            return
        env = self.env
        cr = self.cr
        cr.execute("SELECT model from ir_model")
        checked_models = []
        unloadable = 0  # debuglog
        for (model,) in cr.fetchall():
            if model in self.registry:
                checked_models.append(model)
            else:
                unloadable += 1  # debuglog
                _logger.log(
                    RUNBOT,
                    "Model %s is declared but cannot be loaded! (Perhaps a module was partially removed or renamed)",
                    model,
                )
        _debug.pipeline(
            "modules.post_update_checks",
            updated_modules=len(self.registry.updated_modules),
            models=len(checked_models),
            unloadable=unloadable,
        )
        self._check_removed_columns(checked_models)

        self._reflect_inherits_across_the_whole_registry()

        with _debug.perf(
            "modules.process_end",
            cr=cr,
            modules=len(self.registry.updated_modules),
            xmlids_written=len(self.registry.loading.xmlids_written),
        ):
            self.registry.xmlids.finish_load(env, self.registry.updated_modules)
        self.registry.loading.xmlids_written.clear()
        vacuum_cron = typing.cast(
            "IrCronProtocol | None",
            env.ref("base.autovacuum_job", raise_if_not_found=False),
        )
        _debug.logic("modules.autovacuum_trigger", found=vacuum_cron is not None)
        if vacuum_cron:
            trigger_at = datetime.datetime.now(datetime.UTC).replace(
                tzinfo=None
            ) + datetime.timedelta(minutes=1)
            vacuum_cron._trigger(at=trigger_at)

        env.flush_all()

    def _reflect_inherits_across_the_whole_registry(self) -> None:
        if not self.registry.updated_modules:
            return
        with (
            _debug.perf(
                "modules.reflect_inherits", cr=self.cr, models=len(self.registry.models)
            ),
            self.registry.init_models_window(install=False),
        ):
            self.registry.metaschema.reflect_inherits(
                self.env, list(self.registry.models)
            )

    def uninstall_removed_modules(self) -> None:
        if not self.update_module:
            return
        env = self.env
        cr = self.cr
        cr.execute(
            "SELECT name, id FROM ir_module_module WHERE state=%s",
            ("to remove",),
        )
        modules_to_remove = dict(cr.fetchall())
        if not modules_to_remove:
            return
        _debug.pipeline(
            "modules.uninstall.begin",
            modules=len(modules_to_remove),
            names=",".join(sorted(modules_to_remove)[:8]),
        )

        pkgs = reversed([p for p in self.graph if p.name in modules_to_remove])
        for pkg in pkgs:
            uninstall_hook = pkg.manifest.get("uninstall_hook")
            if uninstall_hook:
                py_module = sys.modules[f"odoo.addons.{pkg.name}"]
                with _debug.perf(
                    "modules.hook", cr=cr, module=pkg.name, hook=uninstall_hook
                ):
                    getattr(py_module, uninstall_hook)(env)
                    env.flush_all()

        Module = env["ir.module.module"]
        with _debug.perf("modules.uninstall", cr=cr, modules=len(modules_to_remove)):
            Module.browse(modules_to_remove.values()).module_uninstall()
            cr.commit()
        _debug.lifecycle("modules.uninstall.reload_required", db=cr.dbname)
        raise _UninstallRequiresReload

    def collect_models_with_manual_fields(self) -> None:
        if not self.update_module:
            return
        self.cr.execute(
            """SELECT DISTINCT model FROM ir_model_fields WHERE state = 'manual'"""
        )
        rows = self.cr.fetchall()
        before = len(self.models_to_check)  # debuglog
        self.models_to_check.update(
            model_name for (model_name,) in rows if model_name in self.registry
        )
        _debug.logic(
            "modules.manual_fields",
            models=len(rows),
            added=len(self.models_to_check) - before,
            to_check=len(self.models_to_check),
        )

    def reinit_models_to_check(self) -> None:
        if not self.models_to_check:
            return
        models = [model for model in self.models_to_check if model in self.registry]
        with _debug.perf(
            "modules.reinit_models_to_check",
            cr=self.cr,
            models=len(models),
            unknown=len(self.models_to_check) - len(models),
        ):
            self.registry.init_models(
                self.cr,
                models,
                {"models_to_check": True, "update_custom_fields": True},
            )

    def warn_invalid_custom_views(self) -> None:
        if not self.update_module:
            return
        View = self.env["ir.ui.view"].with_context(load_all_views=True)
        with _debug.perf(
            "modules.custom_views_check", cr=self.cr, models=len(self.registry)
        ) as span:
            custom_views = View._get_custom_views().grouped("model")
            invalid = 0  # debuglog
            for model, views in custom_views.items():
                if model not in self.registry:
                    continue
                try:
                    views._check_xml()
                except Exception as e:
                    invalid += 1  # debuglog
                    _logger.warning("invalid custom view(s) for model %s: %s", model, e)
            span.set(custom=len(custom_views), invalid=invalid)

    def log_assertion_report(self) -> None:
        report = self.report
        if not report or report.wasSuccessful():
            _logger.info("Modules loaded.")
        else:
            _logger.error("At least one test failed when loading the modules.")
        _debug.lifecycle(
            "modules.loaded",
            db=self.registry.db_name,
            update_module=self.update_module,
            updated_modules=len(self.registry.updated_modules),
            graph=len(self.graph),
            tests=report.testsRun if report else 0,
            failures=report.failures_count if report else 0,
            errors=report.errors_count if report else 0,
        )

    def register_model_hooks(self) -> None:
        with _debug.perf(
            "modules.register_hooks", cr=self.cr, models=len(self.registry)
        ):
            for model in self.env.values():
                model._register_hook()
            self.env.flush_all()

    def check_null_constraints(self) -> None:
        with _debug.perf("modules.check_null_constraints", cr=self.cr):
            self.registry.check_null_constraints(self.cr)

    def mark_database_partially_updated(self) -> None:
        if not self.update_module:
            return
        self.cr.execute("""
            INSERT INTO ir_config_parameter(key, value)
            SELECT 'base.partially_updated_database', '1'
            WHERE EXISTS(SELECT FROM ir_module_module WHERE state IN ('to upgrade', 'to install', 'to remove'))
            ON CONFLICT DO NOTHING
            """)
        _debug.lifecycle(
            "modules.partially_updated", db=self.cr.dbname, marked=self.cr.rowcount == 1
        )


def load_modules(
    registry: Registry,
    *,
    update_module: bool = False,
    upgrade_modules: Collection[str] = (),
    install_modules: Collection[str] = (),
    reinit_modules: Collection[str] = (),
    new_db_demo: bool = False,
    models_to_check: OrderedSet[str] | None = None,
    run_tests: bool = True,
) -> None:
    if models_to_check is None:
        models_to_check = OrderedSet()

    initialize_sys_path()

    with (
        registry.cursor() as cr,
        _debug.perf(
            "modules.load_modules",
            cr=cr,
            db=registry.db_name,
            update_module=update_module,
            install=len(install_modules),
            upgrade=len(upgrade_modules),
            reinit=len(reinit_modules),
            run_tests=run_tests,
        ) as span,
    ):
        if not isinstance(cr, odoo.db.Cursor):
            raise TypeError("Need a real Cursor to load modules")
        cr.execute("SET idle_session_timeout = 0")
        loader = _ModuleLoader(
            registry,
            cr,
            update_module=update_module,
            upgrade_modules=upgrade_modules,
            install_modules=install_modules,
            reinit_modules=reinit_modules,
            new_db_demo=new_db_demo,
            models_to_check=models_to_check,
            run_tests=run_tests,
        )

        if not loader.bootstrap():
            span.set(outcome="not_initialized")
            return

        loader.run_pre_upgrade_scripts()
        loader.capture_database_field_metadata()
        loader.open_environment_and_load_base()
        loader.load_languages()
        loader.apply_module_requests()
        loader.converge_module_graph()
        loader.untranslate_dropped_fields()
        loader.finalize_registry_setup()
        loader.run_deferred_at_install_tests()
        loader.log_modules_that_never_loaded()
        loader.run_end_migrations()
        loader.restore_relations_dropped_by_migrations()
        loader.log_pending_module_states()
        loader.finalize_constraints()
        loader.run_post_update_model_checks()

        try:
            loader.uninstall_removed_modules()
        except _UninstallRequiresReload:
            _logger.info("Reloading registry once more after uninstalling modules")
            span.set(outcome="reload_after_uninstall")
            Registry.new(
                cr.dbname,
                update_module=update_module,
                models_to_check=models_to_check,
            )
            return

        loader.collect_models_with_manual_fields()
        loader.reinit_models_to_check()
        loader.warn_invalid_custom_views()
        loader.log_assertion_report()
        loader.register_model_hooks()
        loader.check_null_constraints()
        loader.mark_database_partially_updated()
        span.set(outcome="loaded", modules=len(loader.graph))


def reset_modules_state(db_name: str) -> None:
    db = odoo.db.db_connect(db_name)
    with db.cursor() as cr:
        if not schema.table_exists(cr, "ir_module_module"):
            _debug.logic("modules.reset_state.skipped", db=db_name)
            _logger.info(
                "skipping reset_modules_state, ir_module_module table does not exist"
            )
            return
        cr.execute(
            "UPDATE ir_module_module SET state='installed' WHERE state IN ('to remove', 'to upgrade')"
        )
        reset_count = cr.rowcount
        cr.execute(
            "UPDATE ir_module_module SET state='uninstalled' WHERE state='to install'"
        )
        reset_count += cr.rowcount
        _debug.lifecycle(
            "modules.reset_state",
            db=db_name,
            reset=reset_count,
            to_uninstalled=cr.rowcount,
        )
        if reset_count:
            _logger.warning(
                "Transient module states were reset (%d modules)", reset_count
            )
