# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import hashlib
import json

import pytz

from asn1crypto import cms, core, x509, algos, tsp

from odoo import models, fields, _
from odoo.exceptions import ValidationError


class L10n_Eg_EdiThumbDrive(models.Model):
    _name = 'l10n_eg_edi.thumb.drive'
    _description = 'Thumb drive used to sign invoices in Egypt'

    user_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    certificate = fields.Binary('ETA Certificate')
    pin = fields.Char('ETA USB Pin', required=True)
    access_token = fields.Char(required=True)

    _user_drive_uniq = models.Constraint(
        'unique (user_id, company_id)',
        'You can only have one thumb drive per user per company!',
    )

    def action_sign_invoices(self, invoice_ids):
        self.ensure_one()
        sign_host = self._get_host()

        to_sign_dict = dict()
        for invoice_id in invoice_ids:
            eta_invoice = json.loads(base64.b64decode(invoice_id.l10n_eg_eta_json_doc_file))['request']
            signed_attrs = self._generate_signed_attrs__(eta_invoice, invoice_id.l10n_eg_signing_time)
            to_sign_dict[invoice_id.id] = base64.b64encode(signed_attrs.dump()).decode()

        return {
            'type': 'ir.actions.client',
            'tag': 'action_post_sign_invoice',
            'params': {
                'sign_host': sign_host,
                'access_token': self.access_token,
                'pin': self.pin,
                'drive_id': self.id,
                'invoices': json.dumps(to_sign_dict)
            }
        }

    def action_set_certificate_from_usb(self):
        self.ensure_one()
        sign_host = self._get_host()

        return {
            'type': 'ir.actions.client',
            'tag': 'action_get_drive_certificate',
            'params': {
                'sign_host': sign_host,
                'access_token': self.access_token,
                'pin': self.pin,
                'drive_id': self.id
            }
        }

    def set_certificate(self, certificate):
        """ This is called from the browser to set the certificate"""
        self.ensure_one()
        self.certificate = certificate.encode()
        return True

    def set_signature_data(self, invoices):
        """ This is called from the browser with the signed data from the local server """
        invoices = json.loads(invoices)
        for key, value in invoices.items():
            invoice_id = self.env['account.move'].browse(int(key))
            eta_invoice_json = json.loads(base64.b64decode(invoice_id.l10n_eg_eta_json_doc_file))

            signature = self._generate_cades_bes_signature(eta_invoice_json['request'], invoice_id.l10n_eg_signing_time,
                                                           base64.b64decode(value))

            eta_invoice_json['request']['signatures'] = [{'signatureType': 'I', 'value': signature}]
            invoice_id.l10n_eg_eta_json_doc_file = base64.b64encode(json.dumps(eta_invoice_json).encode())
            invoice_id.l10n_eg_is_signed = True
        return True

    def _get_host(self):
        # It should be on the loopback address or with a fully valid https host
        # in order to be an exception to the mixed-content restrictions
        sign_host = self.env['ir.config_parameter'].sudo().get_param('l10n_eg_eta.sign.host', 'http://localhost:8069')
        if not sign_host:
            raise ValidationError(_('Please define the host of sign tool.'))
        return sign_host

    def _serialize_for_signing(self, eta_inv):
        if not isinstance(eta_inv, dict):
            return json.dumps(str(eta_inv), ensure_ascii=False)

        canonical_str = []
        for key, value in eta_inv.items():
            if not isinstance(value, list):
                canonical_str.append(json.dumps(key, ensure_ascii=False).upper())
                canonical_str.append(self._serialize_for_signing(value))
            else:
                canonical_str.append(json.dumps(key, ensure_ascii=False).upper())
                for elem in value:
                    canonical_str.append(json.dumps(key, ensure_ascii=False).upper())
                    canonical_str.append(self._serialize_for_signing(elem))
        return ''.join(canonical_str)

    def _generate_signed_attrs__(self, eta_invoice, signing_time):
        cert = x509.Certificate.load(base64.b64decode(self.certificate))
        data = hashlib.sha256(self._serialize_for_signing(eta_invoice).encode()).digest()
        return cms.CMSAttributes([
            cms.CMSAttribute({
                'type': cms.CMSAttributeType('content_type'),
                'values': ('digested_data',),
            }),
            cms.CMSAttribute({
                'type': cms.CMSAttributeType('message_digest'),
                'values': (data,),
            }),
            cms.CMSAttribute({
                'type': tsp.CMSAttributeType('signing_certificate_v2'),
                'values': ({
                               'certs': (tsp.ESSCertIDv2({
                                   'hash_algorithm': algos.DigestAlgorithm({'algorithm': 'sha256'}),
                                   'cert_hash': hashlib.sha256(cert.dump()).digest()
                               }),)
                           },),
            }),
            cms.CMSAttribute({
                'type': cms.CMSAttributeType('signing_time'),
                'values': (
                cms.Time({'utc_time': core.UTCTime(signing_time.replace(tzinfo=pytz.UTC))}),)
            }),
        ])

    def _generate_signer_info__(self, eta_invoice, signing_time, signature=False):
        cert = x509.Certificate.load(base64.b64decode(self.certificate))
        signer_info = {
            'version': 'v1',
            'sid': cms.SignerIdentifier({
                'issuer_and_serial_number': cms.IssuerAndSerialNumber({
                    'issuer': cert.issuer,
                    'serial_number': cert.serial_number,
                }),
            }),
            'digest_algorithm': algos.DigestAlgorithm({'algorithm': 'sha256'}),
            'signature_algorithm': algos.SignedDigestAlgorithm({
                'algorithm': 'sha256_rsa'
            }),
            'signed_attrs': self._generate_signed_attrs__(eta_invoice, signing_time)
        }
        if signature:
            signer_info['signature'] = signature
        return signer_info

    def _generate_cades_bes_signature(self, eta_invoice, signing_time, signature):
        cert = x509.Certificate.load(base64.b64decode(self.certificate))
        signed_data = {
            'version': 'v3',
            'digest_algorithms': cms.DigestAlgorithms((
                algos.DigestAlgorithm({'algorithm': 'sha256'}),
            )),
            'encap_content_info': {
                'content_type': 'digested_data',
            },
            'certificates': [cert],
            'signer_infos': [
                self._generate_signer_info__(eta_invoice, signing_time, signature),
            ],
        }
        content_info = cms.ContentInfo({'content_type': cms.ContentType('signed_data'), 'content': cms.SignedData(signed_data)})
        return base64.b64encode(content_info.dump()).decode()
