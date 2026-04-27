from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools import format_list
import base64
import csv
import io
import pytz


class HrPayrollPaymentReportWizard(models.TransientModel):
    _inherit = 'hr.payroll.payment.report.wizard'

    export_format = fields.Selection(selection_add=[('l10n_ae_wps', 'UAE WPS')], default='l10n_ae_wps', ondelete={'l10n_ae_wps': 'set csv'})
    l10n_ae_employer_narrative = fields.Char(string="Employer Reference for WPS (Optional)")

    def _l10n_ae_get_company_wps(self, raise_if_multi=False):
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

    def _perform_checks(self):
        super()._perform_checks()
        if self.export_format == 'l10n_ae_wps':
            payslips = self.payslip_ids.filtered(lambda p: p.state == "done" and p.net_wage > 0)
            employees = payslips.employee_id
            invalid_banks_employee_ids = employees.filtered(lambda e: not e.bank_account_id.bank_id.l10n_ae_routing_code)
            if invalid_banks_employee_ids:
                raise UserError(_(
                    "Missing UAE routing code for the bank account for the following employees:\n%s",
                    format_list(self.env, invalid_banks_employee_ids.mapped('name'))))
            missing_id_employee_ids = employees.filtered(lambda e: not e.identification_id)
            if missing_id_employee_ids:
                raise UserError(_(
                    "Missing unique Identification No. for the following employees:\n%s",
                    format_list(self.env, missing_id_employee_ids.mapped('name'))))

            company = self._l10n_ae_get_company_wps(raise_if_multi=True)
            company_bank_account = company.l10n_ae_bank_account_id
            if not company_bank_account:
                raise UserError(_("Please set the salaries bank account in the settings"))
            if not company_bank_account.bank_id.l10n_ae_routing_code:
                raise UserError(_("Missing UAE routing code for the salaries bank account"))
            if not company.l10n_ae_employer_code:
                raise UserError(_("Please set the Employer Unique ID in the settings"))

    def _l10n_ae_wps_render_csv(self, create_time):
        csv_data = io.StringIO()
        csv_writer = csv.writer(csv_data, delimiter=',')

        sif_records = self.payslip_ids._l10n_ae_get_wps_data()
        sif_footer = self._l10n_ae_get_wps_footer(create_time)

        for row in sif_records + sif_footer:
            csv_writer.writerow(row)
        csv_data.seek(0)
        generated_file = csv_data.read()
        csv_data.close()
        return base64.encodebytes(generated_file.encode())

    def generate_payment_report(self):
        super().generate_payment_report()
        if self.export_format == 'l10n_ae_wps':
            now = fields.Datetime.now()
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            create_time = pytz.utc.localize(now, is_dst=None).astimezone(user_tz)
            wps_report = self._l10n_ae_wps_render_csv(create_time)
            self._write_file(wps_report, '.sif', self._get_l10n_ae_wps_file_name(create_time))

    def _get_l10n_ae_wps_file_name(self, create_time):
        self.ensure_one()
        timestamp = create_time.strftime('%y%m%d%H%M%S')
        employer_code = self._l10n_ae_get_company_wps().l10n_ae_employer_code
        return f"{(employer_code or '')[:13].zfill(13)}{timestamp}"

    def _l10n_ae_get_wps_footer(self, create_time):
        self.ensure_one()
        company = self._l10n_ae_get_company_wps()
        return [[
            "SCR",
            (company.l10n_ae_employer_code or '').zfill(13),
            company.l10n_ae_bank_account_id.bank_id.l10n_ae_routing_code or '',
            create_time.strftime("%Y-%m-%d") if create_time else '',
            create_time.strftime("%H%M") if create_time else '',
            self.payslip_run_id.date_start and self.payslip_run_id.date_start.strftime("%m%Y") or '',
            len(self.payslip_ids),
            self.env['hr.payslip']._l10n_ae_get_wps_formatted_amount(sum(self.payslip_ids.mapped('net_wage'))),
            "AED",
            self.l10n_ae_employer_narrative or '',
        ]]
