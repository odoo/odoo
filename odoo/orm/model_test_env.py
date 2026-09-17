import logging
import threading
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from contextlib import contextmanager, suppress
from datetime import UTC, datetime
from functools import partial
from typing import TYPE_CHECKING, Any, Self, cast

from odoo.db import BaseCursor, FunctionStatus
from odoo.libs.collections import Collector
from odoo.libs.debug_log import DebugLog
from odoo.libs.lru import LRU
from odoo.tools import OrderedSet
from odoo.tools.constants import REGISTRY_CACHES

from . import decorators as api
from . import registration
from .components.model_graph import ModelGraph
from .components.storage import DictBackend
from .fields import Boolean, Char, Many2many, Many2one
from .models import AbstractModel, MetaModel, Model
from .primitives import SUPERUSER_ID
from .runtime._registry_fields import _RegistryFieldsMixin
from .runtime._registry_models import _RegistryModelsMixin
from .runtime.access_policy import ACCESS_POLICY
from .runtime.environment import Environment
from .runtime.filestore import FILE_STORE
from .runtime.locale import LOCALE, Locale
from .runtime.metaschema import META_SCHEMA
from .runtime.registry import CACHES_BY_KEY
from .runtime.settings import SYSTEM_SETTINGS
from .runtime.transaction import Transaction
from .runtime.xmlids import XMLIDS

if TYPE_CHECKING:
    from .models.base import BaseModel
    from .runtime.registry import Registry

_logger = logging.getLogger("odoo.orm.model_test_env")
_debug = DebugLog(__name__)


class InMemorySqlNotSupported(NotImplementedError):
    pass


class InMemoryRecordRulesNotSupported(NotImplementedError):
    pass


class InMemoryAccessRightsNotSupported(NotImplementedError):
    pass


class _TestBase(AbstractModel):
    _name = "base"
    _description = "Base"
    _register = False
    _module = None


class _TestIrDefault(AbstractModel):
    _name = "ir.default"
    _description = "Ir Default (test stub)"
    _register = False
    _module = None

    def _get_model_defaults(self, model_name, condition=False):
        return {}


class _TestResUsers(Model):
    _name = "res.users"
    _description = "Users (test stub)"
    _register = False
    _module = None
    _log_access = False

    name = Char()
    login = Char()
    active = Boolean(default=True)
    tz = Char()
    lang = Char()
    company_id = Many2one("res.company")
    company_ids = Many2many("res.company")
    # res.users inherits res.partner's parent_id: a many2one to a user
    # describes itself with the hierarchy operators, as on PostgreSQL
    parent_id = Many2one("res.users")
    # the group external ids the user holds, comma-separated: what a test
    # gives a user instead of res.groups rows
    group_xmlids = Char()

    def _get_company_ids(self):
        # the protocol and the real res.users answer tuple[int, ...]
        return (self.company_id | self.company_ids)._ids

    def _held_groups(self) -> set[str]:
        self.check_singleton()
        return {token for token in (self.group_xmlids or "").split(",") if token}

    def _get_group_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._held_groups()))

    def _has_group(self, group_ext_id: str) -> bool:
        return group_ext_id in self._held_groups()

    def has_group(self, group_ext_id: str) -> bool:
        return self._has_group(group_ext_id)

    def has_groups(self, group_spec: str) -> bool:
        if group_spec == ".":
            return False
        tokens = [token.strip() for token in group_spec.split(",") if token.strip()]
        negatives = [token[1:] for token in tokens if token.startswith("!")]
        positives = [token for token in tokens if not token.startswith("!")]
        if not tokens:
            return False
        if any(self._has_group(ext_id) for ext_id in negatives):
            return False
        if any(self._has_group(ext_id) for ext_id in positives):
            return True
        return not positives

    def _is_superuser(self) -> bool:
        return self.id == SUPERUSER_ID

    def _is_admin(self) -> bool:
        return self._is_superuser() or self._has_group("base.group_erp_manager")

    def _is_system(self) -> bool:
        return self._has_group("base.group_system")

    def _is_public(self) -> bool:
        return self._has_group("base.group_public")

    @api.model
    def context_get(self):
        return {"lang": "en_US", "tz": False, "uid": self.env.uid}


class _TestResCompany(Model):
    _name = "res.company"
    _description = "Companies (test stub)"
    _register = False
    _module = None
    _log_access = False

    name = Char()
    active = Boolean(default=True)
    # a stub company is its own root, as a company without a parent is
    root_id = Many2one("res.company", compute="_compute_root_id")

    def _compute_root_id(self):
        for company in self:
            company.root_id = company


