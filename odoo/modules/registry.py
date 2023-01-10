# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Models registries.

"""
from collections import defaultdict, deque
from collections.abc import Mapping
from contextlib import closing, contextmanager
from functools import partial
from operator import attrgetter
import logging
import os
import threading
import time

import psycopg2

import odoo
from .. import SUPERUSER_ID
from odoo.sql_db import TestCursor
from odoo.tools import (config, existing_tables, ignore,
                        lazy_classproperty, lazy_property, sql,
                        Collector, OrderedSet)
from odoo.tools.lru import LRU

_logger = logging.getLogger(__name__)
_schema = logging.getLogger('odoo.schema')


class Registry(Mapping):
    """ Model registry for a particular database.

    The registry is essentially a mapping between model names and model classes.
    There is one registry instance per database.

    """
    _lock = threading.RLock()
    _saved_lock = None

    @lazy_classproperty
    def registries(cls):
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

    def __new__(cls, db_name):
        """ Return the registry for the given database name."""
        with cls._lock:
            try:
                return cls.registries[db_name]
            except KeyError:
                return cls.new(db_name)
            finally:
                # set db tracker - cleaned up at the WSGI dispatching phase in
                # odoo.service.wsgi_server.application
                threading.current_thread().dbname = db_name

    @classmethod
    def new(cls, db_name, force_demo=False, status=None, update_module=False):
        """ Create and return a new registry for the given database name. """
        t0 = time.time()
        with cls._lock:
            registry = object.__new__(cls)
            registry.init(db_name)

            # Initializing a registry will call general code which will in
            # turn call Registry() to obtain the registry being initialized.
            # Make it available in the registries dictionary then remove it
            # if an exception is raised.
            cls.delete(db_name)
            cls.registries[db_name] = registry  # pylint: disable=unsupported-assignment-operation
            try:
                registry.setup_signaling()
                # This should be a method on Registry
                try:
                    odoo.modules.load_modules(registry, force_demo, status, update_module)
                except Exception:
                    odoo.modules.reset_modules_state(db_name)
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
            registry.new = registry.init = registry.registries = None

        _logger.info("Registry loaded in %.3fs", time.time() - t0)
        return registry

    def init(self, db_name):
        self.models = {}    # model name/model instance mapping
        self._sql_constraints = set()
        self._init = True
        self._assertion_report = odoo.tests.runner.OdooTestResult()
        self._fields_by_model = None
        self._ordinary_tables = None
        self._constraint_queue = deque()
        self.__cache = LRU(8192)

        # modules fully loaded (maintained during init phase by `loading` module)
        self._init_modules = set()
        self.updated_modules = []       # installed/updated modules
        self.loaded_xmlids = set()

        self.db_name = db_name
        self._db = odoo.sql_db.db_connect(db_name)

        # cursor for test mode; None means "normal" mode
        self.test_cr = None
        self.test_lock = None

        # Indicates that the registry is
        self.loaded = False             # whether all modules are loaded
        self.ready = False              # whether everything is set up

        # field dependencies
        self.field_depends = Collector()
        self.field_depends_context = Collector()
        self.field_inverses = Collector()

        # Inter-process signaling:
        # The `base_registry_signaling` sequence indicates the whole registry
        # must be reloaded.
        # The `base_cache_signaling sequence` indicates all caches must be
        # invalidated (i.e. cleared).
        self.registry_sequence = None
        self.cache_sequence = None

        # Flags indicating invalidation of the registry or the cache.
        self._invalidation_flags = threading.local()

        with closing(self.cursor()) as cr:
            self.has_unaccent = odoo.modules.db.has_unaccent(cr)
            self.has_trigram = odoo.modules.db.has_trigram(cr)

    @classmethod
    def delete(cls, db_name):
        """ Delete the registry linked to a given database. """
        with cls._lock:
            if db_name in cls.registries:
                del cls.registries[db_name]

    @classmethod
    def delete_all(cls):
        """ Delete all the registries. """
        with cls._lock:
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

    def __getitem__(self, model_name):
        """ Return the model with the given name or raise KeyError if it doesn't exist."""
        return self.models[model_name]

    def __call__(self, model_name):
        """ Same as ``self[model_name]``. """
        return self.models[model_name]

    def __setitem__(self, model_name, model):
        """ Add or replace a model in the registry."""
        self.models[model_name] = model

    def __delitem__(self, model_name):
        """ Remove a (custom) model from the registry. """
        del self.models[model_name]
        # the custom model can inherit from mixins ('mail.thread', ...)
        for Model in self.models.values():
            Model._inherit_children.discard(model_name)

    def descendants(self, model_names, *kinds):
        """ Return the models corresponding to ``model_names`` and all those
        that inherit/inherits from them.
        """
        assert all(kind in ('_inherit', '_inherits') for kind in kinds)
        funcs = [attrgetter(kind + '_children') for kind in kinds]

        models = OrderedSet()
        queue = deque(model_names)
        while queue:
            model = self[queue.popleft()]
            models.add(model._name)
            for func in funcs:
                queue.extend(func(model))
        return models

    def load(self, cr, module):
        """ Load a given module in the registry, and return the names of the
        modified models.

        At the Python level, the modules are already loaded, but not yet on a
        per-registry level. This method populates a registry with the given
        modules, i.e. it instantiates all the classes of a the given module
        and registers them in the registry.

        """
        from .. import models

        # clear cache to ensure consistency, but do not signal it
        self.__cache.clear()

        lazy_property.reset_all(self)

        # Instantiate registered classes (via the MetaModel automatic discovery
        # or via explicit constructor call), and add them to the pool.
        model_names = []
        for cls in models.MetaModel.module_to_models.get(module.name, []):
            # models register themselves in self.models
            model = cls._build_model(self, cr)
            model_names.append(model._name)

        return self.descendants(model_names, '_inherit', '_inherits')

    def setup_models(self, cr):
        """ Complete the setup of models.
            This must be called after loading modules and before using the ORM.
        """
        env = odoo.api.Environment(cr, SUPERUSER_ID, {})

        # Uninstall registry hooks. Because of the condition, this only happens
        # on a fully loaded registry, and not on a registry being loaded.
        if self.ready:
            for model in env.values():
                model._unregister_hook()

        # clear cache to ensure consistency, but do not signal it
        self.__cache.clear()

        lazy_property.reset_all(self)
        self.registry_invalidated = True

        if env.all.tocompute:
            _logger.error(
                "Remaining fields to compute before setting up registry: %s",
                env.all.tocompute, stack_info=True,
            )

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

        # do the actual setup
        for model in models:
            model._setup_base()

        self._m2m = defaultdict(list)
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

        # Reinstall registry hooks. Because of the condition, this only happens
        # on a fully loaded registry, and not on a registry being loaded.
        if self.ready:
            for model in env.values():
                model._register_hook()
            env['base'].flush()

    @lazy_property
    def field_computed(self):
        """ Return a dict mapping each field to the fields computed by the same method. """
        computed = {}
        for model_name, Model in self.models.items():
            groups = defaultdict(list)
            for field in Model._fields.values():
                if field.compute:
                    computed[field] = group = groups[field.compute]
                    group.append(field)
            for fields in groups.values():
                if len({field.compute_sudo for field in fields}) > 1:
                    _logger.warning("%s: inconsistent 'compute_sudo' for computed fields: %s",
                                    model_name, ", ".join(field.name for field in fields))
        return computed

    @lazy_property
    def field_triggers(self):
        # determine field dependencies
        dependencies = {}
        for Model in self.models.values():
            if Model._abstract:
                continue
            for field in Model._fields.values():
                # dependencies of custom fields may not exist; ignore that case
                exceptions = (Exception,) if field.base_field.manual else ()
                with ignore(*exceptions):
                    dependencies[field] = OrderedSet(field.resolve_depends(self))

        # determine transitive dependencies
        def transitive_dependencies(field, seen=[]):
            if field in seen:
                return
            for seq1 in dependencies.get(field, ()):
                yield seq1
                for seq2 in transitive_dependencies(seq1[-1], seen + [field]):
                    yield concat(seq1[:-1], seq2)

        def concat(seq1, seq2):
            if seq1 and seq2:
                f1, f2 = seq1[-1], seq2[0]
                if f1.type == 'one2many' and f2.type == 'many2one' and \
                        f1.model_name == f2.comodel_name and f1.inverse_name == f2.name:
                    return concat(seq1[:-1], seq2[1:])
            return seq1 + seq2

        # determine triggers based on transitive dependencies
        triggers = {}
        for field in dependencies:
            for path in transitive_dependencies(field):
                if path:
                    tree = triggers
                    for label in reversed(path):
                        tree = tree.setdefault(label, {})
                    tree.setdefault(None, OrderedSet()).add(field)

        return triggers

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

    def finalize_constraints(self):
        """ Call the delayed functions from above. """
        while self._constraint_queue:
            func, args, kwargs = self._constraint_queue.popleft()
            try:
                func(*args, **kwargs)
            except Exception as e:
                # warn only, this is not a deployment showstopper, and
                # can sometimes be a transient error
                _schema.warning(*e.args)

    def init_models(self, cr, model_names, context, install=True):
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
            self._post_init_queue = deque()
            self._foreign_keys = {}
            self._is_install = install

            for model in models:
                model._auto_init()
                model.init()

            env['ir.model']._reflect_models(model_names)
            env['ir.model.fields']._reflect_fields(model_names)
            env['ir.model.fields.selection']._reflect_selections(model_names)
            env['ir.model.constraint']._reflect_constraints(model_names)

            self._ordinary_tables = None

            while self._post_init_queue:
                func = self._post_init_queue.popleft()
                func()

            self.check_indexes(cr, model_names)
            self.check_foreign_keys(cr)

            env['base'].flush()

            # make sure all tables are present
            self.check_tables_exist(cr)

        finally:
            del self._post_init_queue
            del self._foreign_keys
            del self._is_install

    def check_indexes(self, cr, model_names):
        """ Create or drop column indexes for the given models. """
        expected = [
            ("%s_%s_index" % (Model._table, field.name), Model._table, field.name, field.index)
            for model_name in model_names
            for Model in [self.models[model_name]]
            if Model._auto and not Model._abstract
            for field in Model._fields.values()
            if field.column_type and field.store
        ]
        if not expected:
            return

        cr.execute("SELECT indexname FROM pg_indexes WHERE indexname IN %s",
                   [tuple(row[0] for row in expected)])
        existing = {row[0] for row in cr.fetchall()}

        for indexname, tablename, columnname, index in expected:
            if index and indexname not in existing:
                try:
                    with cr.savepoint(flush=False):
                        sql.create_index(cr, indexname, tablename, ['"%s"' % columnname])
                except psycopg2.OperationalError:
                    _schema.error("Unable to add index for %s", self)
            elif not index and indexname in existing:
                _schema.info("Keep unexpected index %s on table %s", indexname, tablename)

    def add_foreign_key(self, table1, column1, table2, column2, ondelete,
                        model, module, force=True):
        """ Specify an expected foreign key. """
        key = (table1, column1)
        val = (table2, column2, ondelete, model, module)
        if force:
            self._foreign_keys[key] = val
        else:
            self._foreign_keys.setdefault(key, val)

    def check_foreign_keys(self, cr):
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

    def check_tables_exist(self, cr):
        """
        Verify that all tables are present and try to initialize those that are missing.
        """
        env = odoo.api.Environment(cr, SUPERUSER_ID, {})
        table2model = {
            model._table: name
            for name, model in env.items()
            if not model._abstract and model.__class__._table_query is None
        }
        missing_tables = set(table2model).difference(existing_tables(cr, table2model))

        if missing_tables:
            missing = {table2model[table] for table in missing_tables}
            _logger.info("Models have no table: %s.", ", ".join(missing))
            # recreate missing tables
            for name in missing:
                _logger.info("Recreate table of model %s.", name)
                env[name].init()
            env['base'].flush()
            # check again, and log errors if tables are still missing
            missing_tables = set(table2model).difference(existing_tables(cr, table2model))
            for table in missing_tables:
                _logger.error("Model %s has no table.", table2model[table])

    def _clear_cache(self):
        """ Clear the cache and mark it as invalidated. """
        self.__cache.clear()
        self.cache_invalidated = True

    def clear_caches(self):
        """ Clear the caches associated to methods decorated with
        ``tools.ormcache`` or ``tools.ormcache_multi`` for all the models.
        """
        for model in self.models.values():
            model.clear_caches()

    def is_an_ordinary_table(self, model):
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
    def registry_invalidated(self):
        """ Determine whether the current thread has modified the registry. """
        return getattr(self._invalidation_flags, 'registry', False)

    @registry_invalidated.setter
    def registry_invalidated(self, value):
        self._invalidation_flags.registry = value

    @property
    def cache_invalidated(self):
        """ Determine whether the current thread has modified the cache. """
        return getattr(self._invalidation_flags, 'cache', False)

    @cache_invalidated.setter
    def cache_invalidated(self, value):
        self._invalidation_flags.cache = value

    def setup_signaling(self):
        """ Setup the inter-process signaling on this registry. """
        if self.in_test_mode():
            return

        with self.cursor() as cr:
            # The `base_registry_signaling` sequence indicates when the registry
            # must be reloaded.
            # The `base_cache_signaling` sequence indicates when all caches must
            # be invalidated (i.e. cleared).
            cr.execute("SELECT sequence_name FROM information_schema.sequences WHERE sequence_name='base_registry_signaling'")
            if not cr.fetchall():
                cr.execute("CREATE SEQUENCE base_registry_signaling INCREMENT BY 1 START WITH 1")
                cr.execute("SELECT nextval('base_registry_signaling')")
                cr.execute("CREATE SEQUENCE base_cache_signaling INCREMENT BY 1 START WITH 1")
                cr.execute("SELECT nextval('base_cache_signaling')")

            cr.execute(""" SELECT base_registry_signaling.last_value,
                                  base_cache_signaling.last_value
                           FROM base_registry_signaling, base_cache_signaling""")
            self.registry_sequence, self.cache_sequence = cr.fetchone()
            _logger.debug("Multiprocess load registry signaling: [Registry: %s] [Cache: %s]",
                          self.registry_sequence, self.cache_sequence)

    def check_signaling(self):
        """ Check whether the registry has changed, and performs all necessary
        operations to update the registry. Return an up-to-date registry.
        """
        if self.in_test_mode():
            return self

        with closing(self.cursor()) as cr:
            cr.execute(""" SELECT base_registry_signaling.last_value,
                                  base_cache_signaling.last_value
                           FROM base_registry_signaling, base_cache_signaling""")
            r, c = cr.fetchone()
            _logger.debug("Multiprocess signaling check: [Registry - %s -> %s] [Cache - %s -> %s]",
                          self.registry_sequence, r, self.cache_sequence, c)
            # Check if the model registry must be reloaded
            if self.registry_sequence != r:
                _logger.info("Reloading the model registry after database signaling.")
                self = Registry.new(self.db_name)
            # Check if the model caches must be invalidated.
            elif self.cache_sequence != c:
                _logger.info("Invalidating all model caches after database signaling.")
                self.clear_caches()

            # prevent re-signaling the clear_caches() above, or any residual one that
            # would be inherited from the master process (first request in pre-fork mode)
            self.cache_invalidated = False

            self.registry_sequence = r
            self.cache_sequence = c

        return self

    def signal_changes(self):
        """ Notifies other processes if registry or cache has been invalidated. """
        if self.registry_invalidated and not self.in_test_mode():
            _logger.info("Registry changed, signaling through the database")
            with closing(self.cursor()) as cr:
                cr.execute("select nextval('base_registry_signaling')")
                self.registry_sequence = cr.fetchone()[0]

        # no need to notify cache invalidation in case of registry invalidation,
        # because reloading the registry implies starting with an empty cache
        elif self.cache_invalidated and not self.in_test_mode():
            _logger.info("At least one model cache has been invalidated, signaling through the database.")
            with closing(self.cursor()) as cr:
                cr.execute("select nextval('base_cache_signaling')")
                self.cache_sequence = cr.fetchone()[0]

        self.registry_invalidated = False
        self.cache_invalidated = False

    def reset_changes(self):
        """ Reset the registry and cancel all invalidations. """
        if self.registry_invalidated:
            with closing(self.cursor()) as cr:
                self.setup_models(cr)
                self.registry_invalidated = False
        if self.cache_invalidated:
            self.__cache.clear()
            self.cache_invalidated = False

    @contextmanager
    def manage_changes(self):
        """ Context manager to signal/discard registry and cache invalidations. """
        try:
            yield self
            self.signal_changes()
        except Exception:
            self.reset_changes()
            raise

    def in_test_mode(self):
        """ Test whether the registry is in 'test' mode. """
        return self.test_cr is not None

    def enter_test_mode(self, cr):
        """ Enter the 'test' mode, where one cursor serves several requests. """
        assert self.test_cr is None
        self.test_cr = cr
        self.test_lock = threading.RLock()
        assert Registry._saved_lock is None
        Registry._saved_lock = Registry._lock
        Registry._lock = DummyRLock()

    def leave_test_mode(self):
        """ Leave the test mode. """
        assert self.test_cr is not None
        self.test_cr = None
        self.test_lock = None
        assert Registry._saved_lock is not None
        Registry._lock = Registry._saved_lock
        Registry._saved_lock = None

    def cursor(self):
        """ Return a new cursor for the database. The cursor itself may be used
            as a context manager to commit/rollback and close automatically.
        """
        if self.test_cr is not None:
            # in test mode we use a proxy object that uses 'self.test_cr' underneath
            return TestCursor(self.test_cr, self.test_lock)
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
