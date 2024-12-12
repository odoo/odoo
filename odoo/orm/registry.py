# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Models registries.

"""
from __future__ import annotations

import inspect
import logging
import os
import threading
import time
import typing
import warnings
from collections import defaultdict, deque
from collections.abc import Mapping
from contextlib import closing, contextmanager, nullcontext
from functools import partial
from operator import attrgetter

import psycopg2.sql

import odoo
from odoo import SUPERUSER_ID
from odoo.modules.db import FunctionStatus
from odoo.sql_db import TestCursor
from odoo.tools import (
    SQL,
    OrderedSet,
    config,
    lazy_classproperty,
    lazy_property,
    remove_accents,
    sql,
)
from odoo.tools.func import locked
from odoo.tools.lru import LRU
from odoo.tools.misc import Collector, format_frame

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterable, Iterator, MutableMapping
    from odoo.fields import Field
    from odoo.models import BaseModel
    from odoo.sql_db import BaseCursor, Connection, Cursor
    from odoo.modules import graph


_logger = logging.getLogger('odoo.registry')
_schema = logging.getLogger('odoo.schema')


_REGISTRY_CACHES = {
    'default': 8192,
    'assets': 512, # arbitrary
    'templates': 1024, # arbitrary
    'routing': 1024,  # 2 entries per website
    'routing.rewrites': 8192,  # url_rewrite entries
    'templates.cached_values': 2048, # arbitrary
    'groups': 1,  # contains all res.groups
}

# cache invalidation dependencies, as follows:
# { 'cache_key': ('cache_container_1', 'cache_container_3', ...) }
_CACHES_BY_KEY = {
    'default': ('default', 'templates.cached_values'),
    'assets': ('assets', 'templates.cached_values'),
    'templates': ('templates', 'templates.cached_values'),
    'routing': ('routing', 'routing.rewrites', 'templates.cached_values'),
    'groups': ('groups', 'templates', 'templates.cached_values'),  # The processing of groups is saved in the view
}


def _unaccent(x: SQL | str | psycopg2.sql.Composable) -> SQL | str | psycopg2.sql.Composed:
    if isinstance(x, SQL):
        return SQL("unaccent(%s)", x)
    if isinstance(x, psycopg2.sql.Composable):
        return psycopg2.sql.SQL('unaccent({})').format(x)
    return f'unaccent({x})'


class Registry(Mapping[str, type["BaseModel"]]):
    """ Model registry for a particular database.

    The registry is essentially a mapping between model names and model classes.
    There is one registry instance per database.

    """
    _lock: threading.RLock | DummyRLock = threading.RLock()
    _saved_lock: threading.RLock | DummyRLock | None = None

    @lazy_classproperty
    def registries(cls) -> MutableMapping[str, Registry]:
        """ A mapping from database names to registries. """
        size = config.get('registry_lru_size', None)
        if not size:
            # Size the LRU depending of the memory limits
            if os.name != 'posix':
                # cannot specify the memory limit soft on windows...
                size = 42
            else:
                # A registry takes 10MB of memory on average, so we reserve
                # 10Mb (registry) + 5Mb (working memory) per registry
                avgsz = 15 * 1024 * 1024
                size = int(config['limit_memory_soft'] / avgsz)
        return LRU(size)

    def __new__(cls, db_name: str):
        """ Return the registry for the given database name."""
        assert db_name, "Missing database name"
        with cls._lock:
            try:
                return cls.registries[db_name]
            except KeyError:
                return cls.new(db_name)

    _init: bool  # whether init needs to be done
    ready: bool  # whether everything is set up
    loaded: bool  # whether all modules are loaded
    models: dict[str, type[BaseModel]]

    @classmethod
    @locked
    def new(cls, db_name: str, force_demo: bool = False, status: None = None, update_module: bool = False) -> Registry:
        """ Create and return a new registry for the given database name. """
        if status is not None:
            warnings.warn("Deprecated since 19.0, do not set status", DeprecationWarning)
        t0 = time.time()
        registry: Registry = object.__new__(cls)
        registry.init(db_name)
        registry.new = registry.init = registry.registries = None  # type: ignore

        # Initializing a registry will call general code which will in
        # turn call Registry() to obtain the registry being initialized.
        # Make it available in the registries dictionary then remove it
        # if an exception is raised.
        cls.delete(db_name)
        cls.registries[db_name] = registry  # pylint: disable=unsupported-assignment-operation
        try:
            registry.setup_signaling()
            # This should be a method on Registry
            from odoo.modules.loading import load_modules, reset_modules_state  # noqa: PLC0415
            try:
                load_modules(registry, force_demo, update_module=update_module)
            except Exception:
                reset_modules_state(db_name)
                raise
        except Exception:
            _logger.error('Failed to load registry')
            del cls.registries[db_name]     # pylint: disable=unsupported-delete-operation
            raise

        # load_modules() above can replace the registry by calling
        # indirectly new() again (when modules have to be uninstalled).
        # Yeah, crazy.
        registry = cls.registries[db_name]  # pylint: disable=unsubscriptable-object

        registry._init = False
        registry.ready = True
        registry.registry_invalidated = bool(update_module)
        registry.signal_changes()

        _logger.info("Registry loaded in %.3fs", time.time() - t0)
        return registry

    def init(self, db_name: str) -> None:
        self._init = True
        self.loaded = False
        self.ready = False

        self.models: dict[str, type[BaseModel]] = {}    # model name/model instance mapping
        self._sql_constraints = set()  # type: ignore
        self._database_translated_fields: set[str] = set()  # names of translated fields in database "{model}.{field_name}"
        if config['test_enable'] or config['test_file']:
            from odoo.tests.result import OdooTestResult  # noqa: PLC0415
            self._assertion_report: OdooTestResult | None = OdooTestResult()
        else:
            self._assertion_report = None
        self._ordinary_tables: set[str] | None = None  # cached names of regular tables
        self._constraint_queue: deque[tuple] = deque()  # queue of functions to call on finalization of constraints
        self.__caches: dict[str, LRU] = {cache_name: LRU(cache_size) for cache_name, cache_size in _REGISTRY_CACHES.items()}

        # modules fully loaded (maintained during init phase by `loading` module)
        self._init_modules: set[str] = set()
        self.updated_modules: list[str] = []       # installed/updated modules
        self.loaded_xmlids: set[str] = set()

        self.db_name = db_name
        self._db: Connection = odoo.sql_db.db_connect(db_name, readonly=False)
        self._db_readonly: Connection | None = None
        if config['db_replica_host'] is not False or config['test_enable']:  # by default, only use readonly pool if we have a db_replica_host defined. Allows to have an empty replica host for testing
            self._db_readonly = odoo.sql_db.db_connect(db_name, readonly=True)

        # cursor for test mode; None means "normal" mode
        self.test_cr: Cursor | None = None
        self.test_lock: threading.RLock | None = None

        # field dependencies
        self.field_depends: Collector[Field, tuple[Field, ...]] = Collector()
        self.field_depends_context: Collector[Field, tuple[str, ...]] = Collector()
        self.field_inverses: Collector[Field, tuple[Field, ...]] = Collector()

        # company dependent
        self.many2one_company_dependents: Collector[str, tuple[Field, ...]] = Collector()  # {model_name: (field1, field2, ...)}

        # cache of methods get_field_trigger_tree() and is_modifying_relations()
        self._field_trigger_trees: dict[Field, TriggerTree] = {}
        self._is_modifying_relations: dict[Field, bool] = {}

        # Inter-process signaling:
        # The `orm_signaling_registry` sequence indicates the whole registry
        # must be reloaded.
        # The `orm_signaling_... sequence` indicates the corresponding cache must be
        # invalidated (i.e. cleared).
        self.registry_sequence: int = -1
        self.cache_sequences: dict[str, int] = {}

        # Flags indicating invalidation of the registry or the cache.
        self._invalidation_flags = threading.local()

        with closing(self.cursor()) as cr:
            self.has_unaccent = odoo.modules.db.has_unaccent(cr)
            self.has_trigram = odoo.modules.db.has_trigram(cr)

        self.unaccent = _unaccent if self.has_unaccent else lambda x: x  # type: ignore
        self.unaccent_python = remove_accents if self.has_unaccent else lambda x: x

    @classmethod
    @locked
    def delete(cls, db_name: str) -> None:
        """ Delete the registry linked to a given database. """
        if db_name in cls.registries:  # pylint: disable=unsupported-membership-test
            del cls.registries[db_name]  # pylint: disable=unsupported-delete-operation

    @classmethod
    @locked
    def delete_all(cls):
        """ Delete all the registries. """
        cls.registries.clear()

    #
    # Mapping abstract methods implementation
    # => mixin provides methods keys, items, values, get, __eq__, and __ne__
    #
    def __len__(self):
        """ Return the size of the registry. """
        return len(self.models)

    def __iter__(self):
        """ Return an iterator over all model names. """
        return iter(self.models)

    def __getitem__(self, model_name: str) -> type[BaseModel]:
        """ Return the model with the given name or raise KeyError if it doesn't exist."""
        return self.models[model_name]

    def __call__(self, model_name: str) -> type[BaseModel]:
        """ Same as ``self[model_name]``. """
        return self.models[model_name]

    def __setitem__(self, model_name: str, model: type[BaseModel]):
        """ Add or replace a model in the registry."""
        self.models[model_name] = model

    def __delitem__(self, model_name: str):
        """ Remove a (custom) model from the registry. """
        del self.models[model_name]
        # the custom model can inherit from mixins ('mail.thread', ...)
        for Model in self.models.values():
            Model._inherit_children.discard(model_name)

    def descendants(self, model_names: Iterable[str], *kinds: typing.Literal['_inherit', '_inherits']) -> OrderedSet[str]:
        """ Return the models corresponding to ``model_names`` and all those
        that inherit/inherits from them.
        """
        assert all(kind in ('_inherit', '_inherits') for kind in kinds)
        funcs = [attrgetter(kind + '_children') for kind in kinds]

        models: OrderedSet[str] = OrderedSet()
        queue = deque(model_names)
        while queue:
            model = self[queue.popleft()]
            models.add(model._name)
            for func in funcs:
                queue.extend(func(model))
        return models

    def load(self, cr: Cursor, module: graph.Node) -> OrderedSet[str]:
        """ Load a given module in the registry, and return the names of the
        modified models.

        At the Python level, the modules are already loaded, but not yet on a
        per-registry level. This method populates a registry with the given
        modules, i.e. it instantiates all the classes of a the given module
        and registers them in the registry.

        """
        from . import models  # noqa: PLC0415

        # clear cache to ensure consistency, but do not signal it
        for cache in self.__caches.values():
            cache.clear()

        lazy_property.reset_all(self)
        self._field_trigger_trees.clear()
        self._is_modifying_relations.clear()

        # Instantiate registered classes (via the MetaModel automatic discovery
        # or via explicit constructor call), and add them to the pool.
        model_names = []
        for cls in models.MetaModel.module_to_models.get(module.name, []):
            # models register themselves in self.models
            model = cls._build_model(self, cr)
            model_names.append(model._name)

        return self.descendants(model_names, '_inherit', '_inherits')

    @locked
    def setup_models(self, cr: BaseCursor) -> None:
        """ Complete the setup of models.
            This must be called after loading modules and before using the ORM.
        """
        env = odoo.api.Environment(cr, SUPERUSER_ID, {})
        env.invalidate_all()

        # Uninstall registry hooks. Because of the condition, this only happens
        # on a fully loaded registry, and not on a registry being loaded.
        if self.ready:
            for model in env.values():
                model._unregister_hook()

        # clear cache to ensure consistency, but do not signal it
        for cache in self.__caches.values():
            cache.clear()

        lazy_property.reset_all(self)
        self._field_trigger_trees.clear()
        self._is_modifying_relations.clear()
        self.registry_invalidated = True

        # we must setup ir.model before adding manual fields because _add_manual_models may
        # depend on behavior that is implemented through overrides, such as is_mail_thread which
        # is implemented through an override to env['ir.model']._instanciate
        env['ir.model']._prepare_setup()

        # add manual models
        if self._init_modules:
            env['ir.model']._add_manual_models()

        # prepare the setup on all models
        models = list(env.values())
        for model in models:
            model._prepare_setup()

        self.field_depends.clear()
        self.field_depends_context.clear()
        self.field_inverses.clear()
        self.many2one_company_dependents.clear()

        # do the actual setup
        for model in models:
            model._setup_base()

        self._m2m: defaultdict[tuple[str, str, str], list[Field]] = defaultdict(list)
        for model in models:
            model._setup_fields()
        del self._m2m

        for model in models:
            model._setup_complete()

        # determine field_depends and field_depends_context
        for model in models:
            for field in model._fields.values():
                depends, depends_context = field.get_depends(model)
                self.field_depends[field] = tuple(depends)
                self.field_depends_context[field] = tuple(depends_context)

        # clean the lazy_property again in case they are cached by another ongoing registry readonly request
        lazy_property.reset_all(self)

        # Reinstall registry hooks. Because of the condition, this only happens
        # on a fully loaded registry, and not on a registry being loaded.
        if self.ready:
            for model in env.values():
                model._register_hook()
            env.flush_all()

    @lazy_property
    def field_computed(self) -> dict[Field, list[Field]]:
        """ Return a dict mapping each field to the fields computed by the same method. """
        computed: dict[Field, list[Field]] = {}
        for model_name, Model in self.models.items():
            groups: defaultdict[Field, list[Field]] = defaultdict(list)
            for field in Model._fields.values():
                if field.compute:
                    computed[field] = group = groups[field.compute]
                    group.append(field)
            for fields in groups.values():
                if len(fields) < 2:
                    continue
                if len({field.compute_sudo for field in fields}) > 1:
                    fnames = ", ".join(field.name for field in fields)
                    warnings.warn(
                        f"{model_name}: inconsistent 'compute_sudo' for computed fields {fnames}. "
                        f"Either set 'compute_sudo' to the same value on all those fields, or "
                        f"use distinct compute methods for sudoed and non-sudoed fields.",
                        stacklevel=1,
                    )
                if len({field.precompute for field in fields}) > 1:
                    fnames = ", ".join(field.name for field in fields)
                    warnings.warn(
                        f"{model_name}: inconsistent 'precompute' for computed fields {fnames}. "
                        f"Either set all fields as precompute=True (if possible), or "
                        f"use distinct compute methods for precomputed and non-precomputed fields.",
                        stacklevel=1,
                    )
                if len({field.store for field in fields}) > 1:
                    fnames1 = ", ".join(field.name for field in fields if not field.store)
                    fnames2 = ", ".join(field.name for field in fields if field.store)
                    warnings.warn(
                        f"{model_name}: inconsistent 'store' for computed fields, "
                        f"accessing {fnames1} may recompute and update {fnames2}. "
                        f"Use distinct compute methods for stored and non-stored fields.",
                        stacklevel=1,
                    )
        return computed

    def get_trigger_tree(self, fields: list[Field], select: Callable[[Field], bool] = bool) -> TriggerTree:
        """ Return the trigger tree to traverse when ``fields`` have been modified.
        The function ``select`` is called on every field to determine which fields
        should be kept in the tree nodes.  This enables to discard some unnecessary
        fields from the tree nodes.
        """
        trees = [
            self.get_field_trigger_tree(field)
            for field in fields
            if field in self._field_triggers
        ]
        return TriggerTree.merge(trees, select)

    def get_dependent_fields(self, field: Field) -> Iterator[Field]:
        """ Return an iterable on the fields that depend on ``field``. """
        if field not in self._field_triggers:
            return

        for tree in self.get_field_trigger_tree(field).depth_first():
            yield from tree.root

    def _discard_fields(self, fields: list[Field]) -> None:
        """ Discard the given fields from the registry's internal data structures. """
        for f in fields:
            # tests usually don't reload the registry, so when they create
            # custom fields those may not have the entire dependency setup, and
            # may be missing from these maps
            self.field_depends.pop(f, None)

        # discard fields from field triggers
        self.__dict__.pop('_field_triggers', None)
        self._field_trigger_trees.clear()
        self._is_modifying_relations.clear()

        # discard fields from field inverses
        self.field_inverses.discard_keys_and_values(fields)

    def get_field_trigger_tree(self, field: Field) -> TriggerTree:
        """ Return the trigger tree of a field by computing it from the transitive
        closure of field triggers.
        """
        try:
            return self._field_trigger_trees[field]
        except KeyError:
            pass

        triggers = self._field_triggers

        if field not in triggers:
            return TriggerTree()

        def transitive_triggers(field, prefix=(), seen=()):
            if field in seen or field not in triggers:
                return
            for path, targets in triggers[field].items():
                full_path = concat(prefix, path)
                yield full_path, targets
                for target in targets:
                    yield from transitive_triggers(target, full_path, seen + (field,))

        def concat(seq1, seq2):
            if seq1 and seq2:
                f1, f2 = seq1[-1], seq2[0]
                if (
                    f1.type == 'many2one' and f2.type == 'one2many'
                    and f1.name == f2.inverse_name
                    and f1.model_name == f2.comodel_name
                    and f1.comodel_name == f2.model_name
                ):
                    return concat(seq1[:-1], seq2[1:])
            return seq1 + seq2

        tree = TriggerTree()
        for path, targets in transitive_triggers(field):
            current = tree
            for label in path:
                current = current.increase(label)
            if current.root:
                assert isinstance(current.root, OrderedSet)
                current.root.update(targets)
            else:
                current.root = OrderedSet(targets)

        self._field_trigger_trees[field] = tree

        return tree

    @lazy_property
    def _field_triggers(self) -> defaultdict[Field, defaultdict[tuple[str, ...], OrderedSet[Field]]]:
        """ Return the field triggers, i.e., the inverse of field dependencies,
        as a dictionary like ``{field: {path: fields}}``, where ``field`` is a
        dependency, ``path`` is a sequence of fields to inverse and ``fields``
        is a collection of fields that depend on ``field``.
        """
        triggers: defaultdict[Field, defaultdict[tuple[str, ...], OrderedSet[Field]]] = defaultdict(lambda: defaultdict(OrderedSet))

        for Model in self.models.values():
            if Model._abstract:
                continue
            for field in Model._fields.values():
                try:
                    dependencies = list(field.resolve_depends(self))
                except Exception:
                    # dependencies of custom fields may not exist; ignore that case
                    if not field.base_field.manual:
                        raise
                else:
                    for dependency in dependencies:
                        *path, dep_field = dependency
                        triggers[dep_field][tuple(reversed(path))].add(field)

        return triggers

    def is_modifying_relations(self, field: Field) -> bool:
        """ Return whether ``field`` has dependent fields on some records, and
        that modifying ``field`` might change the dependent records.
        """
        try:
            return self._is_modifying_relations[field]
        except KeyError:
            result = field in self._field_triggers and bool(
                field.relational or self.field_inverses[field] or any(
                    dep.relational or self.field_inverses[dep]
                    for dep in self.get_dependent_fields(field)
                )
            )
            self._is_modifying_relations[field] = result
            return result

    def post_init(self, func, *args, **kwargs):
        """ Register a function to call at the end of :meth:`~.init_models`. """
        self._post_init_queue.append(partial(func, *args, **kwargs))

    def post_constraint(self, func, *args, **kwargs):
        """ Call the given function, and delay it if it fails during an upgrade. """
        try:
            if (func, args, kwargs) not in self._constraint_queue:
                # Module A may try to apply a constraint and fail but another module B inheriting
                # from Module A may try to reapply the same constraint and succeed, however the
                # constraint would already be in the _constraint_queue and would be executed again
                # at the end of the registry cycle, this would fail (already-existing constraint)
                # and generate an error, therefore a constraint should only be applied if it's
                # not already marked as "to be applied".
                func(*args, **kwargs)
        except Exception as e:
            if self._is_install:
                _schema.error(*e.args)
            else:
                _schema.info(*e.args)
                self._constraint_queue.append((func, args, kwargs))

    def finalize_constraints(self) -> None:
        """ Call the delayed functions from above. """
        while self._constraint_queue:
            func, args, kwargs = self._constraint_queue.popleft()
            try:
                func(*args, **kwargs)
            except Exception as e:
                # warn only, this is not a deployment showstopper, and
                # can sometimes be a transient error
                _schema.warning(*e.args)

    def init_models(self, cr: Cursor, model_names: Iterable[str], context: dict[str, typing.Any], install: bool = True):
        """ Initialize a list of models (given by their name). Call methods
            ``_auto_init`` and ``init`` on each model to create or update the
            database tables supporting the models.

            The ``context`` may contain the following items:
             - ``module``: the name of the module being installed/updated, if any;
             - ``update_custom_fields``: whether custom fields should be updated.
        """
        if not model_names:
            return

        if 'module' in context:
            _logger.info('module %s: creating or updating database tables', context['module'])
        elif context.get('models_to_check', False):
            _logger.info("verifying fields for every extended model")

        env = odoo.api.Environment(cr, SUPERUSER_ID, context)
        models = [env[model_name] for model_name in model_names]

        try:
            self._post_init_queue: deque[Callable] = deque()
            # (table1, column1) -> (table2, column2, ondelete, model, module)
            self._foreign_keys: dict[tuple[str, str], tuple[str, str, str, BaseModel, str]] = {}
            self._is_install: bool = install

            for model in models:
                model._auto_init()
                model.init()

            env['ir.model']._reflect_models(model_names)
            env['ir.model.fields']._reflect_fields(model_names)
            env['ir.model.fields.selection']._reflect_selections(model_names)
            env['ir.model.constraint']._reflect_constraints(model_names)
            env['ir.model.inherit']._reflect_inherits(model_names)

            self._ordinary_tables = None

            while self._post_init_queue:
                func = self._post_init_queue.popleft()
                func()

            self.check_indexes(cr, model_names)
            self.check_foreign_keys(cr)

            env.flush_all()

            # make sure all tables are present
            self.check_tables_exist(cr)

        finally:
            del self._post_init_queue
            del self._foreign_keys
            del self._is_install

    def check_indexes(self, cr: Cursor, model_names: Iterable[str]) -> None:
        """ Create or drop column indexes for the given models. """

        expected = [
            (sql.make_index_name(Model._table, field.name), Model._table, field)
            for model_name in model_names
            for Model in [self.models[model_name]]
            if Model._auto and not Model._abstract
            for field in Model._fields.values()
            if field.column_type and field.store
        ]
        if not expected:
            return

        # retrieve existing indexes with their corresponding table
        cr.execute("SELECT indexname, tablename FROM pg_indexes WHERE indexname IN %s",
                   [tuple(row[0] for row in expected)])
        existing = dict(cr.fetchall())

        for indexname, tablename, field in expected:
            index = field.index
            assert index in ('btree', 'btree_not_null', 'trigram', True, False, None)
            if index and indexname not in existing and \
                    ((not field.translate and index != 'trigram') or (index == 'trigram' and self.has_trigram)):
                column_expression = f'"{field.name}"'
                if index == 'trigram':
                    if field.translate:
                        column_expression = f'''(jsonb_path_query_array({column_expression}, '$.*')::text)'''
                    # add `unaccent` to the trigram index only because the
                    # trigram indexes are mainly used for (=)ilike search and
                    # unaccent is added only in these cases when searching
                    if self.has_unaccent == FunctionStatus.INDEXABLE:
                        column_expression = self.unaccent(column_expression)
                    elif self.has_unaccent:
                        warnings.warn(
                            "PostgreSQL function 'unaccent' is present but not immutable, "
                            "therefore trigram indexes may not be effective.",
                            stacklevel=1,
                        )
                    expression = f'{column_expression} gin_trgm_ops'
                    method = 'gin'
                    where = ''
                elif index == 'btree_not_null' and field.company_dependent:
                    # company dependent condition will use extra
                    # `AND col IS NOT NULL` to use the index.
                    expression = f'({column_expression} IS NOT NULL)'
                    method = 'btree'
                    where = f'{column_expression} IS NOT NULL'
                else:  # index in ['btree', 'btree_not_null'， True]
                    expression = f'{column_expression}'
                    method = 'btree'
                    where = f'{column_expression} IS NOT NULL' if index == 'btree_not_null' else ''
                try:
                    with cr.savepoint(flush=False):
                        sql.create_index(cr, indexname, tablename, [expression], method, where)
                except psycopg2.OperationalError:
                    _schema.error("Unable to add index for %s", self)

            elif not index and tablename == existing.get(indexname):
                _schema.info("Keep unexpected index %s on table %s", indexname, tablename)

    def add_foreign_key(
        self, table1: str, column1: str, table2: str, column2: str,
        ondelete: str, model: BaseModel, module: str,
        force: bool = True,
    ) -> None:
        """ Specify an expected foreign key. """
        key = (table1, column1)
        val = (table2, column2, ondelete, model, module)
        if force:
            self._foreign_keys[key] = val
        else:
            self._foreign_keys.setdefault(key, val)

    def check_foreign_keys(self, cr: Cursor) -> None:
        """ Create or update the expected foreign keys. """
        if not self._foreign_keys:
            return

        # determine existing foreign keys on the tables
        query = """
            SELECT fk.conname, c1.relname, a1.attname, c2.relname, a2.attname, fk.confdeltype
            FROM pg_constraint AS fk
            JOIN pg_class AS c1 ON fk.conrelid = c1.oid
            JOIN pg_class AS c2 ON fk.confrelid = c2.oid
            JOIN pg_attribute AS a1 ON a1.attrelid = c1.oid AND fk.conkey[1] = a1.attnum
            JOIN pg_attribute AS a2 ON a2.attrelid = c2.oid AND fk.confkey[1] = a2.attnum
            WHERE fk.contype = 'f' AND c1.relname IN %s
        """
        cr.execute(query, [tuple({table for table, column in self._foreign_keys})])
        existing = {
            (table1, column1): (name, table2, column2, deltype)
            for name, table1, column1, table2, column2, deltype in cr.fetchall()
        }

        # create or update foreign keys
        for key, val in self._foreign_keys.items():
            table1, column1 = key
            table2, column2, ondelete, model, module = val
            deltype = sql._CONFDELTYPES[ondelete.upper()]
            spec = existing.get(key)
            if spec is None:
                sql.add_foreign_key(cr, table1, column1, table2, column2, ondelete)
                conname = sql.get_foreign_keys(cr, table1, column1, table2, column2, ondelete)[0]
                model.env['ir.model.constraint']._reflect_constraint(model, conname, 'f', None, module)
            elif (spec[1], spec[2], spec[3]) != (table2, column2, deltype):
                sql.drop_constraint(cr, table1, spec[0])
                sql.add_foreign_key(cr, table1, column1, table2, column2, ondelete)
                conname = sql.get_foreign_keys(cr, table1, column1, table2, column2, ondelete)[0]
                model.env['ir.model.constraint']._reflect_constraint(model, conname, 'f', None, module)

    def check_tables_exist(self, cr: Cursor) -> None:
        """
        Verify that all tables are present and try to initialize those that are missing.
        """
        env = odoo.api.Environment(cr, SUPERUSER_ID, {})
        table2model = {
            model._table: name
            for name, model in env.registry.items()
            if not model._abstract and not model._table_query
        }
        missing_tables = set(table2model).difference(sql.existing_tables(cr, table2model))

        if missing_tables:
            missing = {table2model[table] for table in missing_tables}
            _logger.info("Models have no table: %s.", ", ".join(missing))
            # recreate missing tables
            for name in missing:
                _logger.info("Recreate table of model %s.", name)
                env[name].init()
            env.flush_all()
            # check again, and log errors if tables are still missing
            missing_tables = set(table2model).difference(sql.existing_tables(cr, table2model))
            for table in missing_tables:
                _logger.error("Model %s has no table.", table2model[table])

    def clear_cache(self, *cache_names: str) -> None:
        """ Clear the caches associated to methods decorated with
        ``tools.ormcache``if cache is in `cache_name` subset. """
        cache_names = cache_names or ('default',)
        assert not any('.' in cache_name for cache_name in cache_names)
        for cache_name in cache_names:
            for cache in _CACHES_BY_KEY[cache_name]:
                self.__caches[cache].clear()
            self.cache_invalidated.add(cache_name)

        # log information about invalidation_cause
        if _logger.isEnabledFor(logging.DEBUG):
            # could be interresting to log in info but this will need to minimize invalidation first,
            # mainly in some setupclass and crons
            caller_info = format_frame(inspect.currentframe().f_back)  # type: ignore
            _logger.debug('Invalidating %s model caches from %s', ','.join(cache_names), caller_info)

    def clear_all_caches(self) -> None:
        """ Clear the caches associated to methods decorated with
        ``tools.ormcache``.
        """
        for cache_name, caches in _CACHES_BY_KEY.items():
            for cache in caches:
                self.__caches[cache].clear()
            self.cache_invalidated.add(cache_name)

        caller_info = format_frame(inspect.currentframe().f_back)  # type: ignore
        log = _logger.info if self.loaded else _logger.debug
        log('Invalidating all model caches from %s', caller_info)

    def is_an_ordinary_table(self, model: BaseModel) -> bool:
        """ Return whether the given model has an ordinary table. """
        if self._ordinary_tables is None:
            cr = model.env.cr
            query = """
                SELECT c.relname
                  FROM pg_class c
                  JOIN pg_namespace n ON (n.oid = c.relnamespace)
                 WHERE c.relname IN %s
                   AND c.relkind = 'r'
                   AND n.nspname = 'public'
            """
            tables = tuple(m._table for m in self.models.values())
            cr.execute(query, [tables])
            self._ordinary_tables = {row[0] for row in cr.fetchall()}

        return model._table in self._ordinary_tables

    @property
    def registry_invalidated(self) -> bool:
        """ Determine whether the current thread has modified the registry. """
        return getattr(self._invalidation_flags, 'registry', False)

    @registry_invalidated.setter
    def registry_invalidated(self, value: bool):
        self._invalidation_flags.registry = value

    @property
    def cache_invalidated(self) -> set[str]:
        """ Determine whether the current thread has modified the cache. """
        try:
            return self._invalidation_flags.cache
        except AttributeError:
            names = self._invalidation_flags.cache = set()
            return names

    def setup_signaling(self) -> None:
        """ Setup the inter-process signaling on this registry. """
        if self.in_test_mode():
            return

        with self.cursor() as cr:
            # The `orm_signaling_registry` sequence indicates when the registry
            # must be reloaded.
            # The `orm_signaling_...` sequences indicates when caches must
            # be invalidated (i.e. cleared).
            signaling_tables = tuple(f'orm_signaling_{cache_name}' for cache_name in ['registry', *_CACHES_BY_KEY])
            cr.execute("SELECT table_name FROM information_schema.tables WHERE table_name IN %s", [signaling_tables])

            existing_sig_tables = tuple(s[0] for s in cr.fetchall())  # could be a set but not efficient with such a little list
            # signaling was previously using sequence but this doesn't work with replication
            # https://www.postgresql.org/docs/current/logical-replication-restrictions.html
            # this is the reason why insert only tables are used.
            for table_name in signaling_tables:
                if table_name not in existing_sig_tables:
                    cr.execute(SQL(
                        "CREATE TABLE %s (id SERIAL PRIMARY KEY, date TIMESTAMP DEFAULT now())",
                        SQL.identifier(table_name),
                    ))
                    cr.execute(SQL("INSERT INTO %s DEFAULT VALUES", SQL.identifier(table_name)))

            db_registry_sequence, db_cache_sequences = self.get_sequences(cr)
            self.registry_sequence = db_registry_sequence
            self.cache_sequences.update(db_cache_sequences)

            _logger.debug("Multiprocess load registry signaling: [Registry: %s] %s",
                          self.registry_sequence, ' '.join('[Cache %s: %s]' % cs for cs in self.cache_sequences.items()))

    def get_sequences(self, cr: BaseCursor) -> tuple[int, dict[str, int]]:
        signaling_tables = tuple(f'orm_signaling_{cache_name}' for cache_name in ['registry', *_CACHES_BY_KEY])
        signaling_selects = SQL(', ').join([SQL('( SELECT max(id) FROM %s)', SQL.identifier(signaling_table)) for signaling_table in signaling_tables])
        cr.execute(SQL("SELECT %s", signaling_selects))
        row = cr.fetchone()
        assert row is not None, "No result when reading signaling sequences"
        registry_sequence, *cache_sequences_values = row
        cache_sequences = dict(zip(_CACHES_BY_KEY, cache_sequences_values))
        return registry_sequence, cache_sequences

    def check_signaling(self, cr: BaseCursor | None = None) -> Registry:
        """ Check whether the registry has changed, and performs all necessary
        operations to update the registry. Return an up-to-date registry.
        """
        if self.in_test_mode():
            return self

        with nullcontext(cr) if cr is not None else closing(self.cursor(readonly=True)) as cr:
            assert cr is not None
            db_registry_sequence, db_cache_sequences = self.get_sequences(cr)
            changes = ''
            # Check if the model registry must be reloaded
            if self.registry_sequence != db_registry_sequence:
                _logger.info("Reloading the model registry after database signaling.")
                self = Registry.new(self.db_name)
                self.registry_sequence = db_registry_sequence
                if _logger.isEnabledFor(logging.DEBUG):
                    changes += "[Registry - %s -> %s]" % (self.registry_sequence, db_registry_sequence)
            # Check if the model caches must be invalidated.
            else:
                invalidated = []
                for cache_name, cache_sequence in self.cache_sequences.items():
                    expected_sequence = db_cache_sequences[cache_name]
                    if cache_sequence != expected_sequence:
                        for cache in _CACHES_BY_KEY[cache_name]: # don't call clear_cache to avoid signal loop
                            if cache not in invalidated:
                                invalidated.append(cache)
                                self.__caches[cache].clear()
                        self.cache_sequences[cache_name] = expected_sequence
                        if _logger.isEnabledFor(logging.DEBUG):
                            changes += "[Cache %s - %s -> %s]" % (cache_name, cache_sequence, expected_sequence)
                if invalidated:
                    _logger.info("Invalidating caches after database signaling: %s", sorted(invalidated))
            if changes:
                _logger.debug("Multiprocess signaling check: %s", changes)
        return self

    def signal_changes(self) -> None:
        """ Notifies other processes if registry or cache has been invalidated. """
        if not self.ready:
            _logger.warning('Calling signal_changes when registry is not ready is not suported')
            return

        if self.registry_invalidated:
            _logger.info("Registry changed, signaling through the database")
            with self.cursor() as cr:
                cr.execute("INSERT INTO orm_signaling_registry DEFAULT VALUES")
                # If another process concurrently updates the registry,
                # self.registry_sequence will actually be out-of-date,
                # and the next call to check_signaling() will detect that and trigger a registry reload.
                # otherwise, self.registry_sequence should be equal to cr.fetchone()[0]
                self.registry_sequence += 1

        # no need to notify cache invalidation in case of registry invalidation,
        # because reloading the registry implies starting with an empty cache
        elif self.cache_invalidated:
            _logger.info("Caches invalidated, signaling through the database: %s", sorted(self.cache_invalidated))
            with self.cursor() as cr:
                for cache_name in self.cache_invalidated:
                    cr.execute(SQL("INSERT INTO %s DEFAULT VALUES", SQL.identifier(f'orm_signaling_{cache_name}')))
                    # If another process concurrently updates the cache,
                    # self.cache_sequences[cache_name] will actually be out-of-date,
                    # and the next call to check_signaling() will detect that and trigger cache invalidation.
                    # otherwise, self.cache_sequences[cache_name] should be equal to cr.fetchone()[0]
                    self.cache_sequences[cache_name] += 1

        self.registry_invalidated = False
        self.cache_invalidated.clear()

    def reset_changes(self) -> None:
        """ Reset the registry and cancel all invalidations. """
        if self.registry_invalidated:
            with closing(self.cursor()) as cr:
                self.setup_models(cr)
                self.registry_invalidated = False
        if self.cache_invalidated:
            for cache_name in self.cache_invalidated:
                for cache in _CACHES_BY_KEY[cache_name]:
                    self.__caches[cache].clear()
            self.cache_invalidated.clear()

    @contextmanager
    def manage_changes(self):
        """ Context manager to signal/discard registry and cache invalidations. """
        try:
            yield self
            self.signal_changes()
        except Exception:
            self.reset_changes()
            raise

    def in_test_mode(self) -> bool:
        """ Test whether the registry is in 'test' mode. """
        return self.test_cr is not None

    def enter_test_mode(self, cr: Cursor, test_readonly_enabled: bool = True) -> None:
        """ Enter the 'test' mode, where one cursor serves several requests. """
        assert self.test_cr is None
        self.test_cr = cr
        self.test_readonly_enabled = test_readonly_enabled
        self.test_lock = threading.RLock()
        assert Registry._saved_lock is None
        Registry._saved_lock = Registry._lock
        Registry._lock = DummyRLock()

    def leave_test_mode(self) -> None:
        """ Leave the test mode. """
        assert self.test_cr is not None
        self.test_cr = None
        del self.test_readonly_enabled
        del self.test_lock
        assert Registry._saved_lock is not None
        Registry._lock = Registry._saved_lock
        Registry._saved_lock = None

    def cursor(self, /, readonly: bool = False) -> BaseCursor:
        """ Return a new cursor for the database. The cursor itself may be used
            as a context manager to commit/rollback and close automatically.

            :param readonly: Attempt to acquire a cursor on a replica database.
                Acquire a read/write cursor on the primary database in case no
                replica exists or that no readonly cursor could be acquired.
        """
        if self.test_cr is not None:
            # in test mode we use a proxy object that uses 'self.test_cr' underneath
            if readonly and not self.test_readonly_enabled:
                _logger.info('Explicitly ignoring readonly flag when generating a cursor')
            assert self.test_lock is not None
            return TestCursor(self.test_cr, self.test_lock, readonly and self.test_readonly_enabled)

        if readonly and self._db_readonly is not None:
            try:
                return self._db_readonly.cursor()
            except psycopg2.OperationalError:
                # Setting _db_readonly to None will deactivate the readonly mode until
                # worker restart / recycling.
                self._db_readonly = None
                _logger.warning('Failed to open a readonly cursor, falling back to read-write cursor')
        return self._db.cursor()


