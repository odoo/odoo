from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrDepartureWizard(models.TransientModel):
    _inherit = "hr.departure.wizard"

    release_assets = fields.Boolean(
        string="Release Assets",
        default=True,
        help="End the custody of every asset the employees hold.",
    )

    def action_register_departure(self):
        action = super().action_register_departure()
        if self.release_assets:
            assignments = self.employee_ids._get_custody_assignments()
            _debug.pipeline(
                "departure_releases_assets",
                employees=self.employee_ids,
                assignments=assignments,
            )
            assignments._end()
        return action
