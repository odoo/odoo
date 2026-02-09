import base64

from cryptography import x509
from cryptography.x509 import ObjectIdentifier
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization

from odoo import _, api, models, service
from odoo.exceptions import UserError

CERT_TEMPLATE_NAME = {
    'prod': b'\x0c\x12ZATCA-Code-Signing',
    'sandbox': b'\x13\x15PREZATCA-Code-Signing',
    'preprod': b'\x13\x15PREZATCA-Code-Signing',
}

MAX_ALLOWED_CSR_VALUE_LENGTH = 64


class CertificateCertificate(models.Model):
    _inherit = 'certificate.certificate'

    def _l10n_sa_get_issuer_name(self):
        self.ensure_one()
        cert = x509.load_pem_x509_certificate(base64.b64decode(self.pem_certificate))
        return ', '.join([s.rfc4514_string() for s in cert.issuer.rdns[::-1]])

    @api.model
    def _l10n_sa_get_csr_vals(self, journal):
        company_id = journal.company_id
        parent_company_id = journal.company_id.parent_id
        version_info = service.common.exp_version()
        return {
            "country_name": {
                "value": company_id.country_id.code,
                "name": _("Country Name"),
            },
            "org_unit_name": {
                "value": company_id.name if parent_company_id else company_id.vat[:10],
                "name": _("Company Name"),
            },
            "org_name": {
                "value": parent_company_id.name if parent_company_id else company_id.name,
                "name": _("Parent Company Name") if parent_company_id else _("Company Name"),
            },
            "common_name": {
                "value": f"{journal.code}-{journal.name}-{company_id.name}",
                "name": _("Common Name"),
            },
            "org_id": {
                "value": parent_company_id.vat if parent_company_id else company_id.vat,
                "name": _("Parent Company VAT") if parent_company_id else _("Company VAT"),
            },
            "state_name": {
                "value": company_id.state_id.name,
                "name": _("State/Province Name"),
            },
            "locality_name": {
                "value": company_id.city,
                "name": _("Locality Name"),
            },
            "egs_serial": {
                "value": f"1-Odoo|2-{version_info['server_serie']}|3-{journal.id}",
                "name": _("Journal Serial Number"),
            },
            "org_uid": {
                "value": company_id.vat,
                "name": _("Company VAT"),
            },
            "invoice_type": {
                "value": company_id._l10n_sa_get_csr_invoice_type(),
                "name": _("Invoice Type"),
            },
            "location": {
                "value": company_id.street,
                "name": _("Street"),
            },
            "industry": {
                "value": company_id.partner_id.industry_id.name or _("Other"),
                "name": _("Partner Industry Name"),
            },
            "cert_tmp": {
                "value": CERT_TEMPLATE_NAME[company_id.l10n_sa_api_mode],
                "name": _("Certificate Template Name"),
            },
        }

    @api.model
    def _l10n_sa_validate_csr_vals(self, journal):
        error_fields = set()
        for data in self._l10n_sa_get_csr_vals(journal).values():
            if len(str(data['value'])) > MAX_ALLOWED_CSR_VALUE_LENGTH:
                error_fields.add(data['name'])
        if error_fields:
            company_fields = [_("Company Name"), _("Parent Company Name")]
            company_msg = _("<br/><br/>Once the journal is onboarded, please update the company name to match the one listed on the VAT Registration Certificate.") if any(field in error_fields for field in company_fields) else ""
            raise UserError(_(
                "Please make sure the following fields are shorter than %(max_length)d characters: %(error_fields_msg)s",
                max_length=MAX_ALLOWED_CSR_VALUE_LENGTH,
                error_fields_msg=" <br/>- " + " <br/>- ".join(error_fields) + company_msg
            ))

    @api.model
    def _l10n_sa_get_csr_str(self, journal):
        """
            Return a string representation of a ZATCA compliant CSR that will be sent to the Compliance API in order to get back
            a signed X509 certificate
        """
        if not journal:
            return

        builder = x509.CertificateSigningRequestBuilder()
        self._l10n_sa_validate_csr_vals(journal)
        csr_vals = {key: data['value'] for key, data in self._l10n_sa_get_csr_vals(journal).items()}
        subject_names = (
            # Country Name
            (NameOID.COUNTRY_NAME, csr_vals['country_name']),
            # Organization Unit Name
            (NameOID.ORGANIZATIONAL_UNIT_NAME, csr_vals['org_unit_name']),
            # Organization Name
            (NameOID.ORGANIZATION_NAME, csr_vals['org_name']),
            # Subject Common Name
            (NameOID.COMMON_NAME, csr_vals['common_name']),
            # Organization Identifier
            (ObjectIdentifier('2.5.4.97'), csr_vals['org_id']),
            # State/Province Name
            (NameOID.STATE_OR_PROVINCE_NAME, csr_vals['state_name']),
            # Locality Name
            (NameOID.LOCALITY_NAME, csr_vals['locality_name']),
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
                x509.NameAttribute(ObjectIdentifier('2.5.4.4'), csr_vals['egs_serial']),
                # Organisation Identifier (UID)
                x509.NameAttribute(NameOID.USER_ID, csr_vals['org_uid']),
                # Invoice Type. 4-digit numerical input using 0 & 1
                x509.NameAttribute(NameOID.TITLE, csr_vals['invoice_type']),
                # Location
                x509.NameAttribute(ObjectIdentifier('2.5.4.26'), csr_vals['location']),
                # Industry
                x509.NameAttribute(ObjectIdentifier('2.5.4.15'), csr_vals['industry']),
            ]))
        ])

        x509_extensions = (
            # Add Certificate template name extension
            (x509.UnrecognizedExtension(ObjectIdentifier('1.3.6.1.4.1.311.20.2'),
                                        csr_vals['cert_tmp']), False),
            # Add alternative names extension
            (x509_alt_names_extension, False),
        )

        for ext in x509_extensions:
            builder = builder.add_extension(ext[0], critical=ext[1])

        private_key = serialization.load_pem_private_key(base64.b64decode(journal.company_id.l10n_sa_private_key_id.pem_key), password=None)
        request = builder.sign(private_key, hashes.SHA256())

        return base64.b64encode(request.public_bytes(serialization.Encoding.PEM)).decode()
