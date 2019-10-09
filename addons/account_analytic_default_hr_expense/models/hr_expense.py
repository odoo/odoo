# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    @api.onchange('product_id', 'date', 'account_id')
    def _onchange_product_id(self):
        res = super(HrExpense, self)._onchange_product_id()
        rec = self.env['account.analytic.default'].sudo().account_get(product_id=self.product_id.id, account_id=self.account_id.id, company_id=self.company_id.id, date=self.date)
        self.analytic_account_id = rec.analytic_id.id
        self.analytic_tag_ids = rec.analytic_tag_ids.ids
        return res
