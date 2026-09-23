from odoo import Command, _, api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    hr_timesheet_config_id = fields.Many2one(
        comodel_name="hr_timesheet.config",
        compute="_compute_hr_timesheet_config_id",
        search="_search_hr_timesheet_config_id",
    )

    def _search_hr_timesheet_config_id(self, operator, value):
        return self._search_config_link("hr_timesheet.config", operator, value)

    def _compute_hr_timesheet_config_id(self):
        configs = self.env["hr_timesheet.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.hr_timesheet_config_id = by_company.get(company.id, False)

    @api.model_create_multi
    def create(self, vals_list):
        company = super().create(vals_list)
        company.sudo()._create_internal_project_task()
        return company

    def _create_internal_project_task(self):
        results = []
        step_ids_ref = self.env.ref(
            "hr_timesheet.internal_project_default_stage", raise_if_not_found=False
        )
        step_ids = [Command.link(step_ids_ref.id)] if step_ids_ref else []
        for company in self:
            company = company.with_company(company)
            results += [
                {
                    "name": _("Internal"),
                    "allow_timesheets": True,
                    "company_id": company.id,
                    "workflow_step_ids": step_ids,
                    "task_ids": [
                        Command.create(
                            {
                                "name": name,
                                "company_id": company.id,
                            }
                        )
                        for name in [_("Training"), _("Meeting")]
                    ],
                }
            ]
        project_ids = self.env["project.project"].create(results)
        _debug.lifecycle(
            "internal_projects_created", companies=self, projects=project_ids
        )
        projects_by_company = {
            project.company_id.id: project for project in project_ids
        }
        for company in self:
            company.hr_timesheet_config_id.internal_project_id = (
                projects_by_company.get(company.id, False)
            )
        return project_ids
