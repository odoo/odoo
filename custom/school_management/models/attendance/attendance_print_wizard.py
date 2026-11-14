import base64

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UniversityAttendancePrintWizard(models.TransientModel):
    _name = "university.attendance.print.wizard"
    _description = "Attendance Reports & Export"

    month = fields.Selection(
        [(str(month), str(month)) for month in range(1, 13)],
        string="Month",
        default=lambda self: str(
            fields.Date.from_string(fields.Date.context_today(self)).month
        ),
        required=True,
    )
    year = fields.Integer(
        string="Year",
        default=lambda self: fields.Date.from_string(
            fields.Date.context_today(self)
        ).year,
        required=True,
    )
    section_ids = fields.Many2many(
        "university.class.section",
        string="Class Sections",
    )

    def _attendance(self):
        return self.env["university.attendance"]

    @api.onchange("year", "month")
    def _onchange_period(self):
        if not (2000 <= (self.year or 0) <= 2100) or not (1 <= int(self.month or 0) <= 12):
            return {"warning": {
                "title": _("Invalid period"),
                "message": _("Please choose a valid month and year."),
            }}

    @api.constrains("year", "month")
    def _check_period(self):
        for wizard in self:
            if not (2000 <= (wizard.year or 0) <= 2100):
                raise ValidationError(_("Please choose a year between 2000 and 2100."))
            if not (1 <= int(wizard.month or 0) <= 12):
                raise ValidationError(_("Please choose a month between 1 and 12."))

    def get_grid_data(self):
        self.ensure_one()
        month = int(self.month)
        year = self.year
        sections = self.section_ids
        if not sections:
            sections = self._attendance()._get_role_sections()
        grid = self._attendance().get_grid_data(sections.ids, month, year)
        for section in grid.get("sections") or []:
            for student in section["students"]:
                counts = {"present": 0, "absent": 0, "late": 0, "excused": 0}
                for cell in student["cells"]:
                    if cell["status"] in counts:
                        counts[cell["status"]] += 1
                student["counts"] = counts
                student["rate"] = self._attendance()._attendance_percentage(counts)
        return grid

    def _download(self, filename, content, mimetype):
        attachment = self.env["ir.attachment"].create({
            "name": filename,
            "datas": base64.b64encode(content),
            "mimetype": mimetype,
        })
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "new",
        }

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref(
            "school_management.action_report_attendance_grid"
        ).report_action(self)

    def action_export_xlsx(self):
        self.ensure_one()
        content = self._attendance().build_grid_xlsx(
            int(self.month), self.year, self.section_ids.ids
        )
        return self._download(
            "attendance_grid_%s-%02d.xlsx" % (self.year, int(self.month)),
            content,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def action_export_csv(self):
        self.ensure_one()
        content = self._attendance().build_grid_csv(
            int(self.month), self.year, self.section_ids.ids
        )
        return self._download(
            "attendance_grid_%s-%02d.csv" % (self.year, int(self.month)),
            content,
            "text/csv",
        )

    def action_export_at_risk_csv(self):
        self.ensure_one()
        month = int(self.month)
        year = self.year
        sections = self.section_ids
        if not sections:
            sections = self._attendance()._get_role_sections()
        content = self._attendance().build_at_risk_csv(month, year, sections.ids)
        return self._download(
            "at_risk_attendance_%s-%02d.csv" % (year, month),
            content,
            "text/csv",
        )