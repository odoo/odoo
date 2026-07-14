import base64

from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from odoo import fields, models
from odoo.exceptions import UserError


class Certificate(models.Model):
    _inherit = 'certificate.certificate'

    scope = fields.Selection(
        selection_add=[
            ('fiscalization', 'Fiscalization')
        ],
    )

    def _l10n_hr_get_certificate_info(self):
        """Return cert content and issuer info used in XML-DSig KeyInfo."""
        self.ensure_one()

        if not self.is_valid:
            raise UserError(self.loading_error or self.env._("This certificate is not valid, its validity has expired."))
        if not self.private_key_id:
            raise UserError(self.env._("No private key linked to the certificate, it is required to sign documents."))

        cert_data = bytes(self.with_context(bin_size=False).pem_certificate)
        cert = x509.load_pem_x509_certificate(cert_data)
        cert_str = cert_data.decode('utf-8')
        cert_lines = cert_str.split('\n')
        cert_content = ''.join(
            line for line in cert_lines
            if not line.startswith('-----BEGIN')
            and not line.startswith('-----END')
            and line.strip()
        )

        issuer = cert.issuer
        attr_mapping = {
            'commonName': 'CN',
            'organizationName': 'O',
            'countryName': 'C',
            'organizationalUnitName': 'OU',
            'stateOrProvinceName': 'ST',
            'localityName': 'L',
            'emailAddress': 'E'
        }

        issuer_parts = []
        for attr in issuer:
            attr_name = attr.oid._name
            abbrev = attr_mapping.get(attr_name, attr_name)
            issuer_parts.append(f"{abbrev}={attr.value}")

        issuer_name = ", ".join(reversed(issuer_parts))
        serial_number = str(cert.serial_number)
        return {
            'certificate': cert_content,
            'issuer_name': issuer_name,
            'serial_number': serial_number
        }

    def _l10n_hr_sign_data(self, data_to_sign):
        """Sign canonicalized bytes using RSA-SHA256 and return base64 string."""
        self.ensure_one()

        if not self.is_valid:
            raise UserError(self.loading_error or self.env._("This certificate is not valid, its validity has expired."))
        if not self.private_key_id:
            raise UserError(self.env._("No private key linked to the certificate, it is required to sign documents."))

        try:
            private_key_data = bytes(self.with_context(bin_size=False).private_key_id.pem_key)
            is_encrypted = b"ENCRYPTED" in private_key_data

            if is_encrypted:
                private_key = serialization.load_pem_private_key(
                    private_key_data,
                    password=self.private_key_id.password.encode('utf-8')
                )
            else:
                private_key = serialization.load_pem_private_key(private_key_data, password=None)

            if not isinstance(private_key, rsa.RSAPrivateKey):
                raise UserError(self.env._("The certificate's private key must be an RSA key for signing"))

            signature = private_key.sign(data_to_sign, padding.PKCS1v15(), hashes.SHA256())
            return base64.b64encode(signature).decode('utf-8')
        except Exception as e:  # noqa: BLE001
            raise UserError(self.env._("Error signing data: %s", e))

    def _parse_chain_missing_ca_vals(self, vals):
        content = vals.get('content')
        if isinstance(content, dict):
            nested_content = content.get('content')
            if nested_content is not None:
                vals['content'] = nested_content
        return super()._parse_chain_missing_ca_vals(vals)
