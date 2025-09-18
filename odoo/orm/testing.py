"""ORM-level testing utilities.

Provides :class:`InMemoryCursor`, a :class:`~odoo.db.BaseCursor` subclass
that satisfies :class:`~odoo.orm.protocols.CursorProtocol` without a
PostgreSQL connection.  When paired with a pre-built
:class:`~odoo.orm.runtime.registry.Registry`, it allows constructing a real
:class:`~odoo.orm.runtime.environment.Environment` in tests that exercise
model compute methods, field logic, or business rules without issuing any SQL.

Usage::

    from odoo.orm.testing import InMemoryCursor
    from odoo.orm.runtime import Environment
    from odoo.orm.primitives import SUPERUSER_ID

    # In a TransactionCase (registry already loaded):
    cr = InMemoryCursor(self.env.registry)
    env = Environment(cr, SUPERUSER_ID, {})

    # With fixture data for queries the model method will issue:
    cr = InMemoryCursor(
        self.env.registry,
        fixtures={
            "SELECT id FROM res_lang WHERE active": [(1,), (2,)],
        },
    )
    env = Environment(cr, SUPERUSER_ID, {})

For database-free testing of model methods with a lightweight registry::

    from odoo.orm.testing import model_test_env
    from odoo.addons.base.models.res_partner import Partner

    with model_test_env(Partner) as env:
        partner = env["res.partner"].create({"name": "Test"})
        partner._compute_display_name()
        assert partner.display_name == "Test"

See :class:`~odoo.orm.components.testing.InMemoryEnvironment` for the
lighter-weight, fully DB-free alternative that uses plain Python callables
instead of ``@api.depends`` compute methods.
"""

import functools
import logging
from collections import defaultdict, deque
from collections.abc import Iterable, Mapping
from contextlib import contextmanager, suppress
from datetime import UTC, datetime
from operator import attrgetter
from typing import TYPE_CHECKING

from odoo.db import BaseCursor
from odoo.libs.collections.misc import Collector
from odoo.tools import OrderedSet

from . import registration
from .components.storage import DictBackend
from .models import AbstractModel
from .primitives import SUPERUSER_ID
from .runtime.transaction import Transaction

if TYPE_CHECKING:
    from .models.base import BaseModel
    from .runtime.registry import Registry

_logger = logging.getLogger("odoo.orm.testing")


# ---------------------------------------------------------------------------
# Minimal 'base' model for testing
# ---------------------------------------------------------------------------


class _TestBase(AbstractModel):
    """Minimal ``base`` model for :class:`ModelRegistry`.

    Every model implicitly inherits from ``base``.  This class provides
    just enough for the registration machinery to work without importing
    the full ``odoo.addons.base`` module tree.

    ``_register = False`` prevents :class:`MetaModel.__init__` from
    appending this class to ``_module_to_models__``, so it never
    interferes with real module loading.
    """

    _name = "base"
    _description = "Base"
    _register = False
    _module = None


# ---------------------------------------------------------------------------
# InMemoryCursor (existing)
# ---------------------------------------------------------------------------