_FALLBACK_MODELS = (
    ("ir.default", _TestIrDefault),
    ("res.users", _TestResUsers),
    ("res.company", _TestResCompany),
)


class InMemorySavepoint:
    # a snapshot of the dict storage stands in for SAVEPOINT; rolling back restores
    # it and drops the ORM caches, as the flushing savepoint does on PostgreSQL
    __slots__ = ("_cr", "_flush", "_snapshot", "closed", "name")

    def __init__(self, cr: InMemoryCursor, *, flush: bool) -> None:
        self._cr = cr
        self._flush = flush
        if flush:
            cr.flush()
        self._snapshot = cr.storage.snapshot()
        self.name = f"memsp{cr._savepoint_depth}"
        self.closed = False
        cr._savepoint_depth += 1
        _debug.lifecycle("test_env.savepoint.opened", name=self.name, flush=flush)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close(rollback=exc_type is not None)

    def rollback(self) -> None:
        if self.closed:
            raise RuntimeError(f'Savepoint "{self.name}" is already closed')
        _debug.lifecycle(
            "test_env.savepoint.rolled_back", name=self.name, flush=self._flush
        )
        if self._flush:
            self._cr.clear()
        self._cr.storage.restore(self._snapshot)
        if self._flush and (transaction := self._cr.transaction) is not None:
            transaction.clear()

    def close(self, *, rollback: bool = True) -> None:
        if self.closed:
            return
        try:
            if rollback:
                self.rollback()
            elif self._flush:
                self._cr.flush()
        finally:
            self.closed = True
            self._cr._savepoint_depth -= 1


class InMemoryCursor(BaseCursor):
    def __init__(
        self,
        registry: Registry,
        fixtures: dict[str | tuple[str, tuple], list[tuple]] | None = None,
    ) -> None:
        super().__init__()
        self.dbname = registry.db_name
        self.storage = DictBackend()
        # SQL.inlined renders literals against the connection; without one
        # psycopg renders them generically, which the compiled statement the
        # in-memory backend never runs can carry
        self._cnx = None
        self.transaction = Transaction(registry, storage=self.storage)
        self._fixtures: dict[str | tuple[str, tuple], list[tuple]] = fixtures or {}
        self._last_result: list[tuple] = []

    def execute(
        self,
        query,
        params=None,
        log_exceptions: bool = True,
        prepare: bool | None = None,
    ) -> None:
        key = str(query)
        # a fixture registered as (query, params) answers only that exact
        # execution; a str-only fixture answers the text whatever the params,
        # as before, but says so when params were dropped on the floor
        rows = None
        if params is not None:
            rows = self._fixtures.get((key, tuple(params)))
        if rows is None:
            rows = self._fixtures.get(key)
            if rows is not None and params is not None:
                _debug.logic(
                    "test_env.sql_fixture_params_ignored",
                    query=key[:120],
                    params=len(params),
                )
        if rows is not None:
            self._last_result = rows
            _debug.logic(
                "test_env.sql_fixture_hit",
                rows=len(self._last_result) if self._last_result else 0,
            )
            return
        _debug.logic("test_env.sql_unsupported", query=key[:120])
        raise InMemorySqlNotSupported(
            "InMemoryCursor (DB-free model_test_env) cannot execute raw SQL:\n"
            f"    {key}\n"
            "ORM CRUD is handled in memory, but this query (e.g. read_group or a "
            "custom cr.execute) needs PostgreSQL. Register its result via "
            "model_test_env(..., fixtures={str(query): rows}) or use a DB-backed "
            "TransactionCase."
        )

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def connection(self) -> None:
        # the DB-API name for a cursor's connection: there is none, and psycopg
        # quotes a literal without one (SQL.inlined); a caller wanting the
        # connection's members fails on None, which is as loud as it was
        return self._cnx

    @property
    def rowcount(self) -> int:
        return len(self._last_result)

    def fetchall(self) -> list[tuple]:
        return list(self._last_result)

    def fetchone(self) -> tuple | None:
        return self._last_result[0] if self._last_result else None

    def fetchmany(self, size: int = 0) -> list[tuple]:
        # psycopg substitutes the cursor's arraysize (default 1) for a
        # falsy size instead of answering no rows
        return self._last_result[: size or 1]

    _DICT_API_UNSUPPORTED = (
        "InMemoryCursor (DB-free model_test_env) cannot serve the dict cursor "
        "API (dictfetchone/dictfetchall): fixtures are tuple rows with no column "
        "names. Consume the registered fixture via fetchone/fetchall, or move the "
        "test to a DB-backed TransactionCase."
    )

    def dictfetchone(self) -> dict | None:
        if not self._last_result:
            return None
        raise InMemorySqlNotSupported(self._DICT_API_UNSUPPORTED)

    def dictfetchall(self) -> list[dict]:
        if not self._last_result:
            return []
        raise InMemorySqlNotSupported(self._DICT_API_UNSUPPORTED)

    def now(self) -> datetime:
        if self._now is None:
            self._now = datetime.now(UTC).replace(tzinfo=None)
        return self._now

    def savepoint(self, flush: bool = True):
        return InMemorySavepoint(self, flush=flush)

    @contextmanager
    def pipeline(self, log_exceptions: bool = True, query: Any = None):
        yield

    def commit(self) -> None:
        if self._savepoint_depth:
            raise RuntimeError(
                "Cannot commit inside a savepoint! "
                "This would corrupt the savepoint's rollback state."
            )
        self.flush()
        self.commit_count += 1
        _debug.lifecycle("test_env.commit", commits=self.commit_count)
        self.clear()
        self._now = None
        self.prerollback.clear()
        self.postrollback.clear()
        self.postcommit.run()

    def rollback(self) -> None:
        raise InMemorySqlNotSupported(
            "InMemoryCursor (DB-free model_test_env) cannot roll back: storage "
            "writes are applied immediately and no snapshot exists to restore. "
            "A silent no-op would diverge from production ROLLBACK (which "
            "discards the transaction's writes); use a DB-backed "
            "TransactionCase to test rollback behaviour."
        )

    def close(self) -> None:
        pass


