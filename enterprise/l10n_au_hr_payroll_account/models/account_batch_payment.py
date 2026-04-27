# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    l10n_au_is_payroll_payment = fields.Boolean("is Payroll Payment")

    def _generate_export_file(self):
        self.ensure_one()
        if self.payment_method_code == 'aba_ct' and self.l10n_au_is_payroll_payment:
            payslip_batch = self.env['hr.payslip.run'].search([('l10n_au_payment_batch_id', '=', self.id)])
            if payslip_batch.payment_report:
                return {
                    'filename': payslip_batch.payment_report_filename,
                    'file': payslip_batch.payment_report,
                }

            self._check_valid_journal_for_aba(self.journal_id)
            self._check_payment_accounts_for_aba()
            filename_date = fields.Datetime.context_timestamp(self, datetime.now()).strftime("%Y%m%d%H%M")
            aba_date = fields.Date.context_today(self).strftime('%d%m%y')
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
            file_data = self._create_aba_document(self.journal_id, aba_values).encode()
            export_file_data = {
                'filename': f'ABA-{self.journal_id.code}-{filename_date}.aba',
                'file': base64.encodebytes(file_data),
            }

            return export_file_data

        return super()._generate_export_file()

    @api.ondelete(at_uninstall=False)
    def _unlink_payslip_payment(self):
        if self.filtered(lambda batch: batch.l10n_au_is_payroll_payment and batch.state != 'draft'):
            raise ValidationError(_("You cannot delete a Payroll payment record once it is done! "
                                    "Please create a credit note to refund the payment."))
