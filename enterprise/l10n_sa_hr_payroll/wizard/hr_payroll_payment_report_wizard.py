from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools import format_list
import base64
import csv
import io


class HrPayrollPaymentReportWizard(models.TransientModel):
    _inherit = 'hr.payroll.payment.report.wizard'

    export_format = fields.Selection(selection_add=[('l10n_sa_wps', 'Saudi WPS')], default='l10n_sa_wps', ondelete={'l10n_sa_wps': 'set csv'})
    l10n_sa_wps_value_date = fields.Date(default=fields.Date.today(), string="WPS Value Date", required=True)
    l10n_sa_wps_debit_date = fields.Date(string="WPS Debit Date")

    def _l10n_sa_get_company_wps(self, raise_if_multi=False):
        """
        Return the appropriate company based on whether the
        wizard is called upon a batch or individual payslips
        :param raise_if_multi: (optional) Check and raise error if payslips belong to multiple companies
        :return: A record of res.company
        """
        self.ensure_one()
        if self.payslip_run_id:
            return self.payslip_run_id.company_id
        if raise_if_multi and len(self.payslip_ids.company_id) > 1:
            raise UserError(_("WPS report can only be generated for one company at a time"))
        return self.payslip_ids.company_id[:1]

    def _l10n_sa_wps_render_csv(self):
        csv_data = io.StringIO()
        csv_writer = csv.writer(csv_data, delimiter='\t')

        header = self._l10n_sa_get_wps_header()
        records = self.payslip_ids._l10n_sa_get_wps_data()

        for row in header + records:
            csv_writer.writerow(row)
        csv_writer.writerow(['-'])  # Required to indicate EOF
        csv_data.seek(0)
        generated_file = csv_data.read()
        csv_data.close()
        return base64.encodebytes(generated_file.encode())

    def _perform_checks(self):
        super()._perform_checks()
        if self.export_format == 'l10n_sa_wps':
            company = self._l10n_sa_get_company_wps(raise_if_multi=True)
            if company.country_code != 'SA':
                raise UserError(_("Saudi WPS report can only be printed for KSA companies"))
            payslips = self.payslip_ids.filtered(lambda p: p.state == "done" and p.net_wage > 0)
            employees = payslips.employee_id
            invalid_banks_employee_ids = employees.filtered(lambda e: not e.bank_account_id.bank_id.l10n_sa_sarie_code)
            if invalid_banks_employee_ids:
                raise UserError(_(
                    "Missing SARIE code for the bank account for the following employees:\n%s",
                    format_list(self.env, invalid_banks_employee_ids.mapped('name'))))
            company_bank_account = company.l10n_sa_bank_account_id
            if not company_bank_account:
                raise UserError(_("Please set the establishment's bank account in the settings"))
            if not company_bank_account.bank_id.l10n_sa_sarie_code:
                raise UserError(_("Missing SARIE code on the company bank %s"), company_bank_account.bank_id.name)
            if not company_bank_account.bank_id.l10n_sa_bank_establishment_code:
                raise UserError(_("Missing establishment code on the company bank %s"), company_bank_account.bank_id.name)
            if not company.l10n_sa_mol_establishment_code:
                raise UserError(_("Please set the MoL Establishment ID in the settings."))
            if self.l10n_sa_wps_debit_date and self.l10n_sa_wps_value_date and self.l10n_sa_wps_debit_date <= self.l10n_sa_wps_value_date:
                raise UserError(_('The debit date cannot be later than the value date'))

    def generate_payment_report(self):
        super().generate_payment_report()
        if self.export_format == 'l10n_sa_wps':
            wps_report = self._l10n_sa_wps_render_csv()
            self._write_file(wps_report, '.csv', self._get_l10n_sa_wps_file_reference())

    def _get_l10n_sa_wps_file_reference(self):
        if self.payslip_run_id:
            return self.payslip_run_id._l10n_sa_wps_generate_file_reference()
        return self.payslip_ids._l10n_sa_wps_generate_file_reference()

    def _l10n_sa_get_wps_header(self):
        self.ensure_one()
        company = self._l10n_sa_get_company_wps()
        company_bank_account = company.l10n_sa_bank_account_id

        header = [
            "[DEST-ID]",
            "[ESTB-ID]",
            "[BANK-ACC]",
            "[32A-CCY]",
            "[32A-VAL]",
            "[32A-AMT]",
            "[D-DATE]",
            "[FILE-REF]",
            "[FILE-REJCDE]",
            "[MOL-ESTBID]",
        ]
        row = [
            company_bank_account.bank_id.l10n_sa_sarie_code or "",
            company_bank_account.bank_id.l10n_sa_bank_establishment_code or "",
            company_bank_account.acc_number or "",
            "SAR",
            (self.l10n_sa_wps_value_date or fields.Date.today()).strftime("%Y%m%d"),
            self.env['hr.payslip']._l10n_sa_format_float(sum(self.payslip_ids.mapped('net_wage'))),
            self.l10n_sa_wps_debit_date.strftime("%Y%m%d") if self.l10n_sa_wps_debit_date else '',
            self._get_l10n_sa_wps_file_reference() or "",
            '',  # Rejection Code: Required blank cell
            company.l10n_sa_mol_establishment_code or "",
        ]

        return [header, row]