class InMemoryCursor(BaseCursor):
    """Cursor backed by fixture data — no PostgreSQL required.

    Inherits :class:`~odoo.db.BaseCursor` to obtain the callback containers
    (``precommit``, ``postcommit``, ``prerollback``, ``postrollback``) and
    the ``savepoint()`` / ``flush()`` machinery without reimplementing them.

    The key trick: :meth:`__init__` pre-builds ``Transaction(registry)`` and
    assigns it to ``self.transaction``.  When
    :meth:`~odoo.orm.runtime.environment.Environment.__new__` checks
    ``cr.transaction``, it finds a non-``None`` value and skips the
    ``Transaction(Registry(cr.dbname))`` call — no database connection is
    ever made.

    A :class:`~odoo.orm.components.storage.DictBackend` is created and
    attached to the transaction as ``storage``.  When ORM CRUD methods
    detect ``transaction.storage is not None``, they dispatch to the
    in-memory backend instead of generating SQL.

    :param registry: Pre-built model registry (e.g. ``self.env.registry``
        in a :class:`~odoo.tests.common.TransactionCase`).
    :param fixtures: Optional mapping of query strings to result row lists.
        When ``execute(query)`` is called, the string representation of
        *query* is looked up in this dict.  Unrecognised queries return an
        empty result set (``[]``).
    """

    def __init__(
        self,
        registry: Registry,
        fixtures: dict[str, list[tuple]] | None = None,
    ) -> None:
        super().__init__()
        self.dbname = registry.db_name
        # In-memory storage for backend-agnostic CRUD
        self.storage = DictBackend()
        # Pre-build Transaction so Environment.__new__ skips Registry(cr.dbname)
        self.transaction = Transaction(registry, storage=self.storage)
        self._fixtures: dict[str, list[tuple]] = fixtures or {}
        self._last_result: list[tuple] = []

    # ------------------------------------------------------------------
    # Query execution — fixture-backed
    # ------------------------------------------------------------------

    def execute(self, query, params=None, log_exceptions: bool = True) -> None:
        """Look up *query* in the fixture dict; default to empty result."""
        self._last_result = self._fixtures.get(str(query), [])

    def fetchall(self) -> list[tuple]:
        """Return all rows from the last executed query."""
        return list(self._last_result)

    def fetchone(self) -> tuple | None:
        """Return the first row from the last executed query, or ``None``."""
        return self._last_result[0] if self._last_result else None

    def fetchmany(self, size: int) -> list[tuple]:
        """Return up to *size* rows from the last executed query."""
        return self._last_result[:size]

    def fetchscalar(self):
        """Return the first column of the first row, or ``None``."""
        row = self.fetchone()
        return row[0] if row else None

    def dictfetchone(self) -> dict | None:
        """Return ``None`` — no column metadata available without a real cursor."""
        return None

    def dictfetchall(self) -> list[dict]:
        """Return ``[]`` — no column metadata available without a real cursor."""
        return []

    # ------------------------------------------------------------------
    # Time
    # ------------------------------------------------------------------

    def now(self) -> datetime:
        """Return the current wall-clock time as a naive UTC datetime.

        The real cursor fetches ``now()`` from PostgreSQL for transaction
        consistency.  InMemoryCursor uses the local clock instead — suitable
        for tests that check *that* a timestamp is set, not its exact value.
        """
        return datetime.now(UTC).replace(tzinfo=None)

    # ------------------------------------------------------------------
    # Transaction control — no-ops
    # ------------------------------------------------------------------

    @contextmanager
    def pipeline(self):
        """No-op context manager — no real connection to pipeline."""
        yield

    def commit(self) -> None:
        """No-op — InMemoryCursor has no underlying connection to commit."""

    def rollback(self) -> None:
        """No-op — InMemoryCursor has no underlying connection to roll back."""

    def close(self) -> None:
        """No-op — there is no connection to close."""


# ---------------------------------------------------------------------------
# ModelRegistry — lightweight registry from class definitions
# ---------------------------------------------------------------------------


