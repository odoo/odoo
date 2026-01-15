import base64

from cryptography import x509
from cryptography.x509 import ObjectIdentifier
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization

from odoo import api, models, service

CERT_TEMPLATE_NAME = {
    'prod': b'\x0c\x12ZATCA-Code-Signing',
    'sandbox': b'\x13\x15PREZATCA-Code-Signing',
    'preprod': b'\x13\x15PREZATCA-Code-Signing',
}


class CertificateCertificate(models.Model):
    _inherit = 'certificate.certificate'

    def _l10n_sa_get_issuer_name(self):
        self.ensure_one()
        cert = x509.load_pem_x509_certificate(base64.b64decode(self.pem_certificate))
        return ', '.join([s.rfc4514_string() for s in cert.issuer.rdns[::-1]])

    @api.model
    def _l10n_sa_get_csr_str(self, journal):
        """
            Return a string representation of a ZATCA compliant CSR that will be sent to the Compliance API in order to get back
            a signed X509 certificate
        """
        if not journal:
            return

        company_id = journal.company_id
        parent_company_id = journal.company_id.parent_id
        version_info = service.common.exp_version()
        builder = x509.CertificateSigningRequestBuilder()
        subject_names = (
            # Country Name
            (NameOID.COUNTRY_NAME, company_id.country_id.code),
            # Organization Unit Name
            (NameOID.ORGANIZATIONAL_UNIT_NAME, company_id.name if parent_company_id else company_id.vat[:10]),
            # Organization Name
            (NameOID.ORGANIZATION_NAME, parent_company_id.name if parent_company_id else company_id.name),
            # Subject Common Name
            (NameOID.COMMON_NAME, "%s-%s-%s" % (journal.code, journal.name, company_id.name)),
            # Organization Identifier
            (ObjectIdentifier('2.5.4.97'), parent_company_id.vat if parent_company_id else company_id.vat),
            # State/Province Name
            (NameOID.STATE_OR_PROVINCE_NAME, company_id.state_id.name),
            # Locality Name
            (NameOID.LOCALITY_NAME, company_id.city),
        )
        # The CertificateSigningRequestBuilder instances are immutable, which is why everytime we modify one,
        # we have to assign it back to itself to keep track of the changes
        builder = builder.subject_name(x509.Name([
            x509.NameAttribute(n[0], '%s' % n[1]) for n in subject_names
        ]))

        x509_alt_names_extension = x509.SubjectAlternativeName([
            x509.DirectoryName(x509.Name([
                # EGS Serial Number. Manufacturer or Solution Provider Name, Model or Version and Serial Number.
                # To be written in the following format: "1-... |2-... |3-..."
                x509.NameAttribute(ObjectIdentifier('2.5.4.4'), '1-Odoo|2-%s|3-%s' % (
                    version_info['server_serie'], journal.id)),
                # Organisation Identifier (UID)
                x509.NameAttribute(NameOID.USER_ID, company_id.vat),
                # Invoice Type. 4-digit numerical input using 0 & 1
                x509.NameAttribute(NameOID.TITLE, company_id._l10n_sa_get_csr_invoice_type()),
                # Location
                x509.NameAttribute(ObjectIdentifier('2.5.4.26'), company_id.street),
                # Industry
                x509.NameAttribute(ObjectIdentifier('2.5.4.15'), company_id.partner_id.industry_id.name or 'Other'),
            ]))
        ])

        x509_extensions = (
            # Add Certificate template name extension
            (x509.UnrecognizedExtension(ObjectIdentifier('1.3.6.1.4.1.311.20.2'),
                                        CERT_TEMPLATE_NAME[company_id.l10n_sa_api_mode]), False),
            # Add alternative names extension
            (x509_alt_names_extension, False),
        )

        for ext in x509_extensions:
            builder = builder.add_extension(ext[0], critical=ext[1])

        private_key = serialization.load_pem_private_key(base64.b64decode(company_id.l10n_sa_private_key_id.pem_key), password=None)
        request = builder.sign(private_key, hashes.SHA256())

        return base64.b64encode(request.public_bytes(serialization.Encoding.PEM)).decode()
