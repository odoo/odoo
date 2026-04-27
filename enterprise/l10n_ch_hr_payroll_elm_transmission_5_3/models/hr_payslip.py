# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    l10n_ch_avs_status = fields.Selection(selection_add=[
        ('retired_wave_deduct', "Retired with Waive of Pension Deduct")
    ], ondelete={'retired_wave_deduct': 'cascade'})

    def _has_lpp_in_percentage(self):
        # To be overriden in ELM 5.3 certification module
        self.ensure_one()
        return self.contract_id.l10n_ch_lpp_in_percentage

    def _get_data_files_to_update(self):
        return super()._get_data_files_to_update() + [(
            'l10n_ch_hr_payroll_elm_transmission_5_3', [
                'data/hr_salary_rule_data.xml',
            ])]

    def _get_additional_input_line_vals(self):
        self.ensure_one()
        vals = super()._get_additional_input_line_vals()

        if self.l10n_ch_compensation_fund_id and self.employee_id.l10n_ch_children:
            input_vals = self.l10n_ch_compensation_fund_id._get_family_allowances(self.employee_id.l10n_ch_children, self.date_from)
            for val in input_vals:
                vals.append(Command.create(val))
        return vals
