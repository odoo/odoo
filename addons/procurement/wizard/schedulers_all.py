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

import logging
import threading
from openerp import SUPERUSER_ID
from openerp import tools

from openerp.osv import osv
from openerp.api import Environment

_logger = logging.getLogger(__name__)

class procurement_compute_all(osv.osv_memory):
    _name = 'procurement.order.compute.all'
    _description = 'Compute all schedulers'

    def _procure_calculation_all(self, cr, uid, ids, context=None):
        """
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        """
        with Environment.manage():
            proc_obj = self.pool.get('procurement.order')
            #As this function is in a new thread, i need to open a new cursor, because the old one may be closed

            new_cr = self.pool.cursor()
            scheduler_cron_id = self.pool['ir.model.data'].get_object_reference(new_cr, SUPERUSER_ID, 'procurement', 'ir_cron_scheduler_action')[1]
            # Avoid to run the scheduler multiple times in the same time
            try:
                with tools.mute_logger('openerp.sql_db'):
                    new_cr.execute("SELECT id FROM ir_cron WHERE id = %s FOR UPDATE NOWAIT", (scheduler_cron_id,))
            except Exception:
                _logger.info('Attempt to run procurement scheduler aborted, as already running')
                new_cr.rollback()
                new_cr.close()
                return {}
            user = self.pool.get('res.users').browse(new_cr, uid, uid, context=context)
            comps = [x.id for x in user.company_ids]
            for comp in comps:
                proc_obj.run_scheduler(new_cr, uid, use_new_cursor=new_cr.dbname, company_id = comp, context=context)
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


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