class ModelRegistry(Mapping):
    """Lightweight model registry built from Python class definitions.

    Satisfies the same interface that :class:`Environment` and
    :class:`Transaction` need from :class:`Registry`, without database
    access or module loading.

    The real :class:`Registry` (~2 000 lines) performs addon scanning,
    database table creation, translation setup, and caching.  For testing
    model methods in isolation, none of that is needed — just a
    ``Mapping[str, type[BaseModel]]`` with initialized field descriptors.

    Usage::

        from odoo.addons.base.models.res_partner import Partner

        registry = ModelRegistry([Partner])
        assert "res.partner" in registry
        assert "base" in registry  # auto-injected

    :param model_defs: Iterable of model definition classes.  The ``base``
        model is auto-injected if not provided.
    :param db_name: Fake database name (default ``":memory:"``).
    """

    def __init__(
        self,
        model_defs: Iterable[type[BaseModel]],
        *,
        db_name: str = ":memory:",
    ) -> None:
        self.db_name = db_name
        self.models: dict[str, type[BaseModel]] = {}

        # Attributes accessed by registration._setup() and _setup_fields().
        # Setting _init_modules=False skips manual (Studio/custom) field
        # loading.  Empty dicts for translated/company_dependent fields
        # skip the database-state patching that prevents data loss during
        # module upgrades — irrelevant for testing.
        self._init_modules = False
        self._database_translated_fields: dict[str, str] = {}
        self._database_company_dependent_fields: dict[str, str] = {}
        self.many2many_relations: Collector = Collector()
        self.field_setup_dependents: Collector = Collector()
        self.many2one_company_dependents: Collector = Collector()

        # Field dependency tracking — same interface as the real
        # Registry.field_depends / field_depends_context properties,
        # which delegate to model_graph._depends / _depends_context.
        self._field_depends: dict = {}
        self._field_depends_context: dict = {}

        # ormcache support — the decorator accesses pool._Registry__caches
        # (name-mangled) to store method results.  defaultdict(dict) gives
        # each cache name an auto-created dict (no LRU eviction needed in
        # tests — datasets are small).
        self._Registry__caches: dict[str, dict] = defaultdict(dict)

        # Registry-loading state — True means "fully loaded, normal operation".
        # Checked by _prepare_create_values to allow/disallow log_access fields.
        self.ready = True

        # Domain optimizer checks which fields have NOT NULL constraints.
        # Populated during _build after field setup.
        self.not_null_fields: set = set()

        # DB-only hooks — no-ops in test registry.  Model field setup code
        # calls these to register foreign keys, constraints, and post-init
        # callbacks.  They're only meaningful for real database registries.
        self.has_trigram = False

        self._build(list(model_defs))

    # ------------------------------------------------------------------
    # Mapping protocol
    # ------------------------------------------------------------------

    def __getitem__(self, model_name: str) -> type[BaseModel]:
        return self.models[model_name]

    def __contains__(self, model_name: object) -> bool:
        return model_name in self.models

    def __iter__(self):
        return iter(self.models)

    def __len__(self):
        return len(self.models)

    # Registry-compatible mutation (used by add_to_registry)
    def __setitem__(self, model_name: str, model: type[BaseModel]) -> None:
        self.models[model_name] = model

    def __delitem__(self, model_name: str) -> None:
        del self.models[model_name]

    # ------------------------------------------------------------------
    # Registry-compatible properties
    # ------------------------------------------------------------------

    @property
    def field_depends(self) -> dict:
        """Field → tuple of dependency field names."""
        return self._field_depends

    @property
    def field_depends_context(self) -> dict:
        """Field → tuple of context key names."""
        return self._field_depends_context

    @functools.cached_property
    def field_computed(self) -> dict:
        """Map each computed field to the list of co-computed fields.

        Same semantics as :attr:`Registry.field_computed`: fields that
        share a ``compute`` method are grouped together so the ORM can
        protect them atomically during create/write.
        """
        computed: dict = {}
        for model_cls in self.models.values():
            groups: defaultdict = defaultdict(list)
            for field in model_cls._fields.values():
                if field.compute:
                    computed[field] = group = groups[field.compute]
                    group.append(field)
        return computed

    @functools.cached_property
    def field_inverses(self) -> Collector:
        """Map each relational field to its inverse fields.

        Calls ``field.setup_inverses()`` for every relational field, same
        as :attr:`Registry.field_inverses`.
        """
        result: Collector = Collector()
        for model_cls in self.models.values():
            for field in model_cls._fields.values():
                if field.relational:
                    try:
                        field.setup_inverses(self, result)
                    except Exception:
                        _logger.debug(
                            "setup_inverses for %s.%s failed",
                            model_cls._name,
                            field.name,
                        )
        return result

    @functools.cached_property
    def _field_triggers(self) -> dict:
        """Empty trigger map — no cascading recomputation in test registry.

        The real Registry delegates to ``model_graph._triggers``.  With an
        empty dict the ``_modified_trigger_loop`` fast path is always taken,
        meaning compute methods must be called explicitly in tests.
        """
        return {}

    def is_modifying_relations(self, field) -> bool:
        """Return whether modifying *field* might change dependent records.

        Always returns ``False`` in :class:`ModelRegistry` — no trigger
        graph is built for the test registry.
        """
        return False

    def get_trigger_tree(self, fields, select=bool):
        """Return an empty trigger tree — no trigger graph in tests."""
        return {}

    def get_dependent_fields(self, field):
        """Yield nothing — no field dependency graph in tests."""
        return iter(())

    # ------------------------------------------------------------------
    # No-op stubs for DB-only Registry methods
    # ------------------------------------------------------------------

    def post_init(self, func, *args, **kwargs) -> None:
        """No-op — post-init callbacks are for real module loading."""

    def post_constraint(self, cr, func, key) -> None:
        """No-op — constraint callbacks need a real database."""

    def add_foreign_key(self, *args, **kwargs) -> None:
        """No-op — foreign keys need a real database."""

    def reset_changes(self) -> None:
        """No-op — change tracking is for multi-process signaling."""

    def clear_cache(self, *cache_names: str) -> None:
        """Clear ormcache entries.  Models call this after CRUD to invalidate
        cached lookups (e.g. currencies, countries).  In test registries we
        simply clear the relevant dicts in ``_Registry__caches``."""
        for _cache_name in cache_names or ("default",):
            for cache in self._Registry__caches.values():
                if cache:
                    cache.clear()

    def is_an_ordinary_table(self, model) -> bool:
        """Return ``True`` — assume all models have tables in tests."""
        return True

    @staticmethod
    def unaccent(text):
        """Identity function — no PostgreSQL unaccent in tests."""
        return text

    @staticmethod
    def unaccent_python(text):
        """Identity function — no accent removal in tests."""
        return text

    # ------------------------------------------------------------------
    # Registry-compatible methods
    # ------------------------------------------------------------------

    def descendants(
        self,
        model_names: Iterable[str],
        *kinds: str,
    ) -> OrderedSet:
        """Return *model_names* and all models that inherit from them.

        Implements the same BFS traversal as :meth:`Registry.descendants`.
        """
        funcs = [attrgetter(kind + "_children") for kind in kinds]
        result: OrderedSet[str] = OrderedSet()
        queue = deque(model_names)
        while queue:
            name = queue.popleft()
            model = self.models.get(name)
            if model is None or model._name in result:
                continue
            result.add(model._name)
            for func in funcs:
                queue.extend(func(model))
        return result

    # ------------------------------------------------------------------
    # Internal: build the registry
    # ------------------------------------------------------------------

    def _build(self, model_defs: list[type[BaseModel]]) -> None:
        """Register model definitions and set up field descriptors.

        Auto-discovers ALL model definitions from the same modules as the
        provided classes (via ``MetaModel._module_to_models__``).  This
        ensures parent models, mixins, and extensions are registered in
        the correct dependency order — callers only need to name the
        models they actually want to test.
        """
        from .models.metaclass import MetaModel

        # 1. Determine which modules we need (always include 'base')
        modules = {"base"}
        for cls in model_defs:
            module = getattr(cls, "_module", None)
            if module:
                modules.add(module)

        # 2. Collect ALL model definitions from those modules,
        #    preserving import order (which respects dependencies).
        #    Process 'base' first since all models inherit from it.
        all_defs: list[type[BaseModel]] = []
        seen_ids: set[int] = set()

        for module in sorted(modules, key=lambda m: (m != "base", m)):
            for cls in MetaModel._module_to_models__.get(module, []):
                if id(cls) not in seen_ids:
                    seen_ids.add(id(cls))
                    all_defs.append(cls)

        # 3. Add any user-provided classes not already covered
        #    (e.g., classes with _register=False or from unregistered modules)
        for cls in model_defs:
            if id(cls) not in seen_ids:
                seen_ids.add(id(cls))
                all_defs.append(cls)

        # 4. Ensure 'base' is present — fallback to _TestBase when the
        #    full base module wasn't imported
        has_base = any(getattr(cls, "_name", None) == "base" for cls in all_defs)
        if not has_base:
            all_defs.insert(0, _TestBase)

        # 5. Stable sort: 'base'-named models first (root of all models)
        all_defs.sort(
            key=lambda c: 0 if getattr(c, "_name", "") == "base" else 1,
        )

        # 6. Register each definition class (creates registry model classes)
        for model_def in all_defs:
            registration.add_to_registry(self, model_def)

        # 7. Create a temporary Environment for field setup
        cr = InMemoryCursor(self)
        from .runtime.environment import Environment

        env = Environment(cr, SUPERUSER_ID, {})

        # 8. Prepare → setup → setup_fields (simplified _setup_models__)
        model_classes = list(self.models.values())

        for model_cls in model_classes:
            registration._prepare_setup(model_cls)

        for model_cls in model_classes:
            registration._setup(model_cls, env)

        for model_cls in model_classes:
            self._setup_fields_lenient(model_cls, env)

        # 9. Resolve field dependencies (for cache_key / recomputation)
        for model_cls in self.models.values():
            model = model_cls(env, (), ())
            for field in model._fields.values():
                try:
                    depends, depends_context = field.get_depends(model)
                    self._field_depends[field] = tuple(depends)
                    self._field_depends_context[field] = tuple(depends_context)
                except Exception:
                    self._field_depends[field] = ()
                    self._field_depends_context[field] = ()

        # 10. Populate not_null_fields (for domain optimizer)
        for model_cls in self.models.values():
            if model_cls._auto and not model_cls._abstract:
                for field in model_cls._fields.values():
                    if field.name == "id" or (
                        field.column_type and field.store and field.required
                    ):
                        self.not_null_fields.add(field)

        # 11. Post-setup hooks (no-op on BaseModel, may do work on subclasses)
        for model_cls in model_classes:
            try:
                model_cls(env, (), ())._post_model_setup__()
            except Exception:
                _logger.debug(
                    "Post-setup hook for %s failed (expected in test registry)",
                    model_cls._name,
                    exc_info=True,
                )

    @staticmethod
    def _setup_fields_lenient(
        model_cls: type[BaseModel],
        env: Environment,
    ) -> None:
        """Set up field descriptors, tolerating missing comodels.

        Unlike :func:`registration._setup_fields`, which raises on any
        non-manual field error, this version catches exceptions and marks
        the field as ``_setup_done = True``.  If a test later accesses a
        field whose comodel was not registered, it will get a clear
        runtime error at that point rather than a cryptic setup failure.
        """
        model = model_cls(env, (), ())
        for name, field in model_cls._fields.items():
            try:
                field.setup(model)
            except Exception:
                _logger.debug(
                    "Field %s.%s setup incomplete (missing comodel?); field will raise if accessed in test",
                    model_cls._name,
                    name,
                )
                field._setup_done = True
            else:
                # Track company-dependent Many2one fields (mirrors _setup_fields)
                if field.type == "many2one" and field.company_dependent:
                    model_cls.pool.many2one_company_dependents.add(
                        field.comodel_name,
                        field,
                    )


