from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pl_edi_offline_next_send = fields.Datetime(copy=False)
    l10n_pl_edi_offline_certificate = fields.Many2one(
        'certificate.certificate',
        string="KSeF Offline Certificate",
        groups='base.group_system',
        help="KSeF type 2 certificate used exclusively to sign the certificate QR code on offline invoices.",
    )
