# -*- coding: utf-8 -*-
import base64
import logging
import ssl

from datetime import datetime
from pytz import timezone

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, load_pem_private_key

from odoo import _, api, fields, models
from odoo.addons.account.tools.certificate import crypto_load_certificate, load_key_and_certificates
from odoo.exceptions import UserError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class Certificate(models.Model):
    _name = 'l10n_cl.certificate'
    _description = 'SII Digital Signature'
    _rec_name = 'signature_filename'
    _order = 'id desc'

    signature_filename = fields.Char('Signature File Name')
    signature_key_file = fields.Binary(string='Certificate Key', help='Certificate Key in PFX format', required=True)
    signature_pass_phrase = fields.Char(string='Certificate Passkey', help='Passphrase for the certificate key',
                                        copy=False, required=True)
    private_key = fields.Text(compute='_check_credentials', string='Private Key', store=True, copy=False,
                              groups='base.group_system')
    certificate = fields.Text(compute='_check_credentials', string='Certificate', store=True, copy=False)
    cert_expiration = fields.Datetime(
        compute='_check_credentials', string='Expiration date', help='The date on which the certificate expires',
        store=True)
    subject_serial_number = fields.Char(
        compute='_check_serial_number', string='Subject Serial Number', store=True, readonly=False, copy=False,
        help='This is the document of the owner of this certificate.'
             'Some certificates does not provide this number and you must fill it by hand')
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company.id, required=True, readonly=True)
    user_id = fields.Many2one('res.users', 'Certificate Owner',
                              help='If this certificate has an owner, he will be the only user authorized to use it, '
                                   'otherwise, the certificate will be shared with other users of the current company')
    last_token = fields.Char('Last Token')
    token_time = fields.Datetime('Token Time')
    l10n_cl_is_there_shared_certificate = fields.Boolean(related='company_id.l10n_cl_is_there_shared_certificate')

    def _get_data(self):
        """ Return the signature_key_file (b64 encoded) and the certificate decrypted """
        self.ensure_one()
        try:
            pkey, cert = load_key_and_certificates(base64.b64decode(self.with_context(bin_size=False).signature_key_file), self.signature_pass_phrase.encode())
        except Exception as error:
            raise UserError(error)
        cer_pem = cert.public_bytes(encoding=Encoding.PEM)
        cert = crypto_load_certificate(cer_pem)
        for to_del in ['\n', ssl.PEM_HEADER, ssl.PEM_FOOTER]:
            cer_pem = cer_pem.replace(to_del.encode('UTF-8'), b'')
        return cer_pem, cert, pkey.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())

    def _is_valid_certificate(self):
        """ Search for a valid certificate that is available and not expired. """
        chilean_current_dt = self.env['l10n_cl.edi.util']._get_cl_current_datetime()
        return len(self.filtered(lambda x: chilean_current_dt <= fields.Datetime.context_timestamp(
            x.with_context(tz='America/Santiago'), x.cert_expiration))) >= 1

    @api.depends('signature_key_file', 'signature_pass_phrase')
    def _check_serial_number(self):
        """
        This method is only for the readonly false compute
        """
        for record in self:
            if not record.signature_key_file or not record.signature_pass_phrase:
                continue
            try:
                certificate = record._get_data()
            except Exception as e:
                raise UserError(_('The certificate signature_key_file is invalid: %s.', e)) from e
            record.subject_serial_number = certificate[1].get_subject().serialNumber

    @api.depends('signature_key_file', 'signature_pass_phrase')
    def _check_credentials(self):
        """
        Check the validity of signature_key_file/key/signature_pass_phrase and fill the fields
        with the certificate values.
        """
        chilean_tz = timezone('America/Santiago')
        chilean_current_dt = self.env['l10n_cl.edi.util']._get_cl_current_datetime()
        date_format = '%Y%m%d%H%M%SZ'
        for record in self:
            if not record.signature_key_file or not record.signature_pass_phrase:
                continue
            try:
                certificate = record._get_data()
                cert_expiration = chilean_tz.localize(
                    datetime.strptime(certificate[1].get_notAfter().decode('utf-8'), date_format))
            except Exception as e:
                raise UserError(_('The certificate signature_key_file is invalid: %s.', e)) from e
            # Assign extracted values from the certificate
            record.cert_expiration = cert_expiration.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            record.certificate = certificate[0]
            record.private_key = certificate[2]
            if chilean_current_dt > cert_expiration:
                raise UserError(_('The certificate is expired since %s', record.cert_expiration))

    def _int_to_bytes(self, value, byteorder='big'):
        return value.to_bytes((value.bit_length() + 7) // 8, byteorder=byteorder)

    def _get_private_key_modulus(self):
        key = load_pem_private_key(self.private_key.encode('ascii'), password=None, backend=default_backend())
        return base64.b64encode(self._int_to_bytes(key.public_key().public_numbers().n)).decode('utf-8')

    def _get_private_key_exponent(self):
        key = load_pem_private_key(self.private_key.encode('ascii'), password=None, backend=default_backend())
        return base64.b64encode(self._int_to_bytes(key.public_key().public_numbers().e)).decode('utf-8')
