from odoo import models
from odoo.addons import account


class AccountChartTemplate(account.AccountChartTemplate):

    def _get_property_accounts(self, additional_properties):
        property_accounts = super()._get_property_accounts(additional_properties)
        property_accounts['property_account_downpayment_categ_id'] = 'product.category'
        return property_accounts
