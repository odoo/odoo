# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.model
    def _run_scheduler_tasks(self, use_new_cursor=False, company_id=False):
        super(ProcurementGroup, self)._run_scheduler_tasks(use_new_cursor=use_new_cursor, company_id=company_id)
        self.env['stock.move']._run_fifo_vacuum()

