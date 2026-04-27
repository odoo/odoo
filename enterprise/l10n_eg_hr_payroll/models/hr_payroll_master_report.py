import base64
import io
from collections import defaultdict
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.misc import xlsxwriter

XLSX = {
    "NUMBER": 0,
    "TEXT": 1,
    "DATE": 2,
    "FORMULA": 3,
    "LABEL": 4,
}


class HrEgMasterReport(models.Model):
    _name = "report.l10n_eg_hr_payroll.master"
    _description = "Eygpt Master Payroll Report"

    name = fields.Char(compute="_compute_name", store=True)
    date_from = fields.Date(required=True, default=fields.Date.today() + relativedelta(day=1))
    date_to = fields.Date(required=True, default=fields.Date.today() + relativedelta(day=1, months=1, days=-1))
    xlsx_file = fields.Binary(string="Report", readonly=True)
    xlsx_filename = fields.Char(readonly=True)
    period_has_payslips = fields.Boolean(compute="_compute_period_has_payslips")

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "EG":
            raise UserError(_("You must be logged in an Egypt company to use this feature"))
        return super().default_get(field_list)

    @api.depends("date_from", "date_to")
    def _compute_name(self):
        for report in self:
            report.name = _(
                "Master Report %(date_from)s - %(date_to)s", date_from=report.date_from, date_to=report.date_to
            )

    @api.depends("date_from", "date_to")
    def _compute_period_has_payslips(self):
        for report in self:
            payslips = report.env["hr.payslip"].search(
                [
                    ("date_from", ">=", report.date_from),
                    ("date_to", "<=", report.date_to),
                    ("company_id", "=", report.env.company.id),
                    ("state", "in", ["done", "paid"]),
                ]
            )
            report.period_has_payslips = bool(payslips)

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for report in self:
            if report.date_from > report.date_to:
                raise ValidationError(_("The starting date must be before or equal to the ending date"))

    @api.model
    def _write_row(self, worksheet, row_index, row, formats):
        for i, (formatting, *value) in enumerate(row):
            if formatting == XLSX["TEXT"]:
                worksheet.write(row_index, i, *value, formats[XLSX["TEXT"]])
            elif formatting == XLSX["DATE"]:
                worksheet.write_datetime(row_index, i, *value, formats[XLSX["DATE"]])

    def action_generate_report(self):
        company = self.env.company
        if company.country_code != "EG":
            raise UserError(_("You must be logged in an Egypt company to use this feature"))

        labels = [_("Employee ID"), _("Employee Name"), _("Joining Date"), _("Department"), _("Job Designation")]

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        formats = {
            XLSX["TEXT"]: workbook.add_format({"border": 1}),
            XLSX["DATE"]: workbook.add_format({"border": 1, "num_format": "dd/mm/yyyy"}),
            XLSX["LABEL"]: workbook.add_format({"border": 1, "bold": True}),
        }

        payslips = self.env["hr.payslip"].search(
            [
                ("date_from", ">=", self.date_from),
                ("date_to", "<=", self.date_to),
                ("company_id", "=", company.id),
                ("state", "in", ["done", "paid"]),
            ]
        )
        if not payslips:
            raise ValidationError(_("There are no eligible payslips for that period of time"))
        payslips_data = defaultdict(dict)
        for payslip in payslips:
            payslips_data[payslip.struct_id][payslip.employee_id] = payslip

        for struct in payslips_data:
            worksheet = workbook.add_worksheet(name=struct.name)

            i = 1
            for employee in payslips_data[struct]:
                joining_date = ""
                if employee.contract_id.date_start:
                    joining_date = datetime.strptime(
                        employee.contract_id.date_start.strftime("%Y-%m-%d"), "%Y-%m-%d"
                    ).date()

                row = [
                    (XLSX["TEXT"], employee.id),
                    (XLSX["TEXT"], employee.name),
                    (XLSX["DATE"], joining_date) if joining_date else (XLSX["TEXT"], ""),
                    (XLSX["TEXT"], employee.department_id.name or ""),
                    (XLSX["TEXT"], employee.job_title or ""),
                ]
                if i == 1:
                    labels.extend(payslips_data[struct][employee].line_ids.mapped("name"))
                row.extend(
                    (XLSX["TEXT"], company.currency_id.format(t))
                    for t in payslips_data[struct][employee].line_ids.mapped("total")
                )
                self._write_row(worksheet, i, row, formats)
                i += 1

            for col, label in enumerate(labels):
                worksheet.write(0, col, label, formats[XLSX["LABEL"]])
            worksheet.set_column(0, len(labels) - 1, 20)

        workbook.close()
        xlsx_data = output.getvalue()
        self.xlsx_file = base64.encodebytes(xlsx_data)
        self.xlsx_filename = f"{self.name}.xlsx"
