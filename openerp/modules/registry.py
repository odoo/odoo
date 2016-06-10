# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

""" Models registries.

"""
from collections import Mapping, defaultdict
import logging
import os
import threading

import openerp
from .. import SUPERUSER_ID
from openerp.tools import assertion_report, lazy_property, classproperty, config
from openerp.tools.lru import LRU

_logger = logging.getLogger(__name__)

class Registry(Mapping):
    """ Model registry for a particular database.

    The registry is essentially a mapping between model names and model
    instances. There is one registry instance per database.

    """

    def __init__(self, db_name):
        super(Registry, self).__init__()
        self.models = {}    # model name/model instance mapping
        self._sql_error = {}
        self._store_function = {}
        self._pure_function_fields = {}         # {model: [field, ...], ...}
        self._init = True
        self._init_parent = {}
        self._assertion_report = assertion_report.assertion_report()
        self._fields_by_model = None

        # modules fully loaded (maintained during init phase by `loading` module)
        self._init_modules = set()

        self.db_name = db_name
        self._db = openerp.sql_db.db_connect(db_name)

        # special cursor for test mode; None means "normal" mode
        self.test_cr = None

        # Indicates that the registry is 
        self.ready = False

        # Inter-process signaling (used only when openerp.multi_process is True):
        # The `base_registry_signaling` sequence indicates the whole registry
        # must be reloaded.
        # The `base_cache_signaling sequence` indicates all caches must be
        # invalidated (i.e. cleared).
        self.base_registry_signaling_sequence = None
        self.base_cache_signaling_sequence = None

        self.cache = LRU(8192)
        # Flag indicating if at least one model cache has been cleared.
        # Useful only in a multi-process context.
        self._any_cache_cleared = False

        cr = self.cursor()
        has_unaccent = openerp.modules.db.has_unaccent(cr)
        if openerp.tools.config['unaccent'] and not has_unaccent:
            _logger.warning("The option --unaccent was given but no unaccent() function was found in database.")
        self.has_unaccent = openerp.tools.config['unaccent'] and has_unaccent
        cr.close()

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

    @lazy_property
    def pure_function_fields(self):
        """ Return the list of pure function fields (field objects) """
        fields = []
        for mname, fnames in self._pure_function_fields.iteritems():
            model_fields = self[mname]._fields
            for fname in fnames:
                fields.append(model_fields[fname])
        return fields

    def clear_manual_fields(self):
        """ Invalidate the cache for manual fields. """
        self._fields_by_model = None

    def get_manual_fields(self, cr, model_name):
        """ Return the manual fields (as a dict) for the given model. """
        if self._fields_by_model is None:
            # Query manual fields for all models at once
            self._fields_by_model = dic = defaultdict(dict)
            cr.execute('SELECT * FROM ir_model_fields WHERE state=%s', ('manual',))
            for field in cr.dictfetchall():
                dic[field['model']][field['name']] = field
        return self._fields_by_model[model_name]

    def do_parent_store(self, cr):
        for o in self._init_parent:
            self.get(o)._parent_store_compute(cr)
        self._init = False

    def obj_list(self):
        """ Return the list of model names in this registry."""
        return self.keys()

    def add(self, model_name, model):
        """ Add or replace a model in the registry."""
        self.models[model_name] = model

    def load(self, cr, module):
        """ Load a given module in the registry.

        At the Python level, the modules are already loaded, but not yet on a
        per-registry level. This method populates a registry with the given
        modules, i.e. it instanciates all the classes of a the given module
        and registers them in the registry.

        """
        from .. import models

        models_to_load = [] # need to preserve loading order
        lazy_property.reset_all(self)

        # Instantiate registered classes (via the MetaModel automatic discovery
        # or via explicit constructor call), and add them to the pool.
        for cls in models.MetaModel.module_to_models.get(module.name, []):
            # models register themselves in self.models
            model = cls._build_model(self, cr)
            if model._name not in models_to_load:
                # avoid double-loading models whose declaration is split
                models_to_load.append(model._name)

        return [self.models[m] for m in models_to_load]

    def setup_models(self, cr, partial=False):
        """ Complete the setup of models.
            This must be called after loading modules and before using the ORM.

            :param partial: ``True`` if all models have not been loaded yet.
        """
        lazy_property.reset_all(self)

        # load custom models
        ir_model = self['ir.model']
        cr.execute('select model from ir_model where state=%s', ('manual',))
        for (model_name,) in cr.fetchall():
            ir_model.instanciate(cr, SUPERUSER_ID, model_name, {})

        # prepare the setup on all models
        for model in self.models.itervalues():
            model._prepare_setup(cr, SUPERUSER_ID)

        # do the actual setup from a clean state
        self._m2m = {}
        for model in self.models.itervalues():
            model._setup_base(cr, SUPERUSER_ID, partial)

        for model in self.models.itervalues():
            model._setup_fields(cr, SUPERUSER_ID)

        for model in self.models.itervalues():
            model._setup_complete(cr, SUPERUSER_ID)

    def clear_caches(self):
        """ Clear the caches
        This clears the caches associated to methods decorated with
        ``tools.ormcache`` or ``tools.ormcache_multi`` for all the models.
        """
        for model in self.models.itervalues():
            model.clear_caches()
        # Special case for ir_ui_menu which does not use openerp.tools.ormcache.
        ir_ui_menu = self.models.get('ir.ui.menu')
        if ir_ui_menu is not None:
            ir_ui_menu.clear_cache()


    # Useful only in a multi-process context.
    def reset_any_cache_cleared(self):
        self._any_cache_cleared = False

    # Useful only in a multi-process context.
    def any_cache_cleared(self):
        return self._any_cache_cleared

    @classmethod
    def setup_multi_process_signaling(cls, cr):
        if not openerp.multi_process:
            return None, None

        # Inter-process signaling:
        # The `base_registry_signaling` sequence indicates the whole registry
        # must be reloaded.
        # The `base_cache_signaling sequence` indicates all caches must be
        # invalidated (i.e. cleared).
        cr.execute("""SELECT sequence_name FROM information_schema.sequences WHERE sequence_name='base_registry_signaling'""")
        if not cr.fetchall():
            cr.execute("""CREATE SEQUENCE base_registry_signaling INCREMENT BY 1 START WITH 1""")
            cr.execute("""SELECT nextval('base_registry_signaling')""")
            cr.execute("""CREATE SEQUENCE base_cache_signaling INCREMENT BY 1 START WITH 1""")
            cr.execute("""SELECT nextval('base_cache_signaling')""")
        
        cr.execute("""
                    SELECT base_registry_signaling.last_value,
                           base_cache_signaling.last_value
                    FROM base_registry_signaling, base_cache_signaling""")
        r, c = cr.fetchone()
        _logger.debug("Multiprocess load registry signaling: [Registry: # %s] "\
                    "[Cache: # %s]",
                    r, c)
        return r, c

    def enter_test_mode(self):
        """ Enter the 'test' mode, where one cursor serves several requests. """
        assert self.test_cr is None
        self.test_cr = self._db.test_cursor()
        RegistryManager.enter_test_mode()

    def leave_test_mode(self):
        """ Leave the test mode. """
        assert self.test_cr is not None
        self.test_cr.force_close()
        self.test_cr = None
        RegistryManager.leave_test_mode()

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

