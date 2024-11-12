import base64

from cryptography import x509

from odoo import fields, models


class CertificateCertificate(models.Model):
    _inherit = 'certificate.certificate'

    scope = fields.Selection(
        selection_add=[
            ('facturae', 'Facturae')
        ],
    )

    def _l10n_es_edi_facturae_get_issuer(self):
        self.ensure_one()

        cert = x509.load_pem_x509_certificate(base64.b64decode(self.pem_certificate))

        rfc4514_attr = dict(element.rfc4514_string().split("=", 1) for element in cert.issuer.rdns)
        return f"CN={rfc4514_attr['CN']}, OU={rfc4514_attr['OU']}, O={rfc4514_attr['O']}, C={rfc4514_attr['C']}"
