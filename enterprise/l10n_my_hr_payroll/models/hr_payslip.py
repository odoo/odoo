# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_data_files_to_update(self):
        # Note: file order should be maintained
        return super()._get_data_files_to_update() + [(
            'l10n_my_hr_payroll', [
                'data/hr_rule_parameter_data.xml',
            ])]
