from odoo import _, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_fr_reference_leave_type = fields.Many2one(
        comodel_name="hr.leave.type",
        string="Company Paid Time Off Type",
    )

    def _get_fr_reference_leave_type(self):
        self.check_singleton()
        if not self.l10n_fr_reference_leave_type:
            raise ValidationError(
                _("You must first define a reference time off type for the company.")
            )
        return self.l10n_fr_reference_leave_type
