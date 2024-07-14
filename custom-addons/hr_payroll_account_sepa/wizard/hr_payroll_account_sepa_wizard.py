# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class HrPayslipSepaWizard(models.TransientModel):
    _name = 'hr.payslip.sepa.wizard'
    _description = 'HR Payslip SEPA Wizard'

    journal_id = fields.Many2one(
        string='Bank Journal', comodel_name='account.journal', required=True,
        default=lambda self: self.env['account.journal'].search([('type', '=', 'bank')], limit=1))

    def generate_sepa_xml_file(self):
        payslips = self.env['hr.payslip'].browse(self.env.context['active_ids'])
        payslips = payslips.filtered(lambda p: p.state == "done" and p.net_wage > 0)
        employees = payslips.mapped('employee_id')
        employee_bank_data = [emp for emp in self.env['hr.employee']._get_account_holder_employees_data() if emp["id"] in employees.ids]

        invalid_employee_ids = self.env['hr.employee']._get_invalid_iban_employee_ids(employee_bank_data)
        user_error_message = ""
        if invalid_employee_ids:
            user_error_message += (_('Invalid bank account for the following employees:\n%s', '\n'.join(self.env['hr.employee'].browse(invalid_employee_ids).mapped('name'))))

        untrusted_banks_employee_ids = self.env['hr.employee']._get_untrusted_bank_employee_ids(employee_bank_data)
        if untrusted_banks_employee_ids:
            if invalid_employee_ids:
                user_error_message += "\n\n"
            user_error_message += _('Untrusted bank account for the following employees:\n%s', '\n'.join(self.env['hr.employee'].browse(untrusted_banks_employee_ids).mapped('name')))

        if user_error_message:
            raise UserError(user_error_message)

        payslips.sudo()._create_xml_file(self.journal_id)


class HrPayslipRunSepaWizard(models.TransientModel):
    _name = 'hr.payslip.run.sepa.wizard'
    _description = 'HR Payslip Run SEPA Wizard'

    def _get_filename(self):
        payslip_run_id = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))
        return payslip_run_id.sepa_export_filename or payslip_run_id.name

    journal_id = fields.Many2one(
        string='Bank Journal', comodel_name='account.journal', required=True,
        default=lambda self: self.env['account.journal'].search([('type', '=', 'bank')], limit=1))
    file_name = fields.Char(string='File name', required=True, default=_get_filename)

    def generate_sepa_xml_file(self):
        payslip_run = self.env['hr.payslip.run'].browse(self.env.context['active_id'])
        payslips = payslip_run.mapped('slip_ids').filtered(lambda p: p.state == "done" and p.net_wage > 0)

        employees = payslips.mapped('employee_id')
        employee_bank_data = [emp for emp in self.env['hr.employee']._get_account_holder_employees_data() if
                              emp["id"] in employees.ids]

        if employee_bank_data:
            user_error_message = ""

            invalid_employee_ids = self.env['hr.employee']._get_invalid_iban_employee_ids(employee_bank_data)
            if invalid_employee_ids:
                user_error_message += (_('Invalid bank account for the following employees:\n%s', '\n'.join(self.env['hr.employee'].browse(invalid_employee_ids).mapped('name'))))

            untrusted_banks_employee_ids = self.env['hr.employee']._get_untrusted_bank_employee_ids(employee_bank_data)
            if untrusted_banks_employee_ids:
                if invalid_employee_ids:
                    user_error_message += "\n\n"
                user_error_message += _('Untrusted bank account for the following employees:\n%s', '\n'.join(self.env['hr.employee'].browse(untrusted_banks_employee_ids).mapped('name')))

            if user_error_message:
                raise UserError(user_error_message)

        payslips.sudo()._create_xml_file(self.journal_id, self.file_name)
