from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pl_edi_offline_certificate = fields.Many2one(
        related='company_id.l10n_pl_edi_offline_certificate',
        readonly=False,
    )