class ModelRegistry(_RegistryFieldsMixin, _RegistryModelsMixin, Mapping):
    _lock: threading.RLock = threading.RLock()
    metaschema = META_SCHEMA
    access_policy = ACCESS_POLICY
    xmlids = XMLIDS
    file_store = FILE_STORE
    settings = SYSTEM_SETTINGS
    locale = LOCALE
    # A database's own ilike normalizer (Registry.get_ilike_normalizer(env)), when a
    # differential wants this registry to fold exactly as that database does.
    ilike_normalizer: Callable[[str], str] | None = None

    def __init__(
        self,
        model_defs: Iterable[type[BaseModel]],
        *,
        db_name: str = ":memory:",
        isolated: bool = False,
    ) -> None:
        self.db_name = db_name
        self._isolated = isolated
        self._init_models_container()

        self.model_graph = ModelGraph()

        self.loaded_modules: set[str] = set()
        self.loaded_xmlids: set[str] = set()
        self.database_translated_fields: dict[str, str] = {}
        self.database_company_dependent_fields: set[str] = set()
        self.many2many_relations: defaultdict[
            tuple[str, str, str], OrderedSet[tuple[str, str]]
        ] = defaultdict(OrderedSet)
        self.field_setup_dependents: Collector = Collector()
        self.many2one_company_dependents: Collector = Collector()

        self.ormcache_lrus: dict[str, LRU] = defaultdict(
            partial(LRU, REGISTRY_CACHES["default"]),
            {name: LRU(size) for name, size in REGISTRY_CACHES.items()},
        )

        self.ready = True

        self.not_null_fields: set = set()

        self.degraded_fields: dict = {}

        self.has_trigram = False

        self.has_unaccent = FunctionStatus.MISSING

        self._setup_registry(list(model_defs))
        self.modules = self._modules_of(model_defs)

    def __getitem__(self, model_name: str) -> type[BaseModel]:
        try:
            return super().__getitem__(model_name)
        except KeyError:
            if model_name == "ir.rule":
                raise InMemoryRecordRulesNotSupported(
                    "ModelRegistry (DB-free model_test_env) has no 'ir.rule' "
                    "model: record rules are NOT enforced in this tier -- an "
                    "access-checked search asks registry.access_policy for the "
                    "ir.rule domain and there is none to answer. A security-adjacent "
                    "assertion would go green here while production filters "
                    "records. Use a DB-backed TransactionCase to test record-"
                    "rule behaviour, or pass your own ir.rule model class to "
                    "model_test_env(...): the in-memory backend applies the "
                    "domain it returns."
                ) from None
            if model_name == "ir.model.access":
                raise InMemoryAccessRightsNotSupported(
                    "ModelRegistry (DB-free model_test_env) has no "
                    "'ir.model.access' model: access rights are NOT enforced in "
                    "this tier -- a read, write, create or unlink by a user "
                    "other than the superuser asks registry.access_policy whether "
                    "the model allows it and there is no ACL to answer. Use a "
                    "DB-backed TransactionCase to test access rights, or pass "
                    "your own ir.model.access model class to model_test_env(...)."
                ) from None
            raise

    def __contains__(self, model_name: object) -> bool:
        # Mapping's default asks __getitem__, whose miss on ir.rule and
        # ir.model.access is a NotImplementedError, not a KeyError
        return model_name in self.models

    def record_xmlids_written(self, xml_ids) -> None:
        self.loaded_xmlids.update(xml_ids)

    def post_init(self, func, *args, **kwargs) -> None:
        pass

    def post_constraint(self, cr, func, key) -> None:
        pass

    def add_foreign_key(self, *args, **kwargs) -> None:
        pass

    def reset_changes(self) -> None:
        pass

    def clear_cache(self, *cache_names: str) -> None:
        for cache_name in cache_names or ("default",):
            if "." in cache_name:
                raise ValueError(
                    f"clear_cache: invalid cache name {cache_name!r} (no dots allowed)"
                )
            for container in CACHES_BY_KEY.get(cache_name, (cache_name,)):
                self.ormcache_lrus[container].clear()

    def is_an_ordinary_table(self, model) -> bool:
        return True

    @staticmethod
    def unaccent(text):
        return text

    @staticmethod
    def unaccent_python(text):
        return text

    def get_ilike_normalizer(self, env):
        if self.ilike_normalizer is not None:
            return self.ilike_normalizer

        def normalize(value):
            text = self.unaccent_python(value)
            if text.isascii():
                return text.lower()
            return "".join(char.lower()[0] for char in text)

        return normalize

    def _collect_field_depends(self, env) -> None:
        for model_cls in self.models.values():
            model = model_cls(env, (), ())
            for field in model._fields.values():
                try:
                    depends, depends_context = field.get_depends(model)
                    self.field_depends[field] = tuple(depends)
                    self.field_depends_context[field] = tuple(depends_context)
                except KeyError as exc:
                    self.field_depends[field] = ()
                    self.field_depends_context[field] = ()
                    self.degraded_fields[field] = f"get_depends: missing {exc}"

        if self.degraded_fields:
            _logger.warning(
                "model_test_env: %d field(s) degraded (missing comodel in the "
                "model set); their triggers/deps are inert. Inspect via "
                "registry.degraded_fields. Degraded: %s",
                len(self.degraded_fields),
                ", ".join(
                    sorted(f"{f.model_name}.{f.name}" for f in self.degraded_fields)
                ),
            )

    @staticmethod
    def _modules_of(model_defs) -> set[str]:
        # only the modules the named classes declare: once a test imports
        # odoo.addons.base.models, "base" holds every base model class and an
        # implicit "base" would drag them into every registry of the process
        modules: set[str] = set()
        for cls in model_defs:
            module = getattr(cls, "_module", None)
            if module:
                modules.add(module)
        return modules

    @classmethod
    def _get_model_defs(
        cls,
        model_defs: list[type[BaseModel]],
        isolated: bool = False,
    ) -> list[type[BaseModel]]:
        # an isolated registry holds these classes and nothing else of their
        # module, so a test can pick real addon models without their neighbours
        modules = () if isolated else cls._modules_of(model_defs)

        all_defs: list[Any] = []
        seen_ids: set[int] = set()

        for module in sorted(modules, key=lambda m: (m != "base", m)):
            for registered in MetaModel._module_to_models__.get(module, []):
                if id(registered) not in seen_ids:
                    seen_ids.add(id(registered))
                    all_defs.append(registered)

        for model_def in model_defs:
            if id(model_def) not in seen_ids:
                seen_ids.add(id(model_def))
                all_defs.append(model_def)

        if not any(getattr(cls, "_name", None) == "base" for cls in all_defs):
            all_defs.insert(0, _TestBase)
        return all_defs

    def _setup_registry(self, model_defs: list[type[BaseModel]]) -> None:
        all_defs = self._get_model_defs(model_defs, self._isolated)

        for model_name, fallback in _FALLBACK_MODELS:
            if not any(getattr(cls, "_name", None) == model_name for cls in all_defs):
                all_defs.append(fallback)

        all_defs.sort(
            key=lambda c: 0 if getattr(c, "_name", "") == "base" else 1,
        )

        registry_self = cast("Registry", self)
        for model_def in all_defs:
            registration.add_model_to_registry(registry_self, model_def)

        cr = InMemoryCursor(registry_self)
        env = Environment(cr, SUPERUSER_ID, {})
        env.transaction.default_env = env

        model_classes = list(self.models.values())

        for model_cls in model_classes:
            registration._reset_setup(model_cls)

        for model_cls in model_classes:
            registration._setup(model_cls, env)

        for model_cls in model_classes:
            self._setup_fields_lenient(model_cls, env)

        self._collect_field_depends(env)

        for model_cls in self.models.values():
            if model_cls._auto and not model_cls._abstract:
                for field in model_cls._fields.values():
                    if field.name == "id" or (
                        field.column_type and field.store and field.required
                    ):
                        self.not_null_fields.add(field)

        _debug.pipeline(
            "test_env.registry_setup",
            models=len(model_classes),
            requested=len(model_defs),
            degraded_fields=len(self.degraded_fields),
            not_null_fields=len(self.not_null_fields),
        )
        for model_cls in model_classes:
            try:
                model_cls(env, (), ())._post_model_setup__()
            except Exception:
                _logger.debug(
                    "Post-setup hook for %s failed (expected in test registry)",
                    model_cls._name,
                    exc_info=True,
                )

    def _setup_fields_lenient(
        self,
        model_cls: type[BaseModel],
        env: Environment,
    ) -> None:
        model = model_cls(env, (), ())
        pool = registration.get_registry_of_model(model_cls)
        for name, field in model_cls._fields.items():
            try:
                field.setup(model)
            except Exception as exc:
                comodel = getattr(field, "comodel_name", None)
                missing_comodel = bool(comodel) and comodel not in pool
                if not missing_comodel and not isinstance(exc, KeyError):
                    raise
                _logger.debug(
                    "Field %s.%s setup incomplete (missing comodel?); field will raise if accessed in test",
                    model_cls._name,
                    name,
                )
                field._setup_done = True
                self.degraded_fields[field] = f"setup: {type(exc).__name__}: {exc}"
                _debug.logic(
                    "test_env.field_setup_degraded",
                    model=model_cls._name,
                    field=name,
                    comodel=comodel,
                    error=type(exc).__name__,
                )
            else:
                if field.is_many2one and field.company_dependent:
                    pool.many2one_company_dependents.add(
                        field.comodel_name or "",
                        field,
                    )


