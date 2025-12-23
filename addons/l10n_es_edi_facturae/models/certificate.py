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
        issuer_key_priority = {
            'CN': 0,
            'OU': 1,
            'O': 2,
            'C': 3,
        }
        items = [rdn.rfc4514_string() for rdn in cert.issuer.rdns]
        sorted_items = sorted(items, key=lambda item_string: issuer_key_priority.get(item_string.split('=', 1)[0], 99))
        return ", ".join(sorted_items)
