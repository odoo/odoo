# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64decode, b64encode
from uuid import uuid4

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import NameOID
from lxml import etree
from odoo import api, fields, models, tools
from odoo.addons.account.tools.certificate import load_key_and_certificates
from odoo.addons.l10n_ec_edi.models.xml_utils import (
    NS_MAP, bytes_as_block, calculate_references_digests,
    cleanup_xml_signature, fill_signature, int_as_bytes)
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
from odoo.tools.xml_utils import cleanup_xml_node


class L10nEcCertificate(models.Model):
    _name = 'l10n_ec_edi.certificate'
    _description = 'Digital Certificate'

    name = fields.Char(string="Name", compute='_compute_l10n_ec_metadata')
    file_name = fields.Char("File Name", readonly=True)
    content = fields.Binary("Certificate", required=True)
    password = fields.Char("Password", required=True)
    active = fields.Boolean("Active", default=True)
    company_id = fields.Many2one('res.company', "Company", required=True, default=lambda self: self.env.company)

    # Fields constrained by content/password
    date_start = fields.Date(string="Emission Date", readonly=True, compute='_compute_l10n_ec_metadata')
    date_end = fields.Date(string="Expiration Date", readonly=True, compute='_compute_l10n_ec_metadata')
    subject_common_name = fields.Char(string="Subject Common Name", readonly=True, compute='_compute_l10n_ec_metadata')

    @tools.ormcache('self.content', 'self.password')
    def _load_certificate(self):
        self.ensure_one()
        content = self.with_context(bin_size=False).content or self.content
        try:
            _private_key, certificate = load_key_and_certificates(
                b64decode(content),
                self.password.encode(),
            )
            return certificate
        except Exception:
            raise ValidationError(_("Error loading certificate %s, check that password is correct and file type is p12", self.display_name))

    @api.depends('content', 'password')
    def _compute_l10n_ec_metadata(self):
        for record in self:
            if not (record.content and record.password):
                record.date_start = False
                record.date_end = False
                record.subject_common_name = False
                record.name = ''
            else:
                # Try to decrypt the certificate
                cert = record._load_certificate()
                # Compute dependent fields
                record.date_start = cert.not_valid_before
                record.date_end = cert.not_valid_after
                record.subject_common_name = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
                record.name = "{subject_common_name} - {date_end}".format_map(record)

    def _action_sign(self, xml_node_or_string):
        self.ensure_one()

        # Signature rendering: prepare reference identifiers
        signature_id = "Signature{}".format(uuid4())
        qweb_values = {
            'signature_id': signature_id,
            'signature_property_id': '{}-SignedPropertiesID{}'.format(signature_id, uuid4()),
            'certificate_id': 'Certificate{}'.format(uuid4()),
            'reference_uri': 'Reference-ID-{}'.format(uuid4()),
            'signed_properties_id': 'SignedPropertiesID{}'.format(uuid4())
        }

        # Load private key and certificates
        private_key, public_cert = load_key_and_certificates(
            b64decode(self.with_context(bin_size=False).content),  # without bin_size=False, size is returned instead of content
            self.password.encode(),
        )

        # Signature rendering: prepare certificate values
        public_key = public_cert.public_key()
        qweb_values.update({
            'sig_certif_digest': b64encode(public_cert.fingerprint(hashes.SHA1())).decode(),
            'x509_certificate': bytes_as_block(public_cert.public_bytes(encoding=serialization.Encoding.DER)),
            'rsa_modulus': bytes_as_block(int_as_bytes(public_key.public_numbers().n)),
            'rsa_exponent': bytes_as_block(int_as_bytes(public_key.public_numbers().e)),
            'x509_issuer_description': public_cert.issuer.rfc4514_string(),
            'x509_serial_number': public_cert.serial_number,
        })

        # Parse document, append rendered signature and process references
        doc = cleanup_xml_node(xml_node_or_string)
        signature_str = self.env['ir.qweb']._render('l10n_ec_edi.ec_edi_signature', qweb_values)
        signature = cleanup_xml_signature(signature_str)
        doc.append(signature)
        calculate_references_digests(signature.find('SignedInfo', namespaces=NS_MAP), base_uri='#comprobante')

        # Sign (writes into SignatureValue)
        fill_signature(signature, private_key)

        return etree.tostring(doc, encoding='unicode')
