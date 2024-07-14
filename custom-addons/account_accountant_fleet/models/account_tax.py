# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class AccountTax(models.Model):
    _inherit = 'account.tax'

    def _get_generation_dict_from_base_line(self, line_vals, tax_vals, force_caba_exigibility=False):
        grouping = super()._get_generation_dict_from_base_line(line_vals, tax_vals, force_caba_exigibility)
        vehicle = line_vals.get('vehicle')
        grouping['vehicle_id'] = vehicle.id if vehicle and not tax_vals['use_in_tax_closing'] else False
        return grouping

    def _get_generation_dict_from_tax_line(self, line_vals):
        tax_grouping = super()._get_generation_dict_from_tax_line(line_vals)
        vehicle = line_vals.get('vehicle')
        tax_grouping['vehicle_id'] = vehicle.id if vehicle else False
        return tax_grouping
