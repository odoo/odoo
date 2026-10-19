from odoo import api, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _round_tax_details_tax_amounts(self, base_lines, company, mode='mixed'):
        # EXTENDS 'account'
        country_code = company.account_fiscal_country_id.code
        if country_code == 'PT':
            mode = 'included'
        super()._round_tax_details_tax_amounts(base_lines, company, mode=mode)

    @api.model
    def _round_tax_details_base_lines(self, base_lines, company, mode='mixed'):
        # EXTENDS 'account'
        country_code = company.account_fiscal_country_id.code
        if country_code == 'PT':
            mode = 'included'
        super()._round_tax_details_base_lines(base_lines, company, mode=mode)
