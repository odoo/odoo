from odoo import models, api


class AccountAccruedOrdersWizard(models.TransientModel):
    _inherit = 'account.accrued.orders.wizard'

    @api.model
    def _get_price_diff_account(self, product):
        if product.cost_method == 'standard':
            return product.categ_id.property_price_difference_account_id
        return super()._get_price_diff_account(product)
