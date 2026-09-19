import logging
import threading
import time
import types
import typing
from collections.abc import Collection, Hashable, Iterable, Mapping
from contextlib import ExitStack, closing, nullcontext

import psycopg

from odoo import db
from odoo.db import schema as sql
from odoo.db.replica import ReplicaRouter, is_readonly_cursor_enabled
from odoo.libs import gc
from odoo.libs.debug_log import DebugLog
from odoo.libs.func import locked, reset_cached_properties
from odoo.libs.lru import LRU
from odoo.libs.memory_watch import read_rss
from odoo.libs.worker_thread import current_worker_thread
from odoo.tools import OrderedSet, config
from odoo.tools.cache import remove_counters
from odoo.tools.constants import CACHES_BY_KEY
from odoo.tools.translate import code_translations

from .. import models, registration
from ..primitives import SUPERUSER_ID
from ._registry_capabilities import (
    _RegistryCapabilitiesMixin,
    clear_all_text_transforms,
    clear_text_transforms,
)
from ._registry_fields import _RegistryFieldsMixin
from ._registry_init_phase import _RegistryInitPhaseMixin
from ._registry_loading_phase import _RegistryLoadingPhaseMixin
from ._registry_models import _RegistryModelsMixin
from ._registry_schema import _RegistrySchemaMixin
from ._registry_signaling import _RegistrySignalingMixin
from .access_policy import ACCESS_POLICY, AccessPolicy
from .filestore import FILE_STORE, FileStore
from .locale import LOCALE, Locale
from .metaschema import META_SCHEMA, MetaSchema
from .settings import SYSTEM_SETTINGS, SystemSettings
from .xmlids import XMLIDS, Xmlids

if typing.TYPE_CHECKING:
    from odoo.db import BaseCursor, Cursor
    from odoo.models import BaseModel
    from odoo.modules import module_graph


_logger = logging.getLogger("odoo.registry")
_schema = logging.getLogger("odoo.schema")
_debug = DebugLog(__name__)


