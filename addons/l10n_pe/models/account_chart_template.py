from odoo import models


class AccountChartTemplate(models.Model):

    _inherit = 'account.chart.template'

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        """Load the rounding method properly to the company once the CoA is installed.
        """
        company.filtered(lambda c: c.country_id.id == self.env.ref('base.pe').id).write({
            'tax_calculation_rounding_method': 'round_globally',
        })
        return super()._load(sale_tax_rate, purchase_tax_rate, company)
