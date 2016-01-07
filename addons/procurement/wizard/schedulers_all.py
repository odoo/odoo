# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import threading

from odoo import api, models, tools
from odoo.api import Environment
from odoo.modules.registry import RegistryManager

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
            registry = RegistryManager.get(self.env.cr.dbname)
            cr = registry.cursor()
            env = Environment(cr, self.env.uid, self.env.context)
            scheduler_cron_id = env.ref('procurement.ir_cron_scheduler_action').id
            # Avoid to run the scheduler multiple times in the same time
            try:
                with tools.mute_logger('odoo.sql_db'):
                    cr.execute("SELECT id FROM ir_cron WHERE id = %s FOR UPDATE NOWAIT", (scheduler_cron_id,))
            except Exception:
                _logger.info('Attempt to run procurement scheduler aborted, as already running')
                cr.rollback()
                cr.close()
                return {}
            comps = [x.id for x in env.user.company_ids]
            for comp in comps:
                env['procurement.order'].run_scheduler(use_new_cursor=cr.dbname, company_id=comp)
            #close the new cursor
            cr.close()
            return {}

    @api.multi
    def procure_calculation(self):
        """
        @param self: The object pointer.
        """
        threaded_calculation = threading.Thread(target=self._procure_calculation_all)
        threaded_calculation.start()
        return {'type': 'ir.actions.act_window_close'}