class _InstalledLangs(Locale):
    __slots__ = ("codes",)

    def __init__(self, codes: Iterable[str]) -> None:
        self.codes = frozenset(codes) | {"en_US"}

    def installed_langs(self, env: Environment) -> list[str]:
        return sorted(self.codes)

    def is_lang_installed(self, env: Environment, code: str) -> bool:
        return code in self.codes


@contextmanager
def model_test_env(
    *model_classes: type[BaseModel],
    registry: ModelRegistry | None = None,
    db_name: str = ":memory:",
    fixtures: dict[str | tuple[str, tuple], list[tuple]] | None = None,
    langs: Iterable[str] = (),
    check_cache: bool = True,
):
    if registry is None:
        registry = ModelRegistry(model_classes, db_name=db_name)
    # a reused registry keeps its own locale only for this call: without a
    # restore, a later model_test_env without langs would still see them
    had_own_locale = "locale" in registry.__dict__
    prev_locale = registry.__dict__.get("locale")
    if langs:
        registry.locale = _InstalledLangs(langs)

    for cache in registry.ormcache_lrus.values():
        cache.clear()

    for attr in ("_field_triggers",):
        with suppress(AttributeError):
            delattr(registry, attr)

    cr = InMemoryCursor(cast("Registry", registry), fixtures=fixtures)

    _create_fixtures(cr.storage, registry)

    env = Environment(cr, SUPERUSER_ID, {})
    env.transaction.default_env = env
    _reflect_models(cr.storage, registry, env)
    failed = True
    try:
        yield env
        failed = False
    finally:
        # every test leaves the caches agreeing with the rows, as
        # TransactionCase asserts against PostgreSQL; a test that plants
        # cache values or expects a refused flush opts out, and a failing
        # test reports its own error
        if langs:
            if had_own_locale:
                registry.locale = cast("Locale", prev_locale)
            else:
                registry.__dict__.pop("locale", None)
        if check_cache and not failed:
            env.cache.check(env)


