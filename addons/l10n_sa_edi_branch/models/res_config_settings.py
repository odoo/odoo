from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_sa_use_branch_crn = fields.Boolean(related='company_id.l10n_sa_use_branch_crn', readonly=False)
