from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _default_project_time_mode_id(self):
        return self.env.ref("uom.product_uom_hour", raise_if_not_found=False)

    @api.model
    def _default_timesheet_encode_uom_id(self):
        return self.env.ref("uom.product_uom_hour", raise_if_not_found=False)

    project_time_mode_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Project Time Unit",
        default=_default_project_time_mode_id,
        help="This will set the unit of measure used in projects and tasks.\n"
        "If you use the timesheet linked to projects, don't "
        "forget to setup the right unit of measure in your employees.",
    )
    timesheet_encode_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Timesheet Encoding Unit",
        default=_default_timesheet_encode_uom_id,
    )
    internal_project_id = fields.Many2one(
        comodel_name="project.project",
        domain=[("is_template", "=", False)],
        help="Default project value for timesheet generated from time off type.",
    )

    @api.constrains("internal_project_id")
    def _check_internal_project_id_company(self):
        if self.filtered(
            lambda company: (
                company.internal_project_id
                and company.internal_project_id.sudo().company_id != company
            )
        ):
            _debug.logic("internal_project_company_mismatch", companies=self)
            raise ValidationError(
                _("The Internal Project of a company should be in that company.")
            )

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
        step_ids = [(4, step_ids_ref.id)] if step_ids_ref else []
        for company in self:
            company = company.with_company(company)
            results += [
                {
                    "name": _("Internal"),
                    "allow_timesheets": True,
                    "company_id": company.id,
                    "workflow_step_ids": step_ids,
                    "task_ids": [
                        (
                            0,
                            0,
                            {
                                "name": name,
                                "company_id": company.id,
                            },
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
            company.internal_project_id = projects_by_company.get(company.id, False)
        return project_ids
