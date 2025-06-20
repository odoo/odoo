from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pt_training_mode = fields.Boolean(string="Training Mode", related='company_id.l10n_pt_training_mode', readonly=False)