class RegistryManager(object):
    """ Model registries manager.

        The manager is responsible for creation and deletion of model
        registries (essentially database connection/model registry pairs).

    """
    _registries = None
    _lock = threading.RLock()
    _saved_lock = None

    @classproperty
    def registries(cls):
        if cls._registries is None:
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

            cls._registries = LRU(size)
        return cls._registries

    @classmethod
    def lock(cls):
        """ Return the current registry lock. """
        return cls._lock

    @classmethod
    def enter_test_mode(cls):
        """ Enter the 'test' mode, where the registry is no longer locked. """
        assert cls._saved_lock is None
        cls._lock, cls._saved_lock = DummyRLock(), cls._lock

    @classmethod
    def leave_test_mode(cls):
        """ Leave the 'test' mode. """
        assert cls._saved_lock is not None
        cls._lock, cls._saved_lock = cls._saved_lock, None

    @classmethod
    def get(cls, db_name, force_demo=False, status=None, update_module=False):
        """ Return a registry for a given database name."""
        with cls.lock():
            try:
                return cls.registries[db_name]
            except KeyError:
                return cls.new(db_name, force_demo, status,
                               update_module)
            finally:
                # set db tracker - cleaned up at the WSGI
                # dispatching phase in openerp.service.wsgi_server.application
                threading.current_thread().dbname = db_name

    @classmethod
    def new(cls, db_name, force_demo=False, status=None,
            update_module=False):
        """ Create and return a new registry for a given database name.

        The (possibly) previous registry for that database name is discarded.

        """
        import openerp.modules
        with cls.lock():
            with openerp.api.Environment.manage():
                registry = Registry(db_name)

                # Initializing a registry will call general code which will in
                # turn call registries.get (this object) to obtain the registry
                # being initialized. Make it available in the registries
                # dictionary then remove it if an exception is raised.
                cls.delete(db_name)
                cls.registries[db_name] = registry
                try:
                    with registry.cursor() as cr:
                        seq_registry, seq_cache = Registry.setup_multi_process_signaling(cr)
                        registry.base_registry_signaling_sequence = seq_registry
                        registry.base_cache_signaling_sequence = seq_cache
                    # This should be a method on Registry
                    openerp.modules.load_modules(registry._db, force_demo, status, update_module)
                except Exception:
                    del cls.registries[db_name]
                    raise

                # load_modules() above can replace the registry by calling
                # indirectly new() again (when modules have to be uninstalled).
                # Yeah, crazy.
                registry = cls.registries[db_name]

                cr = registry.cursor()
                try:
                    registry.do_parent_store(cr)
                    cr.commit()
                finally:
                    cr.close()

        registry.ready = True

        if update_module:
            # only in case of update, otherwise we'll have an infinite reload loop!
            cls.signal_registry_change(db_name)
        return registry

    @classmethod
    def delete(cls, db_name):
        """Delete the registry linked to a given database.  """
        with cls.lock():
            if db_name in cls.registries:
                cls.registries[db_name].clear_caches()
                del cls.registries[db_name]

    @classmethod
    def delete_all(cls):
        """Delete all the registries. """
        with cls.lock():
            for db_name in cls.registries.keys():
                cls.delete(db_name)

    @classmethod
    def clear_caches(cls, db_name):
        """Clear caches

        This clears the caches associated to methods decorated with
        ``tools.ormcache`` or ``tools.ormcache_multi`` for all the models
        of the given database name.

        This method is given to spare you a ``RegistryManager.get(db_name)``
        that would loads the given database if it was not already loaded.
        """
        with cls.lock():
            if db_name in cls.registries:
                cls.registries[db_name].clear_caches()

    @classmethod
    def check_registry_signaling(cls, db_name):
        """
        Check if the modules have changed and performs all necessary operations to update
        the registry of the corresponding database.


        :returns: True if changes has been detected in the database and False otherwise.
        """
        changed = False
        if openerp.multi_process and db_name in cls.registries:
            registry = cls.get(db_name)
            cr = registry.cursor()
            try:
                cr.execute("""
                    SELECT base_registry_signaling.last_value,
                           base_cache_signaling.last_value
                    FROM base_registry_signaling, base_cache_signaling""")
                r, c = cr.fetchone()
                _logger.debug("Multiprocess signaling check: [Registry - old# %s new# %s] "\
                    "[Cache - old# %s new# %s]",
                    registry.base_registry_signaling_sequence, r,
                    registry.base_cache_signaling_sequence, c)
                # Check if the model registry must be reloaded (e.g. after the
                # database has been updated by another process).
                if registry.base_registry_signaling_sequence is not None and registry.base_registry_signaling_sequence != r:
                    changed = True
                    _logger.info("Reloading the model registry after database signaling.")
                    registry = cls.new(db_name)
                # Check if the model caches must be invalidated (e.g. after a write
                # occured on another process). Don't clear right after a registry
                # has been reload.
                elif registry.base_cache_signaling_sequence is not None and registry.base_cache_signaling_sequence != c:
                    changed = True
                    _logger.info("Invalidating all model caches after database signaling.")
                    registry.clear_caches()
                    registry.reset_any_cache_cleared()
                registry.base_registry_signaling_sequence = r
                registry.base_cache_signaling_sequence = c
            finally:
                cr.close()
        return changed

    @classmethod
    def signal_caches_change(cls, db_name):
        if openerp.multi_process and db_name in cls.registries:
            # Check the registries if any cache has been cleared and signal it
            # through the database to other processes.
            registry = cls.get(db_name)
            if registry.any_cache_cleared():
                _logger.info("At least one model cache has been cleared, signaling through the database.")
                cr = registry.cursor()
                r = 1
                try:
                    cr.execute("select nextval('base_cache_signaling')")
                    r = cr.fetchone()[0]
                finally:
                    cr.close()
                registry.base_cache_signaling_sequence = r
                registry.reset_any_cache_cleared()

    @classmethod
    def signal_registry_change(cls, db_name):
        if openerp.multi_process and db_name in cls.registries:
            _logger.info("Registry changed, signaling through the database")
            registry = cls.get(db_name)
            cr = registry.cursor()
            r = 1
            try:
                cr.execute("select nextval('base_registry_signaling')")
                r = cr.fetchone()[0]
            finally:
                cr.close()
            registry.base_registry_signaling_sequence = r

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
