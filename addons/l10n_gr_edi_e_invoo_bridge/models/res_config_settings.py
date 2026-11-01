from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_gr_edi_methodoos_api_token = fields.Char(
        related='company_id.l10n_gr_edi_methodoos_api_token',
        readonly=False,
    )
