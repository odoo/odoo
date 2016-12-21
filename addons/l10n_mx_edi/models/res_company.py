# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

import base64
import ssl
import os
import tempfile
import logging
import re

from contextlib import closing
from StringIO import StringIO
from OpenSSL import crypto
from datetime import datetime

_logger = logging.getLogger(__name__)

CER_TO_PEM_CMD = 'openssl x509 -in %s -inform der -outform pem -out %s'
KEY_TO_PEM_CMD = 'openssl pkcs8 -in %s -inform der -outform pem -out %s -passin file:%s'

def unlink_temporary_files(temporary_files):
    for temporary_file in temporary_files:
        try:
            os.unlink(temporary_file)
        except (OSError, IOError):
            _logger.error('Error when trying to remove file %s' % temporary_file)

def convert_CER_to_PEM(cer):
    cer_file_fd, cer_file_path = tempfile.mkstemp(suffix='.cer', prefix='edi.mx.tmp.')
    with closing(os.fdopen(cer_file_fd, 'w')) as cer_file:
        cer_file.write(cer)
    cerpem_file_fd, cerpem_file_path = tempfile.mkstemp(suffix='.pem', prefix='edi.mx.tmp.')

    os.popen(CER_TO_PEM_CMD % (cer_file_path, cerpem_file_path))
    with open(cerpem_file_path, 'r') as f:
        cer_pem = f.read()
    
    unlink_temporary_files([cer_file_path, cerpem_file_path])
    return cer_pem

def convert_key_CER_to_PEM(key, password):
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

class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_mx_edi_cer = fields.Binary(
        string='Certificate',
        help='Certificate in der format')
    l10n_mx_edi_cer_key = fields.Binary(
        string='Certificate Key',
        help='Certificate Key in der format')
    l10n_mx_edi_cer_password = fields.Char(
        string='Certificate Password',
        help='Password for the Certificate Key')
    l10n_mx_edi_pac = fields.Selection(
        selection=[('solfact', 'Solucion Factible')], 
        string='PAC',
        help='The PAC that will sign/cancel the invoices')
    l10n_mx_edi_pac_test_env = fields.Boolean(
        string='PAC test environment',
        help='Enable the usage of test credentials',
        default=True)
    l10n_mx_edi_pac_username = fields.Char(
        string='PAC username',
        help='The username used to request the seal from the PAC')
    l10n_mx_edi_pac_password = fields.Char(
        string='PAC password',
        help='The password used to request the seal from the PAC')

    @api.model
    def l10n_mx_edi_cer_as_pem(self):
        return convert_CER_to_PEM(base64.decodestring(self.l10n_mx_edi_cer))

    @api.model
    def l10n_mx_edi_cer_key_as_pem(self):
        return convert_key_CER_to_PEM(
            base64.decodestring(self.l10n_mx_edi_cer_key), self.l10n_mx_edi_cer_password)

    @api.model
    def l10n_mx_edi_load_certificate(self):
        self.ensure_one()
        cer_pem = self.l10n_mx_edi_cer_as_pem()
        certificate = crypto.load_certificate(crypto.FILETYPE_PEM, cer_pem)
        return cer_pem, certificate

    @api.model
    def l10n_mx_edi_create_encrypted_cadena(self, cadena):
        self.ensure_one()
        key_pem = self.l10n_mx_edi_cer_key_as_pem()
        private_key = crypto.load_privatekey(crypto.FILETYPE_PEM, key_pem)
        cadena_crypted = crypto.sign(private_key, cadena, 'sha1')
        return base64.encodestring(cadena_crypted).replace('\n', '').replace('\r', '')