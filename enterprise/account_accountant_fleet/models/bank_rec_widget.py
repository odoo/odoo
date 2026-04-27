# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class BankRecWidget(models.Model):
    _inherit = 'bank.rec.widget'

    # -------------------------------------------------------------------------
    # LINES METHODS
    # -------------------------------------------------------------------------

    def _lines_prepare_tax_line(self, tax_line_vals):
        # EXTENDS account_accountant
        results = super()._lines_prepare_tax_line(tax_line_vals)
        results['vehicle_id'] = tax_line_vals['vehicle_id']
        return results

    # -------------------------------------------------------------------------
    # LINES UPDATE METHODS
    # -------------------------------------------------------------------------

    def _line_value_changed_vehicle_id(self, line):
        self.ensure_one()
        self._lines_turn_auto_balance_into_manual_line(line)

        if line.flag != 'tax_line':
            self._lines_recompute_taxes()
