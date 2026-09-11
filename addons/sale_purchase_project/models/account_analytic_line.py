from odoo import api, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def _get_billable_types(self):
        return super()._get_billable_types() + [(150, '20_purchase_order', self.env._('Purchase Orders'))]

    @api.depends('move_line_id.purchase_line_id')
    def _compute_project_billable_type(self):
        super()._compute_project_billable_type()

    def _set_billable_cost(self):
        aals_purchase = self.filtered(lambda aal: aal.category == 'vendor_bill' and aal.move_line_id.purchase_line_id)
        aals_purchase.billable_type = '20_purchase_order'
        super(AccountAnalyticLine, self - aals_purchase)._set_billable_cost()
