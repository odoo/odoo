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
from openerp.osv import fields, osv

class procurement_compute(osv.osv_memory):
    _name = 'procurement.order.compute'
    _description = 'Compute Procurement'

    def _procure_calculation_procure(self, cr, uid, ids, context=None):
        try:
            proc_obj = self.pool.get('procurement.order')
            proc_obj._procure_confirm(cr, uid, use_new_cursor=cr.dbname, context=context)
        finally:
            pass
        return {}

    def procure_calculation(self, cr, uid, ids, context=None):
        """
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: List of IDs selected
         @param context: A standard dictionary
        """
        threaded_calculation = threading.Thread(target=self._procure_calculation_procure, args=(cr, uid, ids, context))
        threaded_calculation.start()
        return {}

procurement_compute()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

