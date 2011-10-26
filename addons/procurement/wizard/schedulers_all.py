# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import threading
import pooler

from osv import osv, fields

class procurement_compute_all(osv.osv_memory):
    _name = 'procurement.order.compute.all'
    _description = 'Compute all schedulers'

    _columns = {
        'automatic': fields.boolean('Automatic orderpoint',help='Triggers an automatic procurement for all products that have a virtual stock under 0. You should probably not use this option, we suggest using a MTO configuration on products.'),
    }

    _defaults = {
         'automatic': lambda *a: False,
    }

    def _procure_calculation_all(self, cr, uid, ids, context=None):
        """
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        """
        proc_obj = self.pool.get('procurement.order')
        #As this function is in a new thread, i need to open a new cursor, because the old one may be closed
        new_cr = pooler.get_db(cr.dbname).cursor()
        for proc in self.browse(new_cr, uid, ids, context=context):
            proc_obj.run_scheduler(new_cr, uid, automatic=proc.automatic, use_new_cursor=new_cr.dbname,\
                    context=context)
        #close the new cursor
        new_cr.close()
        return {}

    def procure_calculation(self, cr, uid, ids, context=None):
        """
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        """
        threaded_calculation = threading.Thread(target=self._procure_calculation_all, args=(cr, uid, ids, context))
        threaded_calculation.start()
        return {'type': 'ir.actions.act_window_close'}

procurement_compute_all()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
