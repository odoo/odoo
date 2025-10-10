from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pl_edi_mode = fields.Selection(
        [('test', 'Test'), ('prod', 'Official')],
        string="KSeF Environment",
    )
    l10n_pl_edi_certificate = fields.Binary(
        string="KSeF Certificate & Private Key",
        attachment=True,
        help="Upload your single .pem file containing both your public certificate and unencrypted private key."
    )

    l10n_pl_access_token = fields.Char(string="KSeF Token", readonly=True, copy=False)
    l10n_pl_refresh_token = fields.Char(string="KSeF Token Expiration", readonly=True, copy=False)
