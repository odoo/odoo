# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

class ProcurementGroup(models.Model):
    _inherit = "procurement.group"

    pos_order_id = fields.Many2one("pos.order", "POS Order")

    @api.model
    def _run_scheduler_tasks(self, use_new_cursor=False, company_id=False):
        super(ProcurementGroup, self)._run_scheduler_tasks(
            use_new_cursor=use_new_cursor, company_id=company_id
        )
        self.env["pos.session"]._alert_old_session()
        if use_new_cursor:
            self.env.cr.commit()
