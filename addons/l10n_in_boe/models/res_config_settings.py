from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # BOE settings
    l10n_in_boe_feature = fields.Boolean(
        related='company_id.l10n_in_boe_feature',
        readonly=False,
        string="Bill of Entry",
    )