class DummyRLock(object):
    """ Dummy reentrant lock, to be used while running rpc and js tests """
    def acquire(self):
        pass
    def release(self):
        pass
    def __enter__(self):
        self.acquire()
    def __exit__(self, type, value, traceback):
        self.release()


class TriggerTree(dict['Field', 'TriggerTree']):
    """ The triggers of a field F is a tree that contains the fields that
    depend on F, together with the fields to inverse to find out which records
    to recompute.

    For instance, assume that G depends on F, H depends on X.F, I depends on
    W.X.F, and J depends on Y.F. The triggers of F will be the tree:

                                 [G]
                               X/   \\Y
                             [H]     [J]
                           W/
                         [I]

    This tree provides perfect support for the trigger mechanism:
    when F is # modified on records,
     - mark G to recompute on records,
     - mark H to recompute on inverse(X, records),
     - mark I to recompute on inverse(W, inverse(X, records)),
     - mark J to recompute on inverse(Y, records).
    """
    __slots__ = ['root']
    root: Collection[Field]

    # pylint: disable=keyword-arg-before-vararg
    def __init__(self, root: Collection[Field] = (), *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = root

    def __bool__(self) -> bool:
        return bool(self.root or len(self))

    def __repr__(self) -> str:
        return f"TriggerTree(root={self.root!r}, {super().__repr__()})"

    def increase(self, key: Field) -> TriggerTree:
        try:
            return self[key]
        except KeyError:
            subtree = self[key] = TriggerTree()
            return subtree

    def depth_first(self) -> Iterator[TriggerTree]:
        yield self
        for subtree in self.values():
            yield from subtree.depth_first()

    @classmethod
    def merge(cls, trees: list[TriggerTree], select: Callable[[Field], bool] = bool) -> TriggerTree:
        """ Merge trigger trees into a single tree. The function ``select`` is
        called on every field to determine which fields should be kept in the
        tree nodes. This enables to discard some fields from the tree nodes.
        """
        root_fields: OrderedSet[Field] = OrderedSet()              # fields in the root node
        subtrees_to_merge = defaultdict(list)   # subtrees to merge grouped by key

        for tree in trees:
            root_fields.update(tree.root)
            for label, subtree in tree.items():
                subtrees_to_merge[label].append(subtree)

        # the root node contains the collected fields for which select is true
        result = cls([field for field in root_fields if select(field)])
        for label, subtrees in subtrees_to_merge.items():
            subtree = cls.merge(subtrees, select)
            if subtree:
                result[label] = subtree

        return result