class Registry(
    _RegistryFieldsMixin,
    _RegistrySchemaMixin,
    _RegistryModelsMixin,
    _RegistryInitPhaseMixin,
    _RegistryLoadingPhaseMixin,
    _RegistryCapabilitiesMixin,
    _RegistrySignalingMixin,
    Mapping[str, type["BaseModel"]],
):
    _lock: threading.RLock | DummyRLock = threading.RLock()

    registries = LRU[str, "Registry"](42)

    idle_timeout: float = 0

    last_used: float

    _replica: ReplicaRouter

    def __new__(cls, db_name: str):
        if not db_name:
            raise ValueError("Missing database name")
        reg = cls.registries.get(db_name)
        if reg is not None and reg.ready:
            reg.last_used = time.monotonic()
            return reg
        with cls._lock:
            try:
                registry = cls.registries[db_name]
                registry.last_used = time.monotonic()
                return registry
            except KeyError:
                return cls.new(db_name)

    ready: bool
    loaded: bool
    metaschema: MetaSchema = META_SCHEMA
    access_policy: AccessPolicy = ACCESS_POLICY
    xmlids: Xmlids = XMLIDS
    file_store: FileStore = FILE_STORE
    settings: SystemSettings = SYSTEM_SETTINGS
    locale: Locale = LOCALE

    @classmethod
    def _new_finalize(cls, db_name: str, update_module: bool, t0: float) -> Registry:
        registry = cls.registries[db_name]

        registry.ready = True
        registry.registry_invalidated = bool(update_module)

        registry._get_field_triggers()

        if update_module:
            db.drain_all()
        registry.signal_changes()

        _logger.info("Registry loaded in %.3fs", time.time() - t0)
        _debug.lifecycle(
            "registry.ready",
            db=db_name,
            models=len(registry.models),
            modules=len(registry.loaded_modules),
            updated=len(registry.updated_modules),
            update_module=update_module,
        )
        registry.last_used = time.monotonic()
        cls._evict_idle_registries()
        gc.freeze_survivors()
        return registry

    @classmethod
    @locked
    def new(
        cls,
        db_name: str,
        *,
        update_module: bool = False,
        install_modules: Collection[str] = (),
        upgrade_modules: Collection[str] = (),
        reinit_modules: Collection[str] = (),
        new_db_demo: bool | None = None,
        models_to_check: OrderedSet[str] | None = None,
        run_tests: bool = True,
    ) -> Registry:
        if db.is_maintenance_db(db_name):
            raise ValueError(
                f"Refusing to build a registry over system or template "
                f"database {db_name!r}"
            )
        t0 = time.time()
        lru_size = config.get("registry_lru_size")
        if lru_size and cls.registries.count != lru_size:
            cls.registries.count = lru_size
        registry: Registry = object.__new__(cls)
        registry.init(db_name)
        registry.new = registry.init = registry.registries = None  # type: ignore[method-assign, assignment]
        first_registry = not cls.registries
        _debug.lifecycle(
            "registry.new",
            db=db_name,
            first=first_registry,
            update_module=update_module,
            install=len(install_modules),
            upgrade=len(upgrade_modules),
            reinit=len(reinit_modules),
            registries=len(cls.registries),
        )

        cls.remove(db_name)
        cls.registries[db_name] = registry

        # Code translations are cached in a process-global, outside the
        # registry, and `_load_module_terms` clears them only in the worker
        # that performs the install or upgrade. Every other worker learns of
        # the change by rebuilding its registry -- which is here -- and would
        # otherwise keep serving the `.po` it read before the module changed
        # on disk. With several workers that means the language a user sees
        # depends on which one answers.
        #
        # Dropping the whole cache is the honest scope: a rebuild means the
        # addons directory may have moved under us, and the entries are read
        # back lazily from disk on the next request that needs them.
        code_translations.clear()

        try:
            registry.setup_signaling()
            with registry.cursor() as cr:
                if sql.table_exists(cr, "ir_module_module"):
                    cr.execute(
                        "DELETE FROM ir_config_parameter WHERE key='base.partially_updated_database'"
                    )
                    if cr.rowcount:
                        update_module = True
            from odoo.modules.loading import (
                load_modules,
                reset_modules_state,
            )

            exit_stack = ExitStack()
            try:
                if upgrade_modules or install_modules or reinit_modules:
                    update_module = True
                if new_db_demo is None:
                    new_db_demo = config["with_demo"]
                if first_registry:
                    exit_stack.enter_context(gc.disabling_gc())
                exit_stack.enter_context(registry.loading_window())
                load_modules(
                    registry,
                    update_module=update_module,
                    upgrade_modules=upgrade_modules,
                    install_modules=install_modules,
                    reinit_modules=reinit_modules,
                    new_db_demo=new_db_demo,
                    models_to_check=models_to_check,
                    run_tests=run_tests,
                )
            except Exception:
                reset_modules_state(db_name)
                raise
            finally:
                exit_stack.close()
        except Exception as exc:
            _logger.error("Failed to load registry")
            _debug.lifecycle(
                "registry.load_failed", db=db_name, error=type(exc).__name__
            )
            cls.remove(db_name)
            raise

        return cls._new_finalize(db_name, update_module, t0)

    def init(self, db_name: str) -> None:
        self.loaded = False
        self.ready = False
        self.last_used = time.monotonic()

        self._init_models_container()
        self._init_phase_state()
        self._loading_phase_state()
        self._init_field_state()
        self._init_schema_state()
        self._init_signaling_state()

        self.loaded_modules: set[str] = set()
        self.updated_modules: list[str] = []
        self.deferred_at_install_modules: list[str] = []
        self.loaded_xmlids: set[str] = set()

        self.db_name = db_name
        self._replica = ReplicaRouter(
            db.db_connect(db_name, readonly=False),
            db.db_connect(db_name, readonly=True)
            if is_readonly_cursor_enabled()
            else None,
        )

        with closing(self.cursor()) as cr:
            self._probe_capabilities(cr, db_name)

    @classmethod
    @locked
    def remove(cls, db_name: str) -> None:
        if db_name in cls.registries:
            del cls.registries[db_name]
            gc.thaw()
            _debug.lifecycle("registry.removed", db=db_name)
        remove_counters(db_name)

    @classmethod
    @locked
    def _evict_idle_registries(cls) -> None:
        if cls.idle_timeout <= 0:
            return
        now = time.monotonic()
        for db_name, registry in cls.registries.items():
            if not registry.ready:
                continue
            idle_for = now - registry.last_used
            if idle_for > cls.idle_timeout:
                _logger.info(
                    "Evicting idle registry for %s, idle for %.0fs", db_name, idle_for
                )
                _debug.lifecycle(
                    "registry.evicted_idle", db=db_name, idle_seconds=idle_for
                )
                cls.remove(db_name)

    @classmethod
    @locked
    def clear_database_state(cls, db_name: str) -> None:
        cls.remove(db_name)
        clear_text_transforms(db_name)
        from odoo.tests.result import forget_assertion_report

        forget_assertion_report(db_name)

    @classmethod
    @locked
    def remove_all(cls):
        _debug.lifecycle("registry.remove_all", registries=len(cls.registries))
        cls.registries.clear()
        gc.thaw()
        clear_all_text_transforms()
        from odoo.tests.result import forget_assertion_report

        forget_assertion_report()

    __eq__ = object.__eq__
    __ne__ = object.__ne__
    __hash__ = object.__hash__

    def load(self, module: module_graph.ModuleNode) -> list[str]:
        model_defs = models.MetaModel._module_to_models__.get(module.name, [])
        if not model_defs:
            return []

        self._caches.clear_all()

        reset_cached_properties(self)
        self.model_graph.clear_caches()

        model_names = []
        for model_def in model_defs:
            model_cls = registration.add_model_to_registry(
                self, typing.cast("type[BaseModel]", model_def)
            )
            model_names.append(model_cls._name)

        _debug.pipeline(
            "registry.load_module", module=module.name, models=len(model_names)
        )
        return model_names

    def _setup_reset_all_models(self) -> None:
        self.many2many_relations.clear()
        self.field_setup_dependents.clear()

        for model_cls in self.models.values():
            model_cls._setup_done__ = False

        self.model_graph.reset_field_metadata()

    def _setup_reset_named_models(
        self, model_names: Iterable[str], models_field_depends_done: set
    ) -> None:
        model_names_to_setup = self.get_descendants(
            model_names, "_inherit", "_inherits"
        )
        for fields in self.many2many_relations.values():
            for pair in list(fields):
                if pair[0] in model_names_to_setup:
                    fields.discard(pair)

        for model_name in model_names_to_setup:
            self[model_name]._setup_done__ = False

        todo: list = []
        for model_cls in self.models.values():
            if model_cls._custom:
                model_cls._setup_done__ = False
            if model_cls._setup_done__:
                models_field_depends_done.add(model_cls)
            else:
                todo.extend(model_cls._fields.values())

        done = set()
        for field in todo:
            if field in done:
                continue

            model_cls = self[field.model_name]
            if model_cls._setup_done__ and field._base_fields__:
                name = field.name
                base_fields = field._base_fields__

                field.__dict__.clear()
                field.__init__(_base_fields__=base_fields)
                field._toplevel = True
                field.__set_name__(model_cls, name)
                field._setup_done = False

                models_field_depends_done.discard(model_cls)

            elif model_cls._setup_done__ and field.related and field.manual:
                model_cls._setup_done__ = False
                models_field_depends_done.discard(model_cls)

            self.field_depends.pop(field, None)
            self.field_depends_context.pop(field, None)

            done.add(field)
            todo.extend(self.field_setup_dependents.pop(field, ()))  # noqa: B909  todo is a worklist: appending newly discovered dependents here is how they get processed later in this same loop

        _debug.logic(
            "registry.setup.reset_named",
            requested=len(list(model_names)),
            models=len(model_names_to_setup),
            fields_reset=len(done),
            models_kept=len(models_field_depends_done),
        )

    def _setup_field_depends(self, env, models_field_depends_done: set) -> None:
        for model_cls in self.models.values():
            if model_cls in models_field_depends_done:
                continue
            model = model_cls(env, (), ())
            for field in model._fields.values():
                depends, depends_context = field.get_depends(model)
                self.field_depends[field] = tuple(depends)
                self.field_depends_context[field] = tuple(depends_context)

    @locked
    def setup_models(
        self,
        cr: BaseCursor,
        model_names: Iterable[str] | None = None,
        *,
        skip_if_clean: bool = False,
    ) -> None:
        if model_names is not None:
            model_names = list(model_names)
        if (
            skip_if_clean
            and model_names is not None
            and not model_names
            and all(
                model_cls._setup_done__ and not model_cls._custom
                for model_cls in self.models.values()
            )
        ):
            _debug.logic("registry.setup_models.skipped", db=self.db_name)
            return

        with _debug.perf(
            "registry.setup_models",
            cr=cr,
            db=self.db_name,
            scope="all" if model_names is None else "named",
            ready=self.ready,
        ):
            from .environment import Environment

            env = Environment(cr, SUPERUSER_ID, {})
            env.invalidate_all()

            if self.ready:
                for model in env.values():
                    model._unregister_hook()

            self._caches.clear_all()

            self.model_graph.begin_invalidation()
            try:
                reset_cached_properties(self)
                self.model_graph.clear_caches()
                self._note_invalidated_models(model_names)

                models_field_depends_done: set[type] = set()

                if model_names is None:
                    self._setup_reset_all_models()
                else:
                    self._setup_reset_named_models(
                        model_names, models_field_depends_done
                    )

                self.many2one_company_dependents.clear()

                registration.setup_model_classes(env)

                self._setup_field_depends(env, models_field_depends_done)

                reset_cached_properties(self)

            finally:
                self.model_graph.end_invalidation()

            if self.not_null_columns:
                self.rebuild_not_null_fields()

            if self.ready:
                for model in env.values():
                    model._register_hook()
                self.__dict__.pop("_field_triggers", None)
                self._get_field_triggers()
                env.flush_all()

    def init_models(
        self,
        cr: Cursor,
        model_names: Iterable[str],
        context: dict[str, typing.Any],
        install: bool = True,
    ):
        model_names = list(model_names)
        if not model_names:
            return

        if "module" in context:
            _logger.info(
                "module %s: creating or updating database tables",
                context["module"],
            )
        elif context.get("models_to_check"):
            _logger.info("verifying fields for every extended model")

        from .environment import Environment

        env = Environment(cr, SUPERUSER_ID, context)
        models = [env[model_name] for model_name in model_names]

        with _debug.perf(
            "registry.init_models",
            cr=cr,
            models=len(model_names),
            install=install,
            module=context.get("module"),
        ):
            with self.init_models_window(
                install,
                model_tables=(
                    model._table
                    for model in self.models.values()
                    if not model._abstract
                ),
            ) as phase:
                for model in models:
                    with _debug.perf(
                        "registry.init_model", cr=cr, model=model._name
                    ) as span:
                        rss = read_rss()
                        model._auto_init()
                        model.init()
                        span.set(rss_mb=(read_rss() - rss) // (1024 * 1024))

                self.metaschema.reflect(
                    env,
                    model_names,
                    relation_reflections=phase.relation_reflections,
                    model_tables=phase.model_tables,
                )

                self._ordinary_tables = {}

                _debug.pipeline(
                    "registry.init_models.reflected",
                    models=len(model_names),
                    relations=len(phase.relation_reflections),
                )
                self.drain_post_init()

                self.check_indexes(cr, model_names)
                self.check_foreign_keys(cr)

                env.flush_all()

                self.check_tables_exist(cr)

    def clear_all_caches(self) -> None:
        _debug.lifecycle(
            "registry.clear_all_caches", db=self.db_name, loaded=self.loaded
        )
        self._invalidate_cache_groups(CACHES_BY_KEY)
        self._log_invalidation(("all",), logging.INFO if self.loaded else logging.DEBUG)

    def setup_signaling(self) -> None:
        with self.cursor() as cr:
            self._create_missing_signaling_tables(cr)
            self._load_sequences(cr)

    def check_signaling(self, cr: BaseCursor | None = None) -> Registry:
        own_cursor = cr is None
        try:
            with (
                nullcontext(cr)
                if cr is not None
                else closing(self.cursor(readonly=True))
            ) as sig_cr:
                db_registry_sequence, db_cache_sequences = self.get_sequences(sig_cr)
                changes = ""
                if db_registry_sequence > self.registry_sequence:
                    old_sequence = self.registry_sequence
                    _debug.lifecycle(
                        "registry.signaling.reload",
                        db=self.db_name,
                        sequence=old_sequence,
                        db_sequence=db_registry_sequence,
                    )
                    self = self._reload_after_signaling(db_registry_sequence)
                    sig_cr.invalidate_cached_plans()
                    if _logger.isEnabledFor(logging.DEBUG):
                        changes += (
                            f"[Registry - {old_sequence} -> {self.registry_sequence}]"
                        )
                elif db_registry_sequence < self.registry_sequence:
                    _logger.debug(
                        "Ignoring stale registry signaling read "
                        "(db %s < local %s), likely replica lag",
                        db_registry_sequence,
                        self.registry_sequence,
                    )
                    _debug.logic(
                        "registry.signaling.stale_read",
                        db=self.db_name,
                        sequence=self.registry_sequence,
                        db_sequence=db_registry_sequence,
                    )
                changes += self._sync_cache_sequences(db_cache_sequences)
                if changes:
                    _logger.debug("Multiprocess signaling check: %s", changes)
        except db.PoolError:
            raise
        except psycopg.OperationalError:
            _debug.lifecycle(
                "registry.signaling.check_failed",
                db=self.db_name,
                removed=own_cursor,
            )
            if own_cursor:
                type(self).remove(self.db_name)
            raise
        return self

    def _reload_after_signaling(self, db_registry_sequence: int) -> Registry:
        _logger.info("Reloading the model registry after database signaling.")
        published = Registry.registries.get(self.db_name)
        if (
            published is not None
            and published is not self
            and published.ready
            and published.registry_sequence >= db_registry_sequence
        ):
            _debug.logic(
                "registry.reload.reuse_published",
                db=self.db_name,
                sequence=published.registry_sequence,
                db_sequence=db_registry_sequence,
            )
            return published
        db.drain_db(self.db_name)
        return Registry.new(self.db_name)

    def signal_changes(self) -> None:
        if not self.ready:
            _logger.warning(
                "Calling signal_changes when registry is not ready is not supported"
            )
            return

        if _debug.logic.enabled and (
            self.registry_invalidated or self.cache_invalidated
        ):
            _debug.logic(
                "registry.signal_changes",
                db=self.db_name,
                registry=self.registry_invalidated,
                caches=sorted(self.cache_invalidated),
            )

        if self.registry_invalidated or self.cache_invalidated:
            with self.cursor() as cr:
                if self.registry_invalidated:
                    self._signal_registry_change(cr)
                if self.cache_invalidated:
                    self._signal_cache_changes(cr)

        self.registry_invalidated = False
        self.cache_invalidated.clear()

    def reset_changes(self) -> None:
        if self.registry_invalidated:
            _debug.logic("registry.reset_changes", db=self.db_name)
            with closing(self.cursor()) as cr:
                self.setup_models(cr)
                self.registry_invalidated = False
        self._reset_cache_changes()

    def cursor(
        self, /, readonly: bool = False, *, pin_key: Hashable | None = None
    ) -> BaseCursor:
        cr, mode = self._replica.cursor(readonly, pin_key=pin_key)
        if mode != "rw":
            thread = current_worker_thread()
            if hasattr(thread, "cursor_mode"):
                thread.cursor_mode = mode
        return cr


class DummyRLock:
    def acquire(self) -> None:
        pass

    def release(self) -> None:
        pass

    def __enter__(self) -> None:
        self.acquire()

    def __exit__(
        self,
        type: type[BaseException] | None,
        value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        self.release()
