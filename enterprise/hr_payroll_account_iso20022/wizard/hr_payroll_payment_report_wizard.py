import base64

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools import format_list


class HrPayrollPaymentReportWizard(models.TransientModel):
    _inherit = 'hr.payroll.payment.report.wizard'

    export_format = fields.Selection(selection_add=[('sepa', 'SEPA'), ('iso20022_ch', 'Swiss ISO20022')], default='sepa', ondelete={'sepa': 'set csv', 'iso20022_ch': 'set csv'})
    journal_id = fields.Many2one(
        string='Bank Journal', comodel_name='account.journal', required=True,
        default=lambda self: self.env['account.journal'].search([('type', '=', 'bank')], limit=1))

    def _create_sepa_binary(self):
        # Map the necessary data
        payments_data = []
        for slip in self.payslip_ids.filtered(lambda p: p.state == "done" and p.net_wage > 0):
            payments_data.append(slip._get_payments_vals(self.journal_id))
        payment_method_code = self.env.context.get('payment_method') or 'sepa_ct'

        # Generate XML File
        xml_doc = self.journal_id.sudo().with_context(
            sepa_payroll_sala=True,
            l10n_be_hr_payroll_sepa_salary_payment=self.journal_id.company_id.account_fiscal_country_id.code == "BE"
        ).create_iso20022_credit_transfer(payments=payments_data, payment_method_code=payment_method_code, batch_booking=True)
        return base64.encodebytes(xml_doc)

    def _perform_checks(self):
        super()._perform_checks()
        if self.export_format in ['sepa', 'iso20022_ch']:
            employees = self.payslip_ids.employee_id.filtered(lambda e: not e.work_contact_id)
            if employees:
                raise UserError(_(
                    "Some employees (%s) don't have a work contact.",
                    format_list(self.env, employees.mapped('name'))))
            employees = self.payslip_ids.employee_id.filtered(lambda e: e.work_contact_id and not e.work_contact_id.name)
            if employees:
                raise UserError(_(
                    "Some employees (%s) don't have a valid name on the work contact.",
                    format_list(self.env, employees.mapped('name'))))
            if self.journal_id.bank_account_id.acc_type != 'iban':
                raise UserError(_(
                    "The journal '%s' requires a proper IBAN account to pay via SEPA. "
                    "Please configure it first.",
                    self.journal_id.name))

    def generate_payment_report(self):
        super().generate_payment_report()
        if self.export_format == 'sepa':
            payment_report = self.with_context(payment_method='sepa_ct')._create_sepa_binary()
            self._write_file(payment_report, '.xml')
        elif self.export_format == 'iso20022_ch':
            payment_report = self.with_context(payment_method='iso20022_ch')._create_sepa_binary()
            self._write_file(payment_report, '.xml')
