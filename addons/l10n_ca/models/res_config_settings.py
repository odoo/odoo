from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_l10n_ca_payment_cpa005 = fields.Boolean(
        string="Canadian CPA005 Payments (EFT/PAD)",
    )
