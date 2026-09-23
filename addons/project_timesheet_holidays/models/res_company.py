from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    project_timesheet_holidays_config_id = fields.Many2one(
        comodel_name="project_timesheet_holidays.config",
        compute="_compute_project_timesheet_holidays_config_id",
        search="_search_project_timesheet_holidays_config_id",
    )

    def _search_project_timesheet_holidays_config_id(self, operator, value):
        return self._search_config_link(
            "project_timesheet_holidays.config", operator, value
        )

    def _compute_project_timesheet_holidays_config_id(self):
        configs = self.env["project_timesheet_holidays.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.project_timesheet_holidays_config_id = by_company.get(
                company.id, False
            )

    def _create_internal_project_task(self):
        projects = super()._create_internal_project_task()
        for project in projects:
            company = project.company_id
            company = company.with_company(company)
            if not company.project_timesheet_holidays_config_id.leave_timesheet_task_id:
                task = (
                    company.env["project.task"]
                    .sudo()
                    .create(
                        {
                            "name": self.env._("Time Off"),
                            "project_id": company.hr_timesheet_config_id.internal_project_id.id,
                            "active": True,
                            "company_id": company.id,
                        }
                    )
                )
                _debug.lifecycle(
                    "leave_timesheet_task_created",
                    company=company,
                    project=company.hr_timesheet_config_id.internal_project_id,
                    task=task,
                )
                company.write(
                    {
                        "leave_timesheet_task_id": task.id,
                    }
                )
        return projects
