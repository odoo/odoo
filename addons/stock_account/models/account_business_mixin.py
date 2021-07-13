# -*- coding: utf-8 -*-
from odoo import api, models


class AccountBusinessMixin(models.AbstractModel):
    _inherit = 'account.business.mixin'

    @api.model
    def _get_default_product_account(self):
        # OVERRIDE
        business_vals = self._get_business_values()
        product = business_vals.get('product')
        company = business_vals.get('company')
        document_type = business_vals.get('document_type')

        if product \
                and company \
                and product.type == 'product' \
                and company.anglo_saxon_accounting \
                and document_type == 'purchase':
            product_template = product.with_company(company).product_tmpl_id
            accounts = product_template.get_product_accounts(fiscal_pos=business_vals.get('fiscal_position'))
            if accounts['stock_input']:
                return accounts['stock_input']

        return super()._get_default_product_account()
