from odoo import fields, models


class CertificateCertificate(models.Model):
    _inherit = 'certificate.certificate'

    scope = fields.Selection(
        selection_add=[
            ('sii', 'SII')
        ],
    )
