# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_data_files_to_update(self):
        # Note: file order should be maintained
        return super()._get_data_files_to_update() + [(
            'l10n_be_hr_contract_salary', [
                'data/cp200/employee_termination_fees_data.xml',
            ])]

    def _get_representation_fees_threshold(self, localdict):
        self.ensure_one()
        contract = self.contract_id
        result = 0
        if contract.job_id.l10n_be_custom_representation_fees:
            for fee in ['homeworking', 'phone', 'internet', 'car_management']:
                result += self._rule_parameter(f'cp200_representation_fees_{fee}') if contract.job_id[f'l10n_be_custom_representation_fees_{fee}'] else 0
        else:
            result = super()._get_representation_fees_threshold(localdict)
        return result
