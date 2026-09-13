from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_fr_reference_leave_type = fields.Many2one(
        comodel_name="hr.leave.type",
        related="company_id.l10n_fr_reference_leave_type",
        readonly=False,
    )