# ---------------------------------------------------------------------------
# model_test_env — convenience context manager
# ---------------------------------------------------------------------------


@contextmanager
def model_test_env(
    *model_classes: type[BaseModel],
    registry: ModelRegistry | None = None,
    db_name: str = ":memory:",
):
    """Create a database-free :class:`Environment` for testing model methods.

    Builds a :class:`ModelRegistry` from the given model definition classes,
    creates a fresh :class:`InMemoryCursor` with a :class:`DictBackend`, and
    yields a fully functional :class:`Environment`.

    CRUD operations (``create``, ``write``, ``unlink``, ``search``) dispatch
    to the in-memory backend.  Compute methods, field access, and
    ``filtered``/``mapped``/``sorted`` work exactly as in production.

    Usage::

        from odoo.addons.base.models.res_partner import Partner
        from odoo.orm.testing import model_test_env

        with model_test_env(Partner) as env:
            partner = env["res.partner"].create({"name": "Alice"})
            partner._compute_display_name()
            assert partner.display_name == "Alice"

            found = env["res.partner"].search([("name", "=", "Alice")])
            assert found == partner

    For performance, build the registry once and reuse it::

        registry = ModelRegistry([Partner])
        with model_test_env(registry=registry) as env:
            ...  # fresh cursor + storage, same registry

    :param model_classes: One or more model definition classes.  The ``base``
        model is auto-injected if not included.  Ignored when *registry* is
        provided.
    :param registry: Pre-built :class:`ModelRegistry` to reuse.  When given,
        *model_classes* and *db_name* are ignored.  Each call still gets a
        fresh :class:`InMemoryCursor` and :class:`DictBackend`, so tests are
        fully isolated.
    :param db_name: Fake database name (default ``":memory:"``).
    :yields: A fully functional :class:`Environment` backed by in-memory
        storage.
    """
    if registry is None:
        registry = ModelRegistry(model_classes, db_name=db_name)

    # Clear ormcaches from any previous use of this registry.
    # When reusing a registry across tests, cached method results may
    # reference record IDs from a previous DictBackend.  Clearing
    # ensures each test starts with a clean slate.
    for cache in registry._Registry__caches.values():
        cache.clear()

    # Also clear cached_property values that reference old Transaction data
    # (field_computed, field_inverses are stable; _field_triggers may not be).
    for attr in ("_field_triggers",):
        with suppress(AttributeError):
            delattr(registry, attr)

    cr = InMemoryCursor(registry)

    # Pre-seed minimal records so env.user / env.company resolve.
    # Many model methods (even simple create) access env.company via
    # ormcache keys, which triggers env.user.company_id → fetch from
    # DictBackend.  Without seed data, this fetch returns nothing.
    _seed_fixtures(cr.storage, registry)

    from .runtime.environment import Environment

    env = Environment(cr, SUPERUSER_ID, {})
    yield env


