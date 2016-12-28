# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import logging
import base64
import tempfile
import os
import pytz
import ssl

from contextlib import closing
from OpenSSL import crypto
from pytz import timezone
from datetime import datetime
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

CER_TO_PEM_CMD = 'openssl x509 -in %s -inform der -outform pem -out %s'
KEY_TO_PEM_CMD = 'openssl pkcs8 -in %s -inform der -outform pem -out %s -passin file:%s'

CERTIFICATE_DATE_FORMAT = '%Y%m%d%H%M%SZ'

def unlink_temporary_files(temporary_files):
    for temporary_file in temporary_files:
        try:
            os.unlink(temporary_file)
        except (OSError, IOError):
            _logger.error('Error when trying to remove file %s' % temporary_file)

def convert_cer_to_pem(cer):
    cer_file_fd, cer_file_path = tempfile.mkstemp(suffix='.cer', prefix='edi.mx.tmp.')
    with closing(os.fdopen(cer_file_fd, 'w')) as cer_file:
        cer_file.write(cer)
    cerpem_file_fd, cerpem_file_path = tempfile.mkstemp(suffix='.pem', prefix='edi.mx.tmp.')

    os.popen(CER_TO_PEM_CMD % (cer_file_path, cerpem_file_path))
    with open(cerpem_file_path, 'r') as f:
        cer_pem = f.read()
    
    unlink_temporary_files([cer_file_path, cerpem_file_path])
    return cer_pem

def convert_key_cer_to_pem(key, password):
    key_file_fd, key_file_path = tempfile.mkstemp(suffix='.key', prefix='edi.mx.tmp.')
    with closing(os.fdopen(key_file_fd, 'w')) as key_file:
        key_file.write(key)
    pwd_file_fd, pwd_file_path = tempfile.mkstemp(suffix='.txt', prefix='edi.mx.tmp.')
    with closing(os.fdopen(pwd_file_fd, 'w')) as pwd_file:
        pwd_file.write(password)
    keypem_file_fd, keypem_file_path = tempfile.mkstemp(suffix='.key', prefix='edi.mx.tmp.')

    os.popen(KEY_TO_PEM_CMD % (key_file_path, keypem_file_path, pwd_file_path))
    with open(keypem_file_path, 'r') as f:
        key_pem = f.read()

    unlink_temporary_files([key_file_path, keypem_file_path, pwd_file_path])
    return key_pem

def str_to_datetime(dt_str, tz=timezone('America/Mexico_City')):
    return tz.localize(fields.Datetime.from_string(dt_str))


class Certificate(models.Model):
    _name = 'l10n_mx_edi.certificate'
    _description = 'SAT Digital Sail'
    _order = "available_date desc, id desc"

    content = fields.Binary(
        string='Certificate',
        help='Certificate in der format',
        required=True,
        stored=True)
    key = fields.Binary(
        string='Certificate Key',
        help='Certificate Key in der format',
        required=True,
        stored=True)
    password = fields.Char(
        string='Certificate Password',
        help='Password for the Certificate Key',
        required=True,
        stored=True)
    data = fields.Binary(
        string='Data',
        help='The content to add to electronic documents',
        readonly=True)
    serial_number = fields.Char(
        string='Serial number',
        help='The serial number to add to electronic documents',
        readonly=True,
        required=True,
        index=True)
    available_date = fields.Datetime(
        string='Available date',
        help='The date on which the certificate will be valid',
        readonly=True,
        required=True)
    expiration_date = fields.Datetime(
        string='Expiration date',
        help='The date on which the certificate will be expired',
        readonly=True,
        required=True)

    @api.multi
    def get_mx_current_datetime(self):
        '''Get the current datetime with the Mexican timezone.
        '''
        default_tz = self._context.get('tz')
        default_tz = timezone(default_tz) if default_tz else pytz.UTC
        mexican_tz = timezone('America/Mexico_City')
        current_dt = default_tz.localize(datetime.now())
        mexican_dt = current_dt.astimezone(mexican_tz)
        return mexican_dt

    @api.multi
    def get_valid_certificate(self):
        '''Search for a valid certificate that is available and not expired.
        '''
        mexican_dt = self.get_mx_current_datetime()
        for record in self:
            available_date = str_to_datetime(record.available_date)
            expiration_date = str_to_datetime(record.expiration_date)
            if mexican_dt >= available_date and mexican_dt <= expiration_date:
                return record
        return None

    @api.multi
    def get_encrypted_cadena(self, cadena):
        '''Encrypt the cadena using the private key.
        '''
        self.ensure_one()
        key = base64.decodestring(self.key)
        key_pem = convert_key_cer_to_pem(key, self.password)
        private_key = crypto.load_privatekey(crypto.FILETYPE_PEM, key_pem)
        cadena_crypted = crypto.sign(private_key, cadena, 'sha1')
        return base64.encodestring(cadena_crypted).replace('\n', '').replace('\r', '')

    @api.multi
    @api.constrains('content', 'key', 'password')
    def _check_date_range(self):
        '''Check the validity of content/key/password and fill the fields
        with the certificate values.
        '''
        mexican_tz = timezone('America/Mexico_City')
        mexican_dt = self.get_mx_current_datetime()
        for record in self:
            try:
                cer = base64.decodestring(record.content)
                cer_pem = convert_cer_to_pem(cer)
                certificate = crypto.load_certificate(crypto.FILETYPE_PEM, cer_pem)
                before = mexican_tz.localize(
                    datetime.strptime(certificate.get_notBefore(), CERTIFICATE_DATE_FORMAT))
                after = mexican_tz.localize(
                    datetime.strptime(certificate.get_notAfter(), CERTIFICATE_DATE_FORMAT))
                serial_number = certificate.get_serial_number()
            except Exception as e:
                raise ValidationError(_('The certificate content is invalid.'))
            for to_del in ['\n', ssl.PEM_HEADER, ssl.PEM_FOOTER]:
                cer_pem = cer_pem.replace(to_del, '')
            record.data = base64.encodestring(cer_pem)
            record.serial_number = ('%x' % serial_number)[1::2]
            record.available_date = before.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            record.expiration_date = after.strftime(DEFAULT_SERVER_DATETIME_FORMAT)        
            if mexican_dt > after:
                raise ValidationError(_('The certificate is expired since %s') % record.expiration_date)
            try:
                key = base64.decodestring(record.key)
                key_pem = convert_key_cer_to_pem(key, record.password)
                private_key = crypto.load_privatekey(crypto.FILETYPE_PEM, key_pem)
            except Exception as e:
                raise ValidationError(_('The certificate key and/or password is/are invalid.'))