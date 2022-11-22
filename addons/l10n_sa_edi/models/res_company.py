import re
import json
from base64 import b64encode
from odoo import models, fields, api, service
from cryptography import x509
from cryptography.x509 import ObjectIdentifier
from cryptography.x509.oid import NameOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import Encoding, load_pem_private_key
from cryptography.hazmat.primitives.asymmetric import ec

CERT_TEMPLATE_NAME = b'\x0c\x12ZATCA-Code-Signing'


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_sa_organization_unit = fields.Char("Organization Unit", copy=False,
                                            help="The branch name for taxpayers. In case of VAT Groups, this field "
                                                 "should contain the 10-digit TIN number of the individual group "
                                                 "member whose device is being onboarded")

    l10n_sa_serial_number = fields.Char("Serial Number", copy=False,
                                        help="The serial number of the Taxpayer solution unit. Provided by ZATCA")

    l10n_sa_private_key = fields.Binary(attachment=False, groups="base.group_erp_manager", copy=False,
                                        compute="_l10n_sa_compute_private_key", store=True,
                                        help="The private key used to generate the CSR and obtain certificates")

    l10n_sa_production_env = fields.Boolean("Production", default=False, copy=False,
                                            help="Specifies if the system should use the Production API")

    l10n_sa_edi_building_number = fields.Char(compute='_compute_address', inverse='_l10n_sa_edi_inverse_building_number')
    l10n_sa_edi_plot_identification = fields.Char(compute='_compute_address', inverse='_l10n_sa_edi_inverse_plot_identification')
    l10n_sa_edi_neighborhood = fields.Char(compute='_compute_address', inverse='_l10n_sa_edi_inverse_neighborhood')

    def _get_company_address_field_names(self):
        """ Override to add ZATCA specific address fields """
        return super()._get_company_address_field_names() + \
               ['l10n_sa_edi_building_number', 'l10n_sa_edi_plot_identification', 'l10n_sa_edi_neighborhood']

    def _l10n_sa_edi_inverse_building_number(self):
        for company in self:
            company.partner_id.l10n_sa_edi_building_number = company.l10n_sa_edi_building_number

    def _l10n_sa_edi_inverse_plot_identification(self):
        for company in self:
            company.partner_id.l10n_sa_edi_plot_identification = company.l10n_sa_edi_plot_identification

    def _l10n_sa_edi_inverse_neighborhood(self):
        for company in self:
            company.partner_id.l10n_sa_edi_neighborhood = company.l10n_sa_edi_neighborhood

    def _l10n_sa_compute_private_key(self):
        """
            Compute a private key for each company that will be used to generate certificate signing requests (CSR)
            in order to receive X509 certificates from the ZATCA APIs and sign EDI documents

            -   public_exponent=65537 is a default value that should be used most of the time, as per the documentation
                of cryptography.
            -   key_size=2048 is considered a reasonable default key size, as per the documentation of cryptography.

            See https://cryptography.io/en/latest/hazmat/primitives/asymmetric/rsa/
        """
        for company in self:
            private_key = ec.generate_private_key(ec.SECP256K1, default_backend())
            company.l10n_sa_private_key = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            )

    def _l10n_sa_generate_company_csr(self):
        """
            Generate a ZATCA compliant CSR request that will be sent to the Compliance API in order to get back
            a signed X509 certifi
        :return:
        """
        self.ensure_one()

        version_info = service.common.exp_version()
        builder = x509.CertificateSigningRequestBuilder()
        subject_names = (
            # Country Name
            (NameOID.COUNTRY_NAME, self.country_id.code),
            # Organization Unit Name
            (NameOID.ORGANIZATIONAL_UNIT_NAME, self.l10n_sa_organization_unit),
            # Organization Name
            (NameOID.ORGANIZATION_NAME, self.name),
            # Subject Common Name
            (NameOID.COMMON_NAME, self.name),
            # Organization Identifier
            (ObjectIdentifier('2.5.4.97'), self.vat),
            # State/Province Name
            (NameOID.STATE_OR_PROVINCE_NAME, self.state_id.name),
            # Locality Name
            (NameOID.LOCALITY_NAME, self.city),
        )
        # The CertificateSigningRequestBuilder instances are immutable, which is why everytime we modify one,
        # we have to assign it back to itself to keep track of the changes
        builder = builder.subject_name(x509.Name([
            x509.NameAttribute(n[0], u'%s' % n[1]) for n in subject_names
        ]))

        x509_alt_names_extension = x509.SubjectAlternativeName([
            x509.DirectoryName(x509.Name([
                # EGS Serial Number. Manufacturer or Solution Provider Name, Model or Version and Serial Number.
                # To be written in the following format: "1-... |2-... |3-..."
                x509.NameAttribute(ObjectIdentifier('2.5.4.4'), '1-Odoo|2-%s|3-%s' % (
                    version_info['server_version_info'][0], self.l10n_sa_serial_number)),
                # Organisation Identifier (UID)
                x509.NameAttribute(NameOID.USER_ID, self.vat),
                # Invoice Type. 4-digit numerical input using 0 & 1 mapped to “TSCZ” where:
                #   -   0: False/Not supported, 1: True/Supported
                #   -   T: Tax Invoice (Standard), S: Simplified Invoice, C & Z will be used in the future and should
                #       always be 0
                #   For example: 1100 would mean the Solution will be generating Standard and Simplified invoices.
                # We can assume Odoo-powered EGS solutions will always generate both Standard & Simplified invoices
                x509.NameAttribute(NameOID.TITLE, '1100'),
                # Location
                x509.NameAttribute(ObjectIdentifier('2.5.4.26'), self.street),
                # Industry
                x509.NameAttribute(ObjectIdentifier('2.5.4.15'), self.partner_id.industry_id.name or 'Other'),
            ]))
        ])

        x509_extensions = (
            # Add Certificate template name extension
            (x509.UnrecognizedExtension(ObjectIdentifier('1.3.6.1.4.1.311.20.2'), CERT_TEMPLATE_NAME), False),
            # Add alternative names extension
            (x509_alt_names_extension, False)
        )

        for ext in x509_extensions:
            builder = builder.add_extension(ext[0], critical=ext[1])

        private_key = load_pem_private_key(self.l10n_sa_private_key, password=None, backend=default_backend())
        request = builder.sign(private_key, hashes.SHA256(), default_backend())
        return b64encode(request.public_bytes(Encoding.PEM)).decode()

    def _l10n_sa_check_vat_tin(self):
        """
            Check company VAT TIN according to ZATCA specifications: The VAT number should start and begin with a '3'
            and be 15 digits long
        """
        self.ensure_one()
        return bool(self.vat and re.match(r'^3[0-9]{13}3$', self.vat))

    def _l10n_sa_check_organization_unit(self):
        """
            Check company Organization Unit according to ZATCA specifications
        """
        self.ensure_one()
        if self._l10n_sa_check_vat_tin() and self.vat[10] == '1':
            return bool(self.l10n_sa_organization_unit and re.match(r'^[0-9]{10}$', self.l10n_sa_organization_unit))
        return bool(self.l10n_sa_organization_unit)
