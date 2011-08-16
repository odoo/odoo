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

import openerp.sql_db
import openerp.osv.orm


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

    def instanciate(self, module, cr):
        """ Instanciate all the classes of a given module for a particular db."""

        res = []

        # Instanciate classes registered through their constructor and
        # add them to the pool.
        for klass in openerp.osv.orm.module_class_list.get(module, []):
            res.append(klass.create_instance(self, cr))

        # Instanciate classes automatically discovered.
        for cls in openerp.osv.orm.MetaModel.module_to_models.get(module, []):
            if cls not in openerp.osv.orm.module_class_list.get(module, []):
                res.append(cls.create_instance(self, cr))

        return res


class RegistryManager(object):
    """ Model registries manager.

        The manager is responsible for creation and deletion of model
        registries (essentially database connection/model registry pairs).

    """

    # Mapping between db name and model registry.
    # Accessed through the methods below.
    registries = {}


    @classmethod
    def get(cls, db_name, force_demo=False, status=None, update_module=False,
            pooljobs=True):
        """ Return a registry for a given database name."""

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
            registry.get('ir.cron').restart(registry.db.dbname)

        return registry


    @classmethod
    def delete(cls, db_name):
        """ Delete the registry linked to a given database. """
        if db_name in cls.registries:
            del cls.registries[db_name]


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
