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
import threading

import logging

import openerp.sql_db
import openerp.osv.orm
import openerp.cron
import openerp.tools
import openerp.modules.db
import openerp.tools.config

class Registry(object):
    """ Model registry for a particular database.

    The registry is essentially a mapping between model names and model
    instances. There is one registry instance per database.

    """

    def __init__(self, db_name):
        self.models = {} # model name/model instance mapping
        self._sql_error = {}
        self._store_function = {}
        self._init = True
        self._init_parent = {}
        self.db_name = db_name
        self.db = openerp.sql_db.db_connect(db_name)

        cr = self.db.cursor()
        has_unaccent = openerp.modules.db.has_unaccent(cr)
        if openerp.tools.config['unaccent'] and not has_unaccent:
            logger = logging.getLogger('unaccent')
            logger.warning("The option --unaccent was given but no unaccent() function was found in database.")
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

        res = []

        # Instantiate registered classes (via the MetaModel automatic discovery
        # or via explicit constructor call), and add them to the pool.
        for cls in openerp.osv.orm.MetaModel.module_to_models.get(module.name, []):
            res.append(cls.create_instance(self, cr))

        return res

    def schedule_cron_jobs(self):
        """ Make the cron thread care about this registry/database jobs.
        This will initiate the cron thread to check for any pending jobs for
        this registry/database as soon as possible. Then it will continuously
        monitor the ir.cron model for future jobs. See openerp.cron for
        details.
        """
        openerp.cron.schedule_wakeup(openerp.cron.WAKE_UP_NOW, self.db.dbname)

    def clear_caches(self):
        """ Clear the caches
        This clears the caches associated to methods decorated with
        ``tools.ormcache`` or ``tools.ormcache_multi`` for all the models.
        """
        for model in self.models.itervalues():
            model.clear_caches()

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
    def get(cls, db_name, force_demo=False, status=None, update_module=False,
            pooljobs=True):
        """ Return a registry for a given database name."""
        with cls.registries_lock:
            if db_name in cls.registries:
                registry = cls.registries[db_name]
            else:
                registry = cls.new(db_name, force_demo, status,
                                   update_module, pooljobs)
            return registry

    @classmethod
    def new(cls, db_name, force_demo=False, status=None,
            update_module=False, pooljobs=True):
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

            cr = registry.db.cursor()
            try:
                registry.do_parent_store(cr)
                registry.get('ir.actions.report.xml').register_all(cr)
                cr.commit()
            finally:
                cr.close()

            if pooljobs:
                registry.schedule_cron_jobs()

            return registry

    @classmethod
    def delete(cls, db_name):
        """Delete the registry linked to a given database.

        This also cleans the associated caches. For good measure this also
        cancels the associated cron job. But please note that the cron job can
        be running and take some time before ending, and that you should not
        remove a registry if it can still be used by some thread. So it might
        be necessary to call yourself openerp.cron.Agent.cancel(db_name) and
        and join (i.e. wait for) the thread.
        """
        with cls.registries_lock:
            if db_name in cls.registries:
                cls.registries[db_name].clear_caches()
                del cls.registries[db_name]
                openerp.cron.cancel(db_name)


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


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: