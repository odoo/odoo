from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_gcc_dual_language_receipt = fields.Boolean(related='pos_config_id.l10n_gcc_dual_language_receipt', readonly=False)
