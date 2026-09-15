from odoo import _, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    leave_timesheet_task_id = fields.Many2one(
        comodel_name="project.task",
        string="Time Off Task",
        domain="[('project_id', '=', internal_project_id)]",
    )

    def _create_internal_project_task(self):
        projects = super()._create_internal_project_task()
        for project in projects:
            company = project.company_id
            company = company.with_company(company)
            if not company.leave_timesheet_task_id:
                task = (
                    company.env["project.task"]
                    .sudo()
                    .create(
                        {
                            "name": _("Time Off"),
                            "project_id": company.internal_project_id.id,
                            "active": True,
                            "company_id": company.id,
                        }
                    )
                )
                _debug.lifecycle(
                    "leave_timesheet_task_created",
                    company=company,
                    project=company.internal_project_id,
                    task=task,
                )
                company.write(
                    {
                        "leave_timesheet_task_id": task.id,
                    }
                )
        return projects
