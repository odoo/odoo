# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ke', 'account.tax')
    def _get_ke_account_tax_etims_type(self):
        """Apply the OSCU tax type code to the taxes on the tax template."""
        additional = self._parse_csv('ke', 'account.tax', module='l10n_ke_edi_oscu')
        return additional
