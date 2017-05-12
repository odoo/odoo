# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProcurementOrder(models.Model):
    _inherit = "procurement.order"

    def _run_move_create(self):
        vals = super(ProcurementOrder, self)._run_move_create()
        if self.sale_line_id:
            vals.update({'sequence': self.sale_line_id.sequence})
        return vals