def _reflect_models(storage: DictBackend, registry: ModelRegistry, env) -> None:
    # the rows init_models reflects on PostgreSQL, so ir.model / ir.model.fields answer
    # the same questions in memory (defaults, xmlids on fields, selection labels)
    if "ir.model" not in registry or "ir.model.fields" not in registry:
        return
    IrModel = env["ir.model"]
    IrModelFields = env["ir.model.fields"]

    def stored(model_cls, vals: dict) -> dict:
        row = {}
        for name, value in vals.items():
            field = model_cls._fields.get(name)
            if field is None or not field.store or not field.column_type:
                continue
            if field.translate and isinstance(value, str):
                value = {"en_US": value}
            row[name] = value
        return row

    xmlids: list[dict] = []

    def xmlid(module: str, name: str, model_name: str, res_id: int) -> None:
        xmlids.append(
            {
                "id": storage.allocate_next_id("ir_model_data"),
                "module": module,
                "name": name,
                "model": model_name,
                "res_id": res_id,
                "noupdate": False,
            }
        )

    for model_cls in registry.models.values():
        model = model_cls(env, (), ())
        module = getattr(model_cls, "_original_module", None) or "base"
        slug = model_cls._name.replace(".", "_")
        model_id = storage.allocate_next_id("ir_model")
        row = stored(registry["ir.model"], IrModel._prepare_model_vals(model))
        row["id"] = model_id
        storage.put_rows("ir_model", [row])
        xmlid(module, f"model_{slug}", "ir.model", model_id)
        rows = []
        for field in model_cls._fields.values():
            vals = IrModelFields._prepare_field_vals(field, model_id)
            frow = stored(registry["ir.model.fields"], vals)
            frow["id"] = storage.allocate_next_id("ir_model_fields")
            rows.append(frow)
            xmlid(module, f"field_{slug}__{field.name}", "ir.model.fields", frow["id"])
        if rows:
            storage.put_rows("ir_model_fields", rows)
    if "ir.model.data" in registry and xmlids:
        storage.put_rows("ir_model_data", xmlids)


