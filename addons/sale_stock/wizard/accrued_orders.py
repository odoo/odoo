from odoo import models, api


class AccountAccruedOrdersWizard(models.TransientModel):
    _inherit = 'account.accrued.orders.wizard'

    @api.model
    def _get_product_expense_and_stock_var_accounts(self, product):
        self.ensure_one()
        res = super()._get_product_expense_and_stock_var_accounts(product)
        if product.is_storable and product.valuation == 'real_time':
            product_accounts = product._get_product_accounts()
            expense_account = product_accounts.get('expense')
            stock_variation_account = product_accounts.get('stock_variation')
            if expense_account and stock_variation_account:
                return (expense_account, stock_variation_account)
        return res
