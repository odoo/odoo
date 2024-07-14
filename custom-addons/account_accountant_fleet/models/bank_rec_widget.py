# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class BankRecWidget(models.Model):
    _inherit = 'bank.rec.widget'

    # -------------------------------------------------------------------------
    # LINES METHODS
    # -------------------------------------------------------------------------

    def _convert_to_tax_base_line_dict(self, line):
        # EXTENDS account_accountant
        tax_base_line_dict = super()._convert_to_tax_base_line_dict(line)
        tax_base_line_dict['vehicle'] = line.vehicle_id
        return tax_base_line_dict

    def _convert_to_tax_line_dict(self, line):
        # EXTENDS account_accountant
        tax_line_dict = super()._convert_to_tax_line_dict(line)
        tax_line_dict['vehicle'] = line.vehicle_id
        return tax_line_dict

    def _lines_prepare_tax_line(self, tax_line_vals):
        # EXTENDS account_accountant
        tax_line_data = super()._lines_prepare_tax_line(tax_line_vals)
        tax_line_data['vehicle_id'] = tax_line_vals.get('vehicle_id', False)
        return tax_line_data

    # -------------------------------------------------------------------------
    # LINES UPDATE METHODS
    # -------------------------------------------------------------------------

    def _line_value_changed_vehicle_id(self, line):
        self.ensure_one()
        self._lines_turn_auto_balance_into_manual_line(line)

        if line.flag != 'tax_line':
            self._lines_recompute_taxes()
