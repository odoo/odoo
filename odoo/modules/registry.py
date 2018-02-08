# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Models registries.

"""
from collections import Mapping, defaultdict, deque
from contextlib import closing, contextmanager
from functools import partial
from operator import attrgetter
from weakref import WeakValueDictionary
import logging
import os
import threading

import odoo
from .. import SUPERUSER_ID
from odoo.tools import (assertion_report, config, existing_tables,
                        lazy_classproperty, lazy_property, table_exists,
                        topological_sort, OrderedSet)
from odoo.tools.lru import LRU

_logger = logging.getLogger(__name__)


class Registry(Mapping):
    """ Model registry for a particular database.

    The registry is essentially a mapping between model names and model classes.
    There is one registry instance per database.

    """
    _lock = threading.RLock()
    _saved_lock = None

    # a cache for model classes, indexed by their base classes
    model_cache = WeakValueDictionary()

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
        with cls._lock:
            with odoo.api.Environment.manage():
                registry = object.__new__(cls)
                registry.init(db_name)

                # Initializing a registry will call general code which will in
                # turn call Registry() to obtain the registry being initialized.
                # Make it available in the registries dictionary then remove it
                # if an exception is raised.
                cls.delete(db_name)
                cls.registries[db_name] = registry
                try:
                    registry.setup_signaling()
                    # This should be a method on Registry
                    try:
                        odoo.modules.load_modules(registry._db, force_demo, status, update_module)
                    except Exception:
                        odoo.modules.reset_modules_state(db_name)
                        raise
                except Exception:
                    _logger.exception('Failed to load registry')
                    del cls.registries[db_name]
                    raise

                # load_modules() above can replace the registry by calling
                # indirectly new() again (when modules have to be uninstalled).
                # Yeah, crazy.
                init_parent = registry._init_parent
                registry = cls.registries[db_name]
                registry._init_parent.update(init_parent)

                with closing(registry.cursor()) as cr:
                    registry.do_parent_store(cr)
                    cr.commit()

        registry.ready = True
        registry.registry_invalidated = bool(update_module)

        return registry

    def init(self, db_name):
        self.models = {}    # model name/model instance mapping
        self._sql_error = {}
        self._init = True
        self._init_parent = set()
        self._assertion_report = assertion_report.assertion_report()
        self._fields_by_model = None
        self._post_init_queue = deque()

        # modules fully loaded (maintained during init phase by `loading` module)
        self._init_modules = set()
        self.updated_modules = []       # installed/updated modules

        self.db_name = db_name
        self._db = odoo.sql_db.db_connect(db_name)

        # special cursor for test mode; None means "normal" mode
        self.test_cr = None

        # Indicates that the registry is
        self.loaded = False             # whether all modules are loaded
        self.ready = False              # whether everything is set up

        # Inter-process signaling (used only when odoo.multi_process is True):
        # The `base_registry_signaling` sequence indicates the whole registry
        # must be reloaded.
        # The `base_cache_signaling sequence` indicates all caches must be
        # invalidated (i.e. cleared).
        self.registry_sequence = None
        self.cache_sequence = None

        # Flags indicating invalidation of the registry or the cache.
        self.registry_invalidated = False
        self.cache_invalidated = False

        with closing(self.cursor()) as cr:
            has_unaccent = odoo.modules.db.has_unaccent(cr)
            if odoo.tools.config['unaccent'] and not has_unaccent:
                _logger.warning("The option --unaccent was given but no unaccent() function was found in database.")
            self.has_unaccent = odoo.tools.config['unaccent'] and has_unaccent

    @classmethod
    def delete(cls, db_name):
        """ Delete the registry linked to a given database. """
        with cls._lock:
            if db_name in cls.registries:
                registry = cls.registries.pop(db_name)
                registry.clear_caches()
                registry.registry_invalidated = True

    @classmethod
    def delete_all(cls):
        """ Delete all the registries. """
        with cls._lock:
            for db_name in list(cls.registries.keys()):
                cls.delete(db_name)

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

    @lazy_property
    def field_sequence(self):
        """ Return a function mapping a field to an integer. The value of a
            field is guaranteed to be strictly greater than the value of the
            field's dependencies.
        """
        # map fields on their dependents
        dependents = {
            field: set(dep for dep, _ in model._field_triggers[field] if dep != field)
            for model in self.values()
            for field in model._fields.values()
        }
        # sort them topologically, and associate a sequence number to each field
        mapping = {
            field: num
            for num, field in enumerate(reversed(topological_sort(dependents)))
        }
        return mapping.get

    def do_parent_store(self, cr):
        env = odoo.api.Environment(cr, SUPERUSER_ID, {})
        for model_name in self._init_parent:
            if model_name in env:
                env[model_name]._parent_store_compute()
        self._init = False

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
        modules, i.e. it instanciates all the classes of a the given module
        and registers them in the registry.

        """
        from .. import models

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
        lazy_property.reset_all(self)
        env = odoo.api.Environment(cr, SUPERUSER_ID, {})

        # add manual models
        if self._init_modules:
            env['ir.model']._add_manual_models()

        # prepare the setup on all models
        models = list(env.values())
        for model in models:
            model._prepare_setup()

        # do the actual setup from a clean state
        self._m2m = {}
        for model in models:
            model._setup_base()

        for model in models:
            model._setup_fields()

        for model in models:
            model._setup_complete()

        self.registry_invalidated = True

    def post_init(self, func, *args, **kwargs):
        """ Register a function to call at the end of :meth:`~.init_models`. """
        self._post_init_queue.append(partial(func, *args, **kwargs))

    def init_models(self, cr, model_names, context):
        """ Initialize a list of models (given by their name). Call methods
            ``_auto_init`` and ``init`` on each model to create or update the
            database tables supporting the models.

            The ``context`` may contain the following items:
             - ``module``: the name of the module being installed/updated, if any;
             - ``update_custom_fields``: whether custom fields should be updated.
        """
        if 'module' in context:
            _logger.info('module %s: creating or updating database tables', context['module'])

        env = odoo.api.Environment(cr, SUPERUSER_ID, context)
        models = [env[model_name] for model_name in model_names]

        for model in models:
            model._auto_init()
            model.init()

        while self._post_init_queue:
            func = self._post_init_queue.popleft()
            func()

        if models:
            models[0].recompute()

        # make sure all tables are present
        table2model = {model._table: name for name, model in env.items() if not model._abstract}
        missing_tables = set(table2model).difference(existing_tables(cr, table2model))
        if missing_tables:
            missing = {table2model[table] for table in missing_tables}
            _logger.warning("Models have no table: %s.", ", ".join(missing))
            # recreate missing tables following model dependencies
            deps = {name: model._depends for name, model in env.items()}
            for name in topological_sort(deps):
                if name in missing:
                    _logger.info("Recreate table of model %s.", name)
                    env[name].init()
            # check again, and log errors if tables are still missing
            missing_tables = set(table2model).difference(existing_tables(cr, table2model))
            for table in missing_tables:
                _logger.error("Model %s has no table.", table2model[table])

    @lazy_property
    def cache(self):
        """ A cache for model methods. """
        # this lazy_property is automatically reset by lazy_property.reset_all()
        return LRU(8192)

    def _clear_cache(self):
        """ Clear the cache and mark it as invalidated. """
        self.cache.clear()
        self.cache_invalidated = True

    def clear_caches(self):
        """ Clear the caches associated to methods decorated with
        ``tools.ormcache`` or ``tools.ormcache_multi`` for all the models.
        """
        for model in self.models.values():
            model.clear_caches()

    def setup_signaling(self):
        """ Setup the inter-process signaling on this registry. """
        if not odoo.multi_process:
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
        if not odoo.multi_process:
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
                self.cache_invalidated = False
            self.registry_sequence = r
            self.cache_sequence = c

        return self

    def signal_changes(self):
        """ Notifies other processes if registry or cache has been invalidated. """
        if odoo.multi_process and self.registry_invalidated:
            _logger.info("Registry changed, signaling through the database")
            with closing(self.cursor()) as cr:
                cr.execute("select nextval('base_registry_signaling')")
                self.registry_sequence = cr.fetchone()[0]

        # no need to notify cache invalidation in case of registry invalidation,
        # because reloading the registry implies starting with an empty cache
        elif odoo.multi_process and self.cache_invalidated:
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
            self.cache.clear()
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

    def enter_test_mode(self):
        """ Enter the 'test' mode, where one cursor serves several requests. """
        assert self.test_cr is None
        self.test_cr = self._db.test_cursor()
        assert Registry._saved_lock is None
        Registry._saved_lock = Registry._lock
        Registry._lock = DummyRLock()

    def leave_test_mode(self):
        """ Leave the test mode. """
        assert self.test_cr is not None
        self.clear_caches()
        self.test_cr.force_close()
        self.test_cr = None
        assert Registry._saved_lock is not None
        Registry._lock = Registry._saved_lock
        Registry._saved_lock = None

    def cursor(self):
        """ Return a new cursor for the database. The cursor itself may be used
            as a context manager to commit/rollback and close automatically.
        """
        cr = self.test_cr
        if cr is not None:
            # While in test mode, we use one special cursor across requests. The
            # test cursor uses a reentrant lock to serialize accesses. The lock
            # is granted here by cursor(), and automatically released by the
            # cursor itself in its method close().
            cr.acquire()
            return cr
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
