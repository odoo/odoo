from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrTimesheetConfig(models.Model):
    _name = "hr_timesheet.config"
    _description = "A company's hr timesheet configuration"
    _inherit = ["mixin.company.config"]

    project_time_mode_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Project Time Unit",
        default=lambda self: self._default_project_time_mode_id(),
        help="This will set the unit of measure used in projects and tasks.\n"
        "If you use the timesheet linked to projects, don't "
        "forget to setup the right unit of measure in your employees.",
    )
    timesheet_encode_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Timesheet Encoding Unit",
        default=lambda self: self._default_timesheet_encode_uom_id(),
    )
    internal_project_id = fields.Many2one(
        comodel_name="project.project",
        domain=[("is_template", "=", False)],
        help="Default project value for timesheet generated from time off type.",
    )

    @api.model
    def _default_project_time_mode_id(self):
        return self.env.ref("uom.product_uom_hour", raise_if_not_found=False)

    @api.model
    def _default_timesheet_encode_uom_id(self):
        return self.env.ref("uom.product_uom_hour", raise_if_not_found=False)

    @api.constrains("internal_project_id")
    def _check_internal_project_id_company(self):
        if self.filtered(
            lambda config: (
                config.internal_project_id
                and config.internal_project_id.sudo().company_id != config.company_id
            )
        ):
            _debug.logic("internal_project_company_mismatch", configs=self)
            raise ValidationError(
                self.env._(
                    "The Internal Project of a company should be in that company."
                )
            )
