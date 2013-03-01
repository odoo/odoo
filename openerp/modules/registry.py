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
from contextlib import contextmanager
import logging
import threading

import openerp.sql_db
import openerp.osv.orm
import openerp.tools
import openerp.modules.db
import openerp.tools.config
from openerp.tools import assertion_report

_logger = logging.getLogger(__name__)

class Registry(object):
    """ Model registry for a particular database.

    The registry is essentially a mapping between model names and model
    instances. There is one registry instance per database.

    """

    def __init__(self, db_name):
        self.models = {}    # model name/model instance mapping
        self._sql_error = {}
        self._store_function = {}
        self._init = True
        self._init_parent = {}
        self._assertion_report = assertion_report.assertion_report()
        self.fields_by_model = None

        # modules fully loaded (maintained during init phase by `loading` module)
        self._init_modules = set()

        self.db_name = db_name
        self.db = openerp.sql_db.db_connect(db_name)

        # Indicates that the registry is 
        self.ready = False

        # Inter-process signaling (used only when openerp.multi_process is True):
        # The `base_registry_signaling` sequence indicates the whole registry
        # must be reloaded.
        # The `base_cache_signaling sequence` indicates all caches must be
        # invalidated (i.e. cleared).
        self.base_registry_signaling_sequence = 1
        self.base_cache_signaling_sequence = 1

        # Flag indicating if at least one model cache has been cleared.
        # Useful only in a multi-process context.
        self._any_cache_cleared = False

        cr = self.db.cursor()
        has_unaccent = openerp.modules.db.has_unaccent(cr)
        if openerp.tools.config['unaccent'] and not has_unaccent:
            _logger.warning("The option --unaccent was given but no unaccent() function was found in database.")
        self.has_unaccent = openerp.tools.config['unaccent'] and has_unaccent
        cr.close()

    def do_parent_store(self, cr):
        for o in self._init_parent:
            self.get(o)._parent_store_compute(cr)
        self._init = False

    def obj_list(self):
        """ Return the list of model names in this registry."""
        return self.models.keys()

    def add(self, model_name, model):
        """ Add or replace a model in the registry."""
        self.models[model_name] = model

    def get(self, model_name):
        """ Return a model for a given name or None if it doesn't exist."""
        return self.models.get(model_name)

    def __getitem__(self, model_name):
        """ Return a model for a given name or raise KeyError if it doesn't exist."""
        return self.models[model_name]

    def load(self, cr, module):
        """ Load a given module in the registry.

        At the Python level, the modules are already loaded, but not yet on a
        per-registry level. This method populates a registry with the given
        modules, i.e. it instanciates all the classes of a the given module
        and registers them in the registry.

        """
        models_to_load = [] # need to preserve loading order
        # Instantiate registered classes (via the MetaModel automatic discovery
        # or via explicit constructor call), and add them to the pool.
        for cls in openerp.osv.orm.MetaModel.module_to_models.get(module.name, []):
            # models register themselves in self.models
            model = cls.create_instance(self, cr)
            if model._name not in models_to_load:
                # avoid double-loading models whose declaration is split
                models_to_load.append(model._name)
        return [self.models[m] for m in models_to_load]

    def clear_caches(self):
        """ Clear the caches
        This clears the caches associated to methods decorated with
        ``tools.ormcache`` or ``tools.ormcache_multi`` for all the models.
        """
        for model in self.models.itervalues():
            model.clear_caches()
        # Special case for ir_ui_menu which does not use openerp.tools.ormcache.
        ir_ui_menu = self.models.get('ir.ui.menu')
        if ir_ui_menu:
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
            return

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

    @contextmanager
    def cursor(self, auto_commit=True):
        cr = self.db.cursor()
        try:
            yield cr
            if auto_commit:
                cr.commit()
        finally:
            cr.close()


class RegistryManager(object):
    """ Model registries manager.

        The manager is responsible for creation and deletion of model
        registries (essentially database connection/model registry pairs).

    """
    # Mapping between db name and model registry.
    # Accessed through the methods below.
    registries = {}
    registries_lock = threading.RLock()

    @classmethod
    def get(cls, db_name, force_demo=False, status=None, update_module=False):
        """ Return a registry for a given database name."""
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
        with cls.registries_lock:
            registry = Registry(db_name)

            # Initializing a registry will call general code which will in turn
            # call registries.get (this object) to obtain the registry being
            # initialized. Make it available in the registries dictionary then
            # remove it if an exception is raised.
            cls.delete(db_name)
            cls.registries[db_name] = registry
            try:
                # This should be a method on Registry
                openerp.modules.load_modules(registry.db, force_demo, status, update_module)
            except Exception:
                del cls.registries[db_name]
                raise

            # load_modules() above can replace the registry by calling
            # indirectly new() again (when modules have to be uninstalled).
            # Yeah, crazy.
            registry = cls.registries[db_name]

            cr = registry.db.cursor()
            try:
                Registry.setup_multi_process_signaling(cr)
                registry.do_parent_store(cr)
                registry.get('ir.actions.report.xml').register_all(cr)
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
        with cls.registries_lock:
            if db_name in cls.registries:
                cls.registries[db_name].clear_caches()
                del cls.registries[db_name]

    @classmethod
    def delete_all(cls):
        """Delete all the registries. """
        with cls.registries_lock:
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
        with cls.registries_lock:
            if db_name in cls.registries:
                cls.registries[db_name].clear_caches()

    @classmethod
    def check_registry_signaling(cls, db_name):
        if openerp.multi_process and db_name in cls.registries:
            registry = cls.get(db_name)
            cr = registry.db.cursor()
            try:
                cr.execute("""
                    SELECT base_registry_signaling.last_value,
                           base_cache_signaling.last_value
                    FROM base_registry_signaling, base_cache_signaling""")
                r, c = cr.fetchone()
                # Check if the model registry must be reloaded (e.g. after the
                # database has been updated by another process).
                if registry.base_registry_signaling_sequence != r:
                    _logger.info("Reloading the model registry after database signaling.")
                    registry = cls.new(db_name)
                    registry.base_registry_signaling_sequence = r
                # Check if the model caches must be invalidated (e.g. after a write
                # occured on another process). Don't clear right after a registry
                # has been reload.
                elif registry.base_cache_signaling_sequence != c:
                    _logger.info("Invalidating all model caches after database signaling.")
                    registry.base_cache_signaling_sequence = c
                    registry.clear_caches()
                    registry.reset_any_cache_cleared()
                    # One possible reason caches have been invalidated is the
                    # use of decimal_precision.write(), in which case we need
                    # to refresh fields.float columns.
                    for model in registry.models.values():
                        for column in model._columns.values():
                            if hasattr(column, 'digits_change'):
                                column.digits_change(cr)
            finally:
                cr.close()

    @classmethod
    def signal_caches_change(cls, db_name):
        if openerp.multi_process and db_name in cls.registries:
            # Check the registries if any cache has been cleared and signal it
            # through the database to other processes.
            registry = cls.get(db_name)
            if registry.any_cache_cleared():
                _logger.info("At least one model cache has been cleared, signaling through the database.")
                cr = registry.db.cursor()
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
            registry = cls.get(db_name)
            cr = registry.db.cursor()
            r = 1
            try:
                cr.execute("select nextval('base_registry_signaling')")
                r = cr.fetchone()[0]
            finally:
                cr.close()
            registry.base_registry_signaling_sequence = r

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
