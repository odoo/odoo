from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('es_common', 'account.tax')
    def _get_es_facturae_account_tax_es_common(self):
        return self._parse_csv('es_common', 'account.tax', module='l10n_es_edi_facturae')

    @template('es_common_mainland', 'account.tax')
    def _get_es_facturae_account_tax_es_common_mainland(self):
        return self._parse_csv('es_common_mainland', 'account.tax', module='l10n_es_edi_facturae')

    @template('es_canary_common', 'account.tax')
    def _get_es_facturae_account_tax_es_canary_common(self):
        return self._parse_csv('es_canary_common', 'account.tax', module='l10n_es_edi_facturae')
