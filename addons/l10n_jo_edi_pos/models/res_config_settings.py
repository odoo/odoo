from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_jo_edi_pos_enabled = fields.Boolean(related="company_id.l10n_jo_edi_pos_enabled", readonly=False)
