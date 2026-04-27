# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class HRPayslip(models.Model):
    _inherit = 'hr.payslip'

    l10n_sa_wps_file_reference = fields.Char(string="WPS File Reference", copy=False)

    def _get_data_files_to_update(self):
        # Note: file order should be maintained
        return super()._get_data_files_to_update() + [(
            'l10n_sa_hr_payroll', [
                'data/hr_salary_rule_saudi_data.xml',
                'data/hr_salary_rule_expat_data.xml',
            ])]

    @api.model
    def _l10n_sa_departure_reason_codes(self):
        return self.env['hr.departure.reason']._get_default_departure_reasons() | {
            'clause_77': 9661,
            'end_of_contract': 9662,
        }

    def _l10n_sa_wps_generate_file_reference(self):
        # if all were previously printed together, dont increment sequence
        if not all(self.mapped('l10n_sa_wps_file_reference')) or len(set(self.mapped('l10n_sa_wps_file_reference'))) != 1:
            # else make a new sequence
            self.l10n_sa_wps_file_reference = self.env['ir.sequence'].next_by_code("l10n_sa.wps")
        return self[:1].l10n_sa_wps_file_reference

    @api.model
    def _l10n_sa_format_float(self, val):
        currency = self.env.ref('base.SAR')
        return f'{currency.round(val):.{currency.decimal_places}f}'

    def _l10n_sa_get_wps_data(self):
        header = [
            "[32B-AMT]",
            "[59-ACC]",
            "[59-NAME]",
            "[57-BANK]",
            "[70-DET]",
            "[RET-CODE]",
            "[MOL-BAS]",
            "[MOL-HAL]",
            "[MOL-OEA]",
            "[MOL-DED]",
            "[MOL-ID]",
            "[TRN-REF]",
            "[TRN-STATUS]",
            "[TRN-DATE]"
        ]
        rows = []

        all_codes = ['BASIC', 'GROSS', 'NET', 'HOUALLOW']
        all_line_values = self._get_line_values(all_codes)

        for payslip in self:
            employee_id = payslip.employee_id

            net = all_line_values['NET'][payslip.id]['total']
            basic = all_line_values['BASIC'][payslip.id]['total']
            gross = all_line_values['GROSS'][payslip.id]['total']
            housing = all_line_values['HOUALLOW'][payslip.id]['total']

            extra_income = gross - basic - housing
            deductions = gross - net

            rows.append([
                self._l10n_sa_format_float(net),
                employee_id.bank_account_id.acc_number or "",
                employee_id.name or "",
                (employee_id.bank_account_id.bank_id.l10n_sa_sarie_code or "") if employee_id.bank_account_id.bank_id != payslip.company_id.l10n_sa_bank_account_id.bank_id else "",
                employee_id.contract_id.l10n_sa_wps_description or "",
                '',  # [RET-CODE]: Required blank cell
                self._l10n_sa_format_float(basic),
                self._l10n_sa_format_float(housing),
                self._l10n_sa_format_float(extra_income),
                self._l10n_sa_format_float(deductions),
                employee_id.l10n_sa_employee_code or "",
                '',  # [TRN-REF]: Required blank cell
                '',  # [TRN-STATUS]: Required blank cell
                '',  # [TRN-DATE]: Required blank cell
            ])
        return [header, *rows]

    def action_payslip_payment_report(self, export_format='l10n_sa_wps'):
        action = super().action_payslip_payment_report()
        if self.company_id.country_code != 'SA':
            return action
        action.update({
            'context': {
                **action['context'],
                'default_export_format': export_format,
            },
        })
        return action
