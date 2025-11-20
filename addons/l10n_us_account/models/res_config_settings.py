from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_l10n_us_direct_deposit = fields.Boolean("U.S. Direct Deposit (via Wise)")
