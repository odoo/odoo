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

import sql_db

pool_dic = {}

def get_db_and_pool(db_name, force_demo=False, status=None, update_module=False, pooljobs=True):
    """Return a database connection and an initialized osv_pool."""
    if not status:
        status={}

    db = sql_db.db_connect(db_name)

    if db_name in pool_dic:
        pool = pool_dic[db_name]
    else:
        import openerp.modules
        import openerp.osv.osv as osv_osv
        pool = osv_osv.osv_pool()

        # Initializing an osv_pool will call general code which will in turn
        # call get_db_and_pool (this function) to obtain the osv_pool begin
        # initialized. Make it available in the pool_dic then remove it if
        # an exception is raised.
        pool_dic[db_name] = pool
        try:
            openerp.modules.load_modules(db, force_demo, status, update_module)
        except Exception:
            del pool_dic[db_name]
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
    return db, pool


def delete_pool(db_name):
    """Delete an existing osv_pool."""
    if db_name in pool_dic:
        del pool_dic[db_name]

def restart_pool(db_name, force_demo=False, status=None, update_module=False):
    """Delete an existing osv_pool and return a database connection and a newly initialized osv_pool."""
    delete_pool(db_name)
    return get_db_and_pool(db_name, force_demo, status, update_module=update_module)


def get_db(db_name):
    """Return a database connection. The corresponding osv_pool is initialize."""
    return get_db_and_pool(db_name)[0]


def get_pool(db_name, force_demo=False, status=None, update_module=False):
    """Return an osv_pool."""
    return get_db_and_pool(db_name, force_demo, status, update_module)[1]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
