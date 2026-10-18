from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ae', 'account.tax')
    def _get_ae_ubl_pint_account_tax(self):
        """ Add the UBL tax category codes to the 'ae' chart's taxes (also used by the post-init hook). """
        return self._parse_csv('ae', 'account.tax', module='l10n_ae_ubl_pint')
