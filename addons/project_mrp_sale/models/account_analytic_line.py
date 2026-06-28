# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    billable_type = fields.Selection(selection_add=[('14_manufacturing_order', 'Manufacturing Orders')])

    def _set_billable_cost(self):
        aals_mrp = self.filtered(lambda aal: aal.category == 'manufacturing_order')
        aals_mrp.billable_type = '14_manufacturing_order'
        super(AccountAnalyticLine, self - aals_mrp)._set_billable_cost()
