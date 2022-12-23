import json
from odoo import models, api
from base64 import b64decode
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_der_x509_certificate


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _l10n_sa_get_qr_code(self, journal_id, unsigned_xml, x509_cert, signature):
        """
            Override to add certificate signature to QR code values for Simplified invoices
        """
        qr_string = super()._l10n_sa_get_qr_code(journal_id, unsigned_xml, x509_cert, signature)
        if qr_string and self._context.get('from_pos'):
            x509_certificate = load_der_x509_certificate(b64decode(x509_cert), default_backend())
            qr_string += self._l10n_sa_get_qr_code_encoding(9, x509_certificate.signature)
        return qr_string