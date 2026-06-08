# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    billable_type = fields.Selection(selection_add=[('15_picking_entry_positive', 'Inventory Transfers (Revenues)'),
                                                    ('16_picking_entry_negative', 'Inventory Transfers (Costs)')])

    @api.depends('billable_type')
    def _compute_category_report(self):
        picking_revenues = self.filtered(lambda t: t.billable_type == '15_picking_entry_positive')
        picking_revenues.category_report = 'revenues'
        super(AccountAnalyticLine, self - picking_revenues)._compute_category_report()

    def _set_billable_cost(self):
        aals_delivery = self.filtered(lambda aal: aal.category == 'picking_entry')
        aals_delivery.billable_type = '16_picking_entry_negative'
        super(AccountAnalyticLine, self - aals_delivery)._set_billable_cost()

    def _get_invoice_type(self, invoice_type):
        if self.category == 'picking_entry':
            return '15_picking_entry_positive'
        return super()._get_invoice_type(invoice_type)
