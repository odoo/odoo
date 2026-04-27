import base64

from cryptography import x509

from odoo import models


class Certificate(models.Model):
    _inherit = 'certificate.certificate'

    def _l10n_ec_edi_get_issuer_rfc_string(self):
        self.ensure_one()

        cert = x509.load_pem_x509_certificate(base64.b64decode(self.pem_certificate))
        return cert.issuer.rfc4514_string()
