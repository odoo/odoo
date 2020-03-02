# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    @api.onchange('product_id', 'date')
    def _onchange_product_id(self):
        res = super(HrExpense, self)._onchange_product_id()
        rec = self.env['account.analytic.default'].account_get(self.product_id.id, company_id=self.company_id.id, date=self.date)
        self.analytic_account_id = self.analytic_account_id or rec.analytic_id.id
        self.analytic_tag_ids = self.analytic_tag_ids or rec.analytic_tag_ids.ids
        return res
