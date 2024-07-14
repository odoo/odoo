# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SlpCustomHandler(models.AbstractModel):
    _name = 'l10n_ph.slp.report.handler'
    _inherit = 'l10n_ph.slsp.report.handler'
    _description = 'Summary Lists of Purchases Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options.update({
            'move_type': 'in_invoice',
            # This mapping will be used to build the amount for each expression_label based on the grid names.
            'report_grids_map': {
                'gross_amount': ['42A', '42SA', '43A', '46E', '46ZR', 'CAPA'],
                'exempt_amount': ['46E'],
                'zero_rated_amount': ['46ZR'],
                'taxable_amount': ['42A', '42SA', '43A', 'CAPA'],
                'services_amount': ['42SA', '43A'],
                'capital_goods_amount': ['CAPA'],
                'non_capital_goods_amount': ['42A'],
                'tax_amount': ['42B', '42SB', '43B', 'CAPB'],
                'gross_taxable_amount': ['42A', '42SA', '43A', 'CAPA', '42B', '42SB', '43B', 'CAPB'],
            }
        })
        if options['include_imports']:
            # 47A
            options['report_grids_map']['gross_amount'].append('47A')
            options['report_grids_map']['exempt_amount'].append('47A')
            # 44A
            options['report_grids_map']['gross_amount'].append('44A')
            options['report_grids_map']['taxable_amount'].append('44A')
            options['report_grids_map']['capital_goods_amount'].append('44A')
            options['report_grids_map']['gross_taxable_amount'].append('44A')
            # 44B
            options['report_grids_map']['tax_amount'].append('44B')
            options['report_grids_map']['gross_taxable_amount'].append('44B')
