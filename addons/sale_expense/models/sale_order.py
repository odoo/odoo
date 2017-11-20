# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval



class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    ###########################################
    ### Analytic : auto recompute delivered quantity
    ###########################################

    def _expense_compute_delivered_quantity_domain(self):
        so_line_ids = self.filtered(lambda sol: sol.product_id.can_be_expensed).ids
        domain = []
        if so_line_ids:
            domain = [('so_line', 'in', so_line_ids)]
        return domain

    @api.multi
    def _analytic_compute_delivered_quantity_domain(self):
        domain = super(SaleOrderLine, self)._analytic_compute_delivered_quantity_domain()
        expense_domain = self._expense_compute_delivered_quantity_domain()
        return expression.OR([domain, expense_domain])
