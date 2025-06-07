import base64

from cryptography import x509

from odoo import fields, models


class Certificate(models.Model):
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

        # The 'Organizational Unit' field is optional
        issuer = f"CN={rfc4514_attr.pop('CN')}, "
        if 'OU' in rfc4514_attr:
            issuer += f"OU={rfc4514_attr.pop('OU')}, "
        issuer += f"O={rfc4514_attr.pop('O')}, C={rfc4514_attr.pop('C')}"

        # Add remaining certificate fields (not all certificates have other fields)
        return issuer + "".join([f", {key}={value}" for key, value in rfc4514_attr.items()])
