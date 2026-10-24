from odoo import fields, models


class CertificateCertificate(models.Model):
    _inherit = 'certificate.certificate'

    scope = fields.Selection(
        selection_add=[
            ('at_series', 'AT Series Webservice'),
        ],
    )
