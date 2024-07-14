# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class SlsCustomHandler(models.AbstractModel):
    _name = 'l10n_ph.sls.report.handler'
    _inherit = 'l10n_ph.slsp.report.handler'
    _description = 'Summary Lists of Sales Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options.update({
            'move_type': 'out_invoice',
            # This mapping will be used to build the amount for each expression_label based on the grid names.
            'report_grids_map': {
                'gross_amount': ['31A', '32A', '33A', '34A'],
                'exempt_amount': ['34A'],
                'zero_rated_amount': ['33A'],
                'taxable_amount': ['31A', '32A'],
                'tax_amount': ['31B', '32B'],
                'gross_taxable_amount': ['31A', '32A', '31B', '32B'],
            }
        })
