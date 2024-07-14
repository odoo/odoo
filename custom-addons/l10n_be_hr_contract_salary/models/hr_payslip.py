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

    def _get_dashboard_warnings(self):
        res = super()._get_dashboard_warnings()
        belgian_companies = self.env.companies.filtered(lambda c: c.country_id.code == 'BE')
        if belgian_companies:
            ip_eligible_contract = self.env['hr.contract'].search([
                ('job_id.l10n_be_contract_ip', '=', True),
                ('ip', '=', False),
                ('state', 'in', ['draft', 'open']),
                ('company_id', 'in', belgian_companies.ids),
            ])
            if ip_eligible_contract:
                ip_eligible_str = _('Employees without Intellectual Property')
                res.append({
                    'string': ip_eligible_str,
                    'count': len(ip_eligible_contract),
                    'action': self._dashboard_default_action(ip_eligible_str, 'hr.contract', ip_eligible_contract.ids),
                })

            tax_exemption_eligible_contract = self.env['hr.contract'].search([
                ('rd_percentage', '=', 0),
                ('job_id.l10n_be_contract_withholding_taxes_exemption', '=', True),
                ('employee_id.certificate', 'in', ['bachelor', 'master', 'doctor', 'civil_engineer']),
                ('state', 'in', ['draft', 'open']),
                ('company_id', 'in', belgian_companies.ids),
            ])
            if tax_exemption_eligible_contract:
                tax_exemption_eligible_str = _('Employees without Withholding Taxes Exemption')
                res.append({
                    'string': tax_exemption_eligible_str,
                    'count': len(tax_exemption_eligible_contract),
                    'action': self._dashboard_default_action(tax_exemption_eligible_str, 'hr.contract', tax_exemption_eligible_contract.ids),
                })
        return res

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
