from odoo import models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def _get_or_create_account_from_so(self, order_id):
        sale_order = self.env['sale.order'].browse(order_id)

        if sale_order.project_id.account_id:
            return sale_order.project_id.account_id

        return super()._get_or_create_account_from_so(order_id)
