from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('it', 'account.tax')
    def _get_it_account_tax(self):
        base_taxes = self._parse_csv('it', 'account.tax', module='l10n_it')
        edi_fields_taxes = self._parse_csv('it', 'account.tax', module='l10n_it_edi')
        self._deref_account_tags('it', base_taxes)
        self._deref_account_tags('it', edi_fields_taxes)

        for xml_id, edi_values in edi_fields_taxes.items():
            if xml_id in base_taxes:
                base_taxes[xml_id].update(edi_values)
        return base_taxes
