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

""" Model registries manager.

    The manager is responsible for creation and deletion of bound model
    registries (essentially database connection/model registry pairs).

"""

import openerp.sql_db


class BoundRegistry(object):
    """ Model registry/database connection pair."""
    def __init__(self, db, registry):
        self.db = db
        self.registry = registry


class RegistryManager(object):


    # TODO maybe should receive the addons paths
    def __init__(self):
        # Mapping between db name and bound model registry.
        # Accessed through the methods below.
        self.bound_registries = {}


    def get(self, db_name, force_demo=False, status=None, update_module=False,
            pooljobs=True):
        """ Return a bound registry for a given database name."""

        if db_name in self.bound_registries:
            bound_registry = self.bound_registries[db_name]
        else:
            bound_registry = self.new(db_name, force_demo, status,
                update_module, pooljobs)
        return bound_registry


    def new(self, db_name, force_demo=False, status=None,
            update_module=False, pooljobs=True):
        """ Create and return a new bound registry for a given database name.

        The (possibly) previous bound registry for that database name is
        discarded.

        """

        import openerp.modules
        import openerp.osv.osv as osv_osv
        db = openerp.sql_db.db_connect(db_name)
        pool = osv_osv.osv_pool()

        # Initializing a registry will call general code which will in turn
        # call registries.get (this object) to obtain the registry being
        # initialized. Make it available in the bound_registries dictionary
        # then remove it if an exception is raised.
        self.delete(db_name)
        bound_registry = BoundRegistry(db, pool)
        self.bound_registries[db_name] = bound_registry
        try:
            # This should be a method on BoundRegistry
            openerp.modules.load_modules(db, force_demo, status, update_module)
        except Exception:
            del self.bound_registries[db_name]
            raise

        cr = db.cursor()
        try:
            pool.init_set(cr, False)
            pool.get('ir.actions.report.xml').register_all(cr)
            cr.commit()
        finally:
            cr.close()

        if pooljobs:
            pool.get('ir.cron').restart(db.dbname)

        return bound_registry


    def delete(self, db_name):
        if db_name in self.bound_registries:
            del self.bound_registries[db_name]


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
