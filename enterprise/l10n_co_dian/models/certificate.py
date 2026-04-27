import base64

from cryptography import x509

from odoo import models


class Certificate(models.Model):
    _inherit = 'certificate.certificate'

    def _get_issuer_string(self):
        self.ensure_one()

        cert = x509.load_pem_x509_certificate(base64.b64decode(self.pem_certificate))
        return cert.issuer.rfc4514_string()