def _seed_fixtures(storage: DictBackend, registry: ModelRegistry) -> None:
    """Insert minimal records into *storage* for ``env.user`` / ``env.company``.

    These records satisfy the chain::

        env.company → env.user.company_id → fetch res_users id=1 → company_id=1
                    → fetch res_company id=1 → partner_id=1

    Without them, any model method that accesses ``env.company`` (directly
    or via an ormcache key) would fail with a missing-record error.
    """

    def _inject(table: str, record_id: int, data: dict) -> None:
        """Insert a record with a specific ID, bypassing auto-increment."""
        tbl = storage._tables.setdefault(table, {})
        data["id"] = record_id
        tbl[record_id] = data
        storage._sequences[table] = max(storage._sequences[table], record_id)

    # Partner for the company (id=1)
    if "res.partner" in registry:
        _inject(
            "res_partner",
            1,
            {
                "name": "Test Company",
                "active": True,
                "is_company": True,
                "type": "contact",
            },
        )

    # Company (id=1)
    if "res.company" in registry:
        _inject(
            "res_company",
            1,
            {
                "name": "Test Company",
                "active": True,
                "partner_id": 1,
                "parent_path": "1/",
            },
        )

    # Superuser (id=1 = SUPERUSER_ID)
    if "res.users" in registry:
        _inject(
            "res_users",
            1,
            {
                "name": "Admin",
                "login": "admin",
                "active": True,
                "company_id": 1,
                "company_ids": (1,),
                "partner_id": 1,
            },
        )
