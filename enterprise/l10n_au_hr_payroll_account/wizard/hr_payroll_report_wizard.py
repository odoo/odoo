import base64

from odoo import fields, models, _
from odoo.exceptions import RedirectWarning


class HrPayrollPaymentReportWizard(models.TransientModel):
    _inherit = 'hr.payroll.payment.report.wizard'

    export_format = fields.Selection(selection_add=[('aba', 'ABA')], default='aba', ondelete={'aba': 'set csv'})
    journal_id = fields.Many2one(
        string='Bank Journal', comodel_name='account.journal', required=True,
        default=lambda self: self.env['account.journal'].search([('type', '=', 'bank')], limit=1))

    def _generate_aba_file(self):
        self.ensure_one()
        aba_date = fields.Date.context_today(self).strftime('%d%m%y')
        payslip_batch = self.env['hr.payslip.run'].search([('l10n_au_payment_batch_id', '=', self.id)])
        aba_values = {
            'aba_date': aba_date,
            'aba_description': 'PAYROLL',
            'self_balancing_reference': 'PAYROLL %s' % aba_date,
            'payments_data': [{
                'name': payslip.number,
                'amount': payslip.net_wage,
                'bank_account': payslip.employee_id.bank_account_id,
                'account_holder': payslip.employee_id,
                'transaction_code': "53",  # PAYROLL
                'reference': payslip.number,
            } for payslip in payslip_batch.slip_ids]
        }
        file_data = self.env['account.batch.payment']._create_aba_document(self.journal_id, aba_values).encode()
        return base64.encodebytes(file_data)

    def _perform_checks(self):
        if self.export_format == 'aba':
            self.env['account.batch.payment']._check_valid_journal_for_aba(self.journal_id)
            employees = self.payslip_ids.employee_id.filtered(
                lambda emp: emp.bank_account_id.acc_type != "aba" or not emp.bank_account_id.aba_bsb or not emp.bank_account_id.allow_out_payment
            )
            if employees:
                raise RedirectWarning(
                    message=_("Following bank account(s) have invalid BSB or account number.\n%s",
                            "\n".join(employees.mapped("name"))),
                    action=employees._get_records_action(name=_("Configure Bank Account(s)"), target="new"),
                    button_text=_("Configure Bank Account(s)")
                )
            return
        super()._perform_checks()

    def generate_payment_report(self):
        super().generate_payment_report()
        if self.export_format == 'aba':
            payment_report = self._generate_aba_file()
            self._write_file(payment_report, '.txt')