def _create_fixtures(storage: DictBackend, registry: ModelRegistry) -> None:

    def _insert_row(table: str, record_id: int, data: dict) -> None:
        data["id"] = record_id
        storage.put_rows(table, [data])

    # the rows base/data/base_data.sql seeds before any XML loads, with their xmlids
    xmlids: list[tuple[str, str]] = []

    if "res.currency" in registry:
        _insert_row("res_currency", 1, {"name": "USD", "symbol": "$", "active": True})
        xmlids.append(("USD", "res.currency"))

    if "res.partner" in registry:
        _insert_row(
            "res_partner",
            1,
            {
                "name": "Test Company",
                "active": True,
                "is_company": True,
                "type": "contact",
            },
        )
        xmlids.append(("main_partner", "res.partner"))

    if "res.company" in registry:
        _insert_row(
            "res_company",
            1,
            {
                "name": "Test Company",
                "active": True,
                "partner_id": 1,
                "parent_path": "1/",
                "currency_id": 1 if "res.currency" in registry else None,
            },
        )
        xmlids.append(("main_company", "res.company"))

    if "res.users" in registry:
        _insert_row(
            "res_users",
            1,
            {
                "name": "Admin",
                "login": "admin",
                "active": True,
                "company_id": 1,
                "partner_id": 1,
            },
        )
        field = registry["res.users"]._fields.get("company_ids")
        if field is not None and field.is_many2many and field.store and field.relation:
            relation, column1, column2 = field._get_relation_triple()
            storage.insert_rows(relation, [column1, column2], [(1, 1)])
        xmlids.append(("user_root", "res.users"))

    if "res.groups" in registry:
        _insert_row("res_groups", 1, {"name": {"en_US": "Employee"}})
        xmlids.append(("group_user", "res.groups"))

    if "ir.model.data" in registry:
        storage.put_rows(
            "ir_model_data",
            [
                {
                    "id": storage.allocate_next_id("ir_model_data"),
                    "module": "base",
                    "name": name,
                    "model": model,
                    "res_id": 1,
                    "noupdate": True,
                }
                for name, model in xmlids
            ],
        )
