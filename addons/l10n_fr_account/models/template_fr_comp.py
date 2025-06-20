# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('fr_comp')
    def _get_fr_comp_template_data(self):
        return {
            'name': _('Companies accounting plan'),
            'parent': 'fr',
            'code_digits': 6,
            'property_account_receivable_id': 'fr_pcg_recv',
            'property_account_payable_id': 'fr_pcg_pay',
            'property_account_downpayment_categ_id': 'pcg_4191',
        }
