from odoo import models
from .extra_eu_tax_map import EXTRA_EU_TAX_MAP


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        rslt = super()._load(sale_tax_rate, purchase_tax_rate, company)

        if company.account_fiscal_country_id.code in [t[0] for t in EXTRA_EU_TAX_MAP]:
            company._map_extra_eu_taxes()

        return rslt
