from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('cz', 'account.tax')
    def _get_cz_control_statement_account_tax(self):
        taxes_data = self._parse_csv('cz', 'account.tax', module='l10n_cz_reports_2025')
        return {xmlid: tax_data for xmlid, tax_data in taxes_data.items() if self.ref(xmlid, raise_if_not_found=False)}
