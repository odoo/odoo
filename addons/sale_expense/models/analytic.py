# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    @api.multi
    def _sale_determine_order(self):
        mapping = super(AccountAnalyticLine, self)._sale_determine_order()
        for analytic_line in self.sudo().filtered(lambda aal: not aal.so_line and aal.product_id and aal.product_id.expense_policy != 'no'):
            if analytic_line.move_id.expense_id.sale_order_id:
                mapping[analytic_line.id] = analytic_line.move_id.expense_id.sale_order_id
        return mapping
