import base64

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7

from odoo import _, models
from odoo.exceptions import UserError


class Certificate(models.Model):
    _inherit = 'certificate.certificate'

    def _decode_certificate_for_be_dmfa_xml(self, message):
        if not isinstance(message, bytes):
            message = message.encode('utf-8')

        if not self.is_valid:
            raise UserError(self.loading_error or _("This certificate is not valid, its validity has expired."))
        if not self.private_key_id:
            raise UserError(_("No private key linked to the certificate, it is required to sign documents."))

        cert = x509.load_pem_x509_certificate(base64.b64decode(self.pem_certificate))
        key = serialization.load_pem_private_key(base64.b64decode(self.private_key_id.pem_key), None)
        options = [
            pkcs7.PKCS7Options.DetachedSignature,
        ]
        signature = pkcs7.PKCS7SignatureBuilder().set_data(
            message
        ).add_signer(
            cert, key, hashes.SHA256()
        ).sign(
            serialization.Encoding.PEM, options
        )
        # Remove -----BEGIN PKCS7-----, -----END PKCS7----- and final new line
        signature = (b'\r\n').join(signature.split(b'\n')[1:-2]) + b'\r\n'
        return signature
