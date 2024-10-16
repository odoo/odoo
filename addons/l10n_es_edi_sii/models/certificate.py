from odoo import fields, models
from odoo.addons import certificate


class CertificateCertificate(certificate.CertificateCertificate):

    scope = fields.Selection(
        selection_add=[
            ('sii', 'SII')
        ],
    )
