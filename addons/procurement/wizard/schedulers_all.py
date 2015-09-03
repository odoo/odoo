# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import threading
from openerp import api, models, tools
from openerp.api import Environment

_logger = logging.getLogger(__name__)


class ProcurementComputeAll(models.TransientModel):
    _name = 'procurement.order.compute.all'
    _description = 'Compute all schedulers'

    @api.multi
    def _procure_calculation_all(self):
        """
        @param self: The object pointer.
        """
        with Environment.manage():
            #As this function is in a new thread, i need to open a new cursor, because the old one may be closed

            new_cr = self.pool.cursor()
            scheduler_cron_id = self.pool['ir.model.data'].get_object_reference(new_cr, self.env.uid, 'procurement', 'ir_cron_scheduler_action')[1]
            # Avoid to run the scheduler multiple times in the same time
            try:
                with tools.mute_logger('openerp.sql_db'):
                    new_cr.execute("SELECT id FROM ir_cron WHERE id = %s FOR UPDATE NOWAIT", (scheduler_cron_id,))
            except Exception:
                _logger.info('Attempt to run procurement scheduler aborted, as already running')
                new_cr.rollback()
                new_cr.close()
                return {}
            # pool Use For new_cr is cursor
            user = self.pool['res.users'].browse(new_cr, self.env.uid, self.env.uid, context=self.env.context)
            comps = [x.id for x in user.company_ids]
            for comp in comps:
                self.pool['procurement.order'].run_scheduler(new_cr, self.env.uid, use_new_cursor=new_cr.dbname, company_id=comp)
            #close the new cursor
            new_cr.close()
            return {}

    @api.multi
    def procure_calculation(self):
        """
        @param self: The object pointer.
        """
        threaded_calculation = threading.Thread(target=self._procure_calculation_all)
        threaded_calculation.start()
        return {'type': 'ir.actions.act_window_close'}
