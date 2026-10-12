# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _withholding_tax_account_tax_group_demo(self, template_code):
        # The demo withholding tax below uses the local VDS group, leaving the generic "WTH" one unused
        res = super()._withholding_tax_account_tax_group_demo(template_code)
        if template_code == 'bd':
            res.pop('withholding_demo_tax_group', None)
        return res

    @template(template='bd', model='account.tax', demo=True)
    def _l10n_bd_withholding_tax_account_tax_demo(self):
        return {
            'withholding_demo_tax': {
                'name': 'VDS 15%',
                'amount': -15,
                'tax_group_id': 'tax_group_bd_vds',
                'description': 'VAT Deducted at Source',
                'invoice_label': 'VDS 15%',
                'invoice_repartition_line_ids': [
                    Command.create({
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'repartition_type': 'tax',
                        'account_id': 'l10n_bd_211530',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.create({
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'repartition_type': 'tax',
                        'account_id': 'l10n_bd_211530',
                    }),
                ],
            },
        }
