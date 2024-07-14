# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import ssl
from base64 import b64decode, b64encode
from copy import deepcopy
from cryptography.hazmat.primitives import serialization
from lxml import etree
from pytz import timezone
from datetime import datetime
from OpenSSL import crypto

from odoo import _, api, fields, models, tools
from odoo.addons.account.tools.certificate import load_key_and_certificates
from odoo.exceptions import ValidationError


class Certificate(models.Model):
    _name = 'l10n_pe_edi.certificate'
    _description = 'Sunat Digital Certificate'
    _order = 'date_start desc, id desc'
    _rec_name = 'serial_number'

    content = fields.Binary(string="Certificate", required=True, help="PFX Certificate")
    password = fields.Char(help="Passphrase for the PFX certificate")
    serial_number = fields.Char(readonly=True, index=True, help="The serial number to add to electronic documents")
    date_start = fields.Datetime(readonly=True, help="The date on which the certificate starts to be valid")
    date_end = fields.Datetime(readonly=True, help="The date on which the certificate expires")
    company_id = fields.Many2one(comodel_name='res.company', required=True, default=lambda self: self.env.company)

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def _get_pe_current_datetime(self):
        """Get the current datetime with the Peruvian timezone. """
        peruvian_tz = timezone('America/Lima')
        return datetime.now(peruvian_tz)

    @tools.ormcache('self.content', 'self.password')
    def _decode_certificate(self):
        """Return the content (DER encoded) and the certificate decrypted based in the point 3.1 from the RS 097-2012
        http://www.vauxoo.com/r/manualdeautorizacion#page=21
        """
        self.ensure_one()
        private_key, certificate = load_key_and_certificates(b64decode(self.content), self.password.encode())
        pem_certificate = certificate.public_bytes(serialization.Encoding.PEM)
        pem_private_key = private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())

        # Cleanup pem_content.
        for to_clean in ('\n', ssl.PEM_HEADER, ssl.PEM_FOOTER):
            pem_certificate = pem_certificate.replace(to_clean.encode('UTF-8'), b'')

        return pem_certificate, pem_private_key, certificate

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        certificates = super().create(vals_list)

        peruvian_tz = timezone('America/Lima')
        peruvian_dt = self._get_pe_current_datetime()
        date_format = '%Y%m%d%H%M%SZ'
        for certificate in certificates:
            try:
                dummy, dummy, certif = certificate._decode_certificate()
                cert_date_start = peruvian_tz.localize(certif.not_valid_before, date_format)
                cert_date_end = peruvian_tz.localize(certif.not_valid_after, date_format)
                serial_number = certif.serial_number
            except:
                raise ValidationError(_('There has been a problem with the certificate, some usual problems can be:\n'
                                        '- The password given or the certificate are not valid.\n'
                                        '- The certificate content is invalid.'))
            # Assign extracted values from the certificate
            certificate.write({
                'serial_number': ('%x' % serial_number)[1::2],
                'date_start': fields.Datetime.to_string(cert_date_start),
                'date_end': fields.Datetime.to_string(cert_date_end),
            })
            if peruvian_dt > cert_date_end:
                raise ValidationError(_('The certificate is expired since %s', certificate.date_end))
        return certificates

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _sign(self, edi_tree):
        self.ensure_one()
        pem_certificate, pem_private_key, dummy = self._decode_certificate()
        namespaces = {'ds': 'http://www.w3.org/2000/09/xmldsig#'}

        edi_tree_copy = deepcopy(edi_tree)
        signature_element = edi_tree_copy.xpath('.//ds:Signature', namespaces=namespaces)[0]
        signature_element.getparent().remove(signature_element)

        edi_tree_c14n_str = etree.tostring(edi_tree_copy, method='c14n', exclusive=True, with_comments=False)
        digest_b64 = b64encode(hashlib.new('sha1', edi_tree_c14n_str).digest())
        signature_str = self.env['ir.qweb']._render(
            'l10n_pe_edi.ubl_pe_21_signature_template',
            {'digest_value': digest_b64.decode()}
        )

        # Eliminate all non useful spaces and new lines in the stream
        signature_str = signature_str.replace('\n', '').replace('  ', '')

        signature_tree = etree.fromstring(signature_str)
        signed_info_element = signature_tree.xpath('.//ds:SignedInfo', namespaces=namespaces)[0]
        signature = etree.tostring(signed_info_element, method='c14n', exclusive=True, with_comments=False)
        private_pem_key = crypto.load_privatekey(crypto.FILETYPE_PEM, pem_private_key)
        signature_b64_hash = b64encode(crypto.sign(private_pem_key, signature, 'sha1'))

        signature_tree.xpath('.//ds:SignatureValue', namespaces=namespaces)[0].text = signature_b64_hash
        signature_tree.xpath('.//ds:X509Certificate', namespaces=namespaces)[0].text = pem_certificate
        signed_edi_tree = deepcopy(edi_tree)
        signature_element = signed_edi_tree.xpath('.//ds:Signature', namespaces=namespaces)[0]
        for child_element in signature_tree:
            signature_element.append(child_element)
        return signed_edi_tree
