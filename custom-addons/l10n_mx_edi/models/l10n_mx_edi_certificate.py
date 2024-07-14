# -*- coding: utf-8 -*-

import base64
import logging
import ssl
from cryptography.hazmat.primitives import serialization
from datetime import datetime
from lxml import etree
from pytz import timezone

from odoo import _, api, fields, models, tools
from odoo.addons.account.tools.certificate import crypto_load_certificate
from odoo.exceptions import ValidationError, UserError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

try:
    from OpenSSL import crypto
except ImportError:
    _logger.warning('OpenSSL library not found. If you plan to use l10n_mx_edi, please install the library from https://pypi.python.org/pypi/pyOpenSSL')


class Certificate(models.Model):
    _name = 'l10n_mx_edi.certificate'
    _description = 'SAT Digital Sail'
    _order = "date_start desc, id desc"

    content = fields.Binary(
        string='Certificate',
        help='Certificate in .cer format',
        required=True,
        attachment=False,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        ondelete='cascade',
    )
    key = fields.Binary(
        string='Certificate Key',
        help='Certificate Key in .key format',
        required=True,
        attachment=False,
    )
    password = fields.Char(
        string='Certificate Password',
        help='Password for the Certificate Key',
        required=True,
    )
    serial_number = fields.Char(
        string='Serial number',
        help='The serial number to add to electronic documents',
        readonly=True,
        index=True,
    )
    date_start = fields.Datetime(
        string='Available date',
        help='The date on which the certificate starts to be valid',
        readonly=True,
    )
    date_end = fields.Datetime(
        string='Expiration date',
        help='The date on which the certificate expires',
        readonly=True,
    )

    @tools.ormcache('content')
    def _get_pem_cer(self, content):
        '''Get the current content in PEM format
        '''
        self.ensure_one()
        return ssl.DER_cert_to_PEM_cert(base64.decodebytes(content)).encode('UTF-8')

    @tools.ormcache('key', 'password')
    def _get_pem_key(self, key, password):
        '''Get the current key in PEM format
        '''
        self.ensure_one()
        private_key = serialization.load_der_private_key(base64.b64decode(key), password.encode())
        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

    @api.model
    def _get_timezone(self):
        """ Get the timezone to consider for the CFDI. """
        return timezone('America/Mexico_City')

    def _get_data(self):
        '''Return the content (b64 encoded) and the certificate decrypted
        '''
        self.ensure_one()
        cer_pem = self._get_pem_cer(self.content)
        certificate = crypto_load_certificate(cer_pem)
        for to_del in ['\n', ssl.PEM_HEADER, ssl.PEM_FOOTER]:
            cer_pem = cer_pem.replace(to_del.encode('UTF-8'), b'')
        return cer_pem, certificate

    def _get_valid_certificate(self):
        '''Search for a valid certificate that is available and not expired. '''
        tz = self._get_timezone()
        now = datetime.now(tz)
        for record in self:
            date_start = tz.localize(record.date_start)
            date_end = tz.localize(record.date_end)
            if date_start <= now <= date_end:
                return record
        return None

    def _get_encrypted_cadena(self, cadena):
        '''Encrypt the cadena using the private key.
        '''
        self.ensure_one()
        key_pem = self._get_pem_key(self.key, self.password)
        private_key = crypto.load_privatekey(crypto.FILETYPE_PEM, bytes(key_pem))
        encrypt = 'sha256WithRSAEncryption'
        cadena_crypted = crypto.sign(private_key, bytes(cadena.encode()), encrypt)
        return base64.b64encode(cadena_crypted)

    @api.model
    def _get_cadena_chain(self, xml_tree, xslt_path):
        """ Use the provided XSLT document to generate a pipe-delimited string
        :param xml_tree: the source lxml document
        :param xslt_path: Path to the XSLT document
        :return: string
        """
        cadena_transformer = etree.parse(tools.file_open(xslt_path))
        return str(etree.XSLT(cadena_transformer)(xml_tree))

    @api.constrains('content', 'key', 'password')
    def _check_credentials(self):
        '''Check the validity of content/key/password and fill the fields
        with the certificate values.
        '''
        tz = self._get_timezone()
        now = datetime.now(tz)
        date_format = '%Y%m%d%H%M%SZ'
        for record in self:
            # Try to decrypt the certificate
            try:
                certificate = record._get_data()[1]
                before = tz.localize(datetime.strptime(certificate.get_notBefore().decode("utf-8"), date_format))
                after = tz.localize(datetime.strptime(certificate.get_notAfter().decode("utf-8"), date_format))
                serial_number = certificate.get_serial_number()
            except UserError as exc_orm:  # ;-)
                raise exc_orm
            except Exception as e:
                raise ValidationError(_('The certificate content is invalid %s.', e))
            # Assign extracted values from the certificate
            record.serial_number = ('%x' % serial_number)[1::2]
            record.date_start = before.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            record.date_end = after.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            if now > after:
                raise ValidationError(_('The certificate is expired since %s', record.date_end))
            # Check the pair key/password
            try:
                key_pem = self._get_pem_key(self.key, self.password)
                crypto.load_privatekey(crypto.FILETYPE_PEM, key_pem)
            except Exception:
                raise ValidationError(_('The certificate key and/or password is/are invalid.'))
