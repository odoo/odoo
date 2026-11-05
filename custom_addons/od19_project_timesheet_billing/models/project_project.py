from odoo import _, api, fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    od19_unbilled_timesheet_count = fields.Integer(
        string="Unbilled Timesheets",
        compute="_compute_od19_unbilled_timesheet",
        compute_sudo=True,
    )
    od19_unbilled_timesheet_hours = fields.Float(
        string="Unbilled Hours",
        compute="_compute_od19_unbilled_timesheet",
        compute_sudo=True,
    )

    @api.depends("allow_billable")
    def _compute_od19_unbilled_timesheet(self):
        domain = [
            ("od19_is_billable_unbilled", "=", True),
            ("project_id", "in", self.ids),
        ]
        grouped = self.env["account.analytic.line"]._read_group(
            domain, ["project_id"], ["__count", "unit_amount:sum"],
        )
        mapped = {project.id: (count, hours) for project, count, hours in grouped}
        for project in self:
            count, hours = mapped.get(project.id, (0, 0))
            project.od19_unbilled_timesheet_count = count
            project.od19_unbilled_timesheet_hours = hours

    def action_od19_view_unbilled_timesheets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Unbilled Timesheets / Timesheet รอเรียกเก็บ"),
            "res_model": "account.analytic.line",
            "view_mode": "list,form",
            "domain": [
                ("od19_is_billable_unbilled", "=", True),
                ("project_id", "=", self.id),
            ],
        }
