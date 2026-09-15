from odoo import _, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_fr_reference_leave_type = fields.Many2one(
        comodel_name="hr.leave.type",
        string="Company Paid Time Off Type",
    )

    def _get_fr_reference_leave_type(self):
        self.check_singleton()
        if not self.l10n_fr_reference_leave_type:
            _debug.logic(
                "fr_reference_leave_type_missing",
                reason="not_configured",
                company=self,
            )
            raise ValidationError(
                _("You must first define a reference time off type for the company.")
            )
        return self.l10n_fr_reference_leave_type
