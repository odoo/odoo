import base64

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7

from odoo import _, api, models
from odoo.exceptions import UserError


class Certificate(models.Model):
    _inherit = 'certificate.certificate'

    @api.model
    def _l10n_ar_create_certificate_request(self, company_id):
        """ Create Certificate Request using an existing private key id. If none,
            it creates a private key first.
        """

        company = self.env['res.company'].browse(company_id)
        if not company:
            return

        private_key = serialization.load_pem_private_key(base64.b64decode(company.l10n_ar_afip_ws_key_id.pem_key), None)

        common_name = 'AFIP WS %s - %s' % (company._get_environment_type(), company.name)[:50]

        csr = x509.CertificateSigningRequestBuilder().subject_name(
            x509.Name([
                x509.NameAttribute(x509.NameOID.COUNTRY_NAME, company.partner_id.country_id.code),
                x509.NameAttribute(x509.NameOID.STATE_OR_PROVINCE_NAME, company.partner_id.state_id.name or ''),
                x509.NameAttribute(x509.NameOID.LOCALITY_NAME, company.partner_id.city),
                x509.NameAttribute(x509.NameOID.ORGANIZATION_NAME, company.name),
                x509.NameAttribute(x509.NameOID.COMMON_NAME, common_name),
                x509.NameAttribute(x509.NameOID.ORGANIZATIONAL_UNIT_NAME, 'IT'),
                x509.NameAttribute(x509.NameOID.SERIAL_NUMBER, 'CUIT %s' % company.partner_id.ensure_vat()),
                ])
            ).sign(private_key, hashes.SHA256())

        return csr.public_bytes(serialization.Encoding.PEM)

    def _l10n_ar_pkcs7_sign(self, message):
        self.ensure_one()

        if not self.is_valid:
            raise UserError(self.loading_error or _("This certificate is not valid, its validity has expired."))
        if not self.private_key_id:
            raise UserError(_("No private key linked to the certificate, it is required to sign documents."))

        if not isinstance(message, bytes):
            message = message.encode('utf-8')

        cert = x509.load_pem_x509_certificate(base64.b64decode(self.with_context(bin_size=False).pem_certificate))
        key = serialization.load_pem_private_key(base64.b64decode(self.with_context(bin_size=False).private_key_id.pem_key), None)
        options = [pkcs7.PKCS7Options.Binary]
        signature = pkcs7.PKCS7SignatureBuilder().set_data(
            message
        ).add_signer(
            cert, key, hashes.SHA256()
        ).sign(
            serialization.Encoding.DER, options
        )
        return signature
