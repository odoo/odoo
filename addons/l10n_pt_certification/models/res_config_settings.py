from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pt_at_ws_username = fields.Char(
        related='company_id.l10n_pt_at_ws_username',
        readonly=False,
    )
    l10n_pt_at_ws_password = fields.Char(
        related='company_id.l10n_pt_at_ws_password',
        readonly=False,
    )
    l10n_pt_at_ws_public_cert_id = fields.Many2one(
        related='company_id.l10n_pt_at_ws_public_cert_id',
        comodel_name='certificate.certificate',
        readonly=False,
    )
