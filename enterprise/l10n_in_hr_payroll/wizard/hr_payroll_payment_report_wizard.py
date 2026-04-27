# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import base64
from datetime import datetime, date

from odoo import api, fields, models, _
from odoo.tools.misc import xlsxwriter
from odoo.exceptions import UserError


class HrPayrollPaymentReportWizard(models.TransientModel):
    _inherit = 'hr.payroll.payment.report.wizard'

    export_format = fields.Selection(selection_add=[('advice', 'Payment Advice')], default='advice', ondelete={'advice': 'set default'})
    l10n_in_payment_advice_pdf = fields.Binary('Payment Advice PDF', readonly=True, attachment=False)
    l10n_in_payment_advice_filename_pdf = fields.Char()
    l10n_in_payment_advice_xlsx = fields.Binary('Payment Advice XLSX', readonly=True, attachment=False)
    l10n_in_payment_advice_filename_xlsx = fields.Char()
    l10n_in_reference = fields.Char(string="Reference")
    l10n_in_neft = fields.Boolean(string="NEFT Transaction", help="Tick this box if your company use online transfer for salary")
    l10n_in_cheque_number = fields.Char(string="Cheque Number")
    l10n_in_state_pdf = fields.Boolean()
    l10n_in_state_xlsx = fields.Boolean()

    def _get_report_data(self, payslip):
        employee = payslip.employee_id
        bank_account = employee.bank_account_id

        return {
            'name': employee.name,
            'acc_no': bank_account.acc_number or '',
            'ifsc_code': bank_account.bank_bic or '',
            'bysal': payslip.net_wage,
            'debit_credit': 'C',
        }

    def _get_pdf_data(self):
        total_bysal = 0
        lines = []

        partner_bank = self.company_id.partner_id.bank_ids
        partner_bank_name = partner_bank[0].bank_id.name if partner_bank else ''
        partner_bank_acc_number = partner_bank[0].acc_number if partner_bank else ''

        for payslip in self.payslip_ids:
            report_line_data = self._get_report_data(payslip)
            lines.append(report_line_data)
            total_bysal += report_line_data['bysal']

        return {
            'bank': {
                'bank_name': partner_bank_name,
                'acc_number': partner_bank_acc_number,
            },
            'line_ids': {
                'lines': lines,
                'total_bysal': total_bysal,
            },
            'current_date': date.today(),
            'l10n_in_neft': self.l10n_in_neft,
            'l10n_in_cheque_number': self.l10n_in_cheque_number,
            'note': _('Please make the payroll transfer from above account number to the below mentioned account numbers towards employee salaries:'),
        }

    def _get_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payment Advice'),
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    @api.model_create_multi
    def create(self, vals_list):
        date = datetime.now()
        for vals in vals_list:
            if not vals.get('l10n_in_reference'):
                advice_year = date.strftime('%m-%Y')
                number = self.env['ir.sequence'].next_by_code('payment.advice')
                vals['l10n_in_reference'] = f"PAY/{advice_year}/{number}"
        return super().create(vals_list)

    def generate_payment_report_pdf(self):
        self.ensure_one()
        self._perform_checks()

        pdf_content = self.env["ir.actions.report"].sudo()._render_qweb_pdf(
            self.env.ref('l10n_in_hr_payroll.payroll_advice_report').id,
            res_ids=self.ids, data=self._get_pdf_data()
        )[0]

        payment_report = base64.encodebytes(pdf_content)
        self.l10n_in_payment_advice_pdf = payment_report
        self.l10n_in_payment_advice_filename_pdf = f"{self.l10n_in_reference}.pdf"
        self._write_file(payment_report, '.pdf', self.l10n_in_reference)
        self.l10n_in_state_pdf = True

        return self._get_wizard()

    def generate_payment_report_xls(self):
        self.ensure_one()
        self._perform_checks()

        output = io.BytesIO()

        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Payment Advice Report')
        header_format = workbook.add_format({'bold': True, 'pattern': 1, 'bg_color': '#E0E0E0', 'align': 'center'})
        cell_format = workbook.add_format({'align': 'center'})
        total_format = workbook.add_format({'bold': True, 'align': 'center'})
        headers = [_('SI No.'), _('Name Of Employee'), _('Bank Account No.'), _('IFSC Code'), _('By Salary'), _('C/D')]

        worksheet.write_row(0, 0, headers, header_format)

        total_salary = 0

        for row_idx, payslip in enumerate(self.payslip_ids, start=1):
            row_data = self._get_report_data(payslip)
            worksheet.write(row_idx, 0, row_idx, cell_format)
            worksheet.write_row(row_idx, 1, row_data.values(), cell_format)
            total_salary += row_data['bysal']

        worksheet.set_column(0, 0, 10)  # SI No.
        worksheet.set_column(1, 1, 20)  # Name Of Employee
        worksheet.set_column(2, 2, 20)  # Bank Account No.
        worksheet.set_column(3, 3, 15)  # IFSC Code
        worksheet.set_column(4, 4, 15)  # By Salary
        worksheet.set_column(5, 5, 10)  # C/D

        row_idx += 1
        worksheet.write(row_idx + 1, 2, "Total:", total_format)
        worksheet.write(row_idx + 1, 4, total_salary, total_format)

        workbook.close()
        xlsx_data = output.getvalue()
        payment_report = base64.encodebytes(xlsx_data)

        self.l10n_in_payment_advice_xlsx = payment_report
        self.l10n_in_payment_advice_filename_xlsx = f"{self.l10n_in_reference}.xlsx"
        self._write_file(payment_report, '.xlsx', self.l10n_in_reference)
        self.l10n_in_state_xlsx = True

        return self._get_wizard()

    def _perform_checks(self):
        super()._perform_checks()
        if self.company_id.country_code == 'IN':
            payslip_ids = self.payslip_ids.filtered(lambda p: p.state == "done" and p.net_wage > 0)
            invalid_ifsc_employee_ids = payslip_ids.employee_id._get_employees_with_invalid_ifsc()
            if invalid_ifsc_employee_ids:
                raise UserError(_(
                    'The file cannot be generated, the employees listed below have a bank account with no bank\'s identification number.\n%s',
                    '\n'.join(invalid_ifsc_employee_ids.mapped('name'))
                ))
