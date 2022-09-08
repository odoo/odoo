from odoo import models, fields, _
from odoo.exceptions import UserError
from .account_edi_proxy_auth import OdooEdiProxyAuth

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.fernet import Fernet
from psycopg2 import OperationalError
import requests
import uuid
import base64
import logging


_logger = logging.getLogger(__name__)


DEFAULT_SERVER_URL = 'https://l10n-it-edi.api.odoo.com'
DEFAULT_TEST_SERVER_URL = 'https://iap-services-test.odoo.com'
TIMEOUT = 30


class AccountEdiProxyError(Exception):

    def __init__(self, code, message=False):
        self.code = code
        self.message = message
        super().__init__(message or code)


class AccountEdiProxyClientUser(models.Model):
    """Represents a user of the proxy for an electronic invoicing format.
    An edi_proxy_user has a unique identification on a specific format (for example, the vat for Peppol) which
    allows to identify him when receiving a document addressed to him. It is linked to a specific company on a specific
    Odoo database.
    It also owns a key with which each file should be decrypted with (the proxy encrypt all the files with the public key).
    """
    _name = 'account_edi_proxy_client.user'
    _description = 'Account EDI proxy user'

    active = fields.Boolean(default=True)
    id_client = fields.Char(required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    edi_format_id = fields.Many2one('account.edi.format', required=True)
    edi_format_code = fields.Char(related='edi_format_id.code', readonly=True)
    edi_identification = fields.Char(required=True, help="The unique id that identifies this user for on the edi format, typically the vat")
    private_key = fields.Binary(required=True, attachment=False, groups="base.group_system", help="The key to encrypt all the user's data")
    refresh_token = fields.Char(groups="base.group_system")

    _sql_constraints = [
        ('unique_id_client', 'unique(id_client)', 'This id_client is already used on another user.'),
        ('unique_edi_identification_per_format', 'unique(edi_identification, edi_format_id)', 'This edi identification is already assigned to a user'),
    ]

    def _get_demo_state(self):
        demo_state = self.env['ir.config_parameter'].sudo().get_param('account_edi_proxy_client.demo', False)
        return 'prod' if demo_state in ['prod', False] else 'test' if demo_state == 'test' else 'demo'

    def _get_server_url(self):
        return DEFAULT_TEST_SERVER_URL if self._get_demo_state() == 'test' else self.env['ir.config_parameter'].sudo().get_param('account_edi_proxy_client.edi_server_url', DEFAULT_SERVER_URL)

    def _make_request(self, url, params=False):
        ''' Make a request to proxy and handle the generic elements of the reponse (errors, new refresh token).
        '''
        payload = {
            'jsonrpc': '2.0',
            'method': 'call',
            'params': params or {},
            'id': uuid.uuid4().hex,
        }

        if self._get_demo_state() == 'demo':
            # Last barrier : in case the demo mode is not handled by the caller, we block access.
            raise Exception("Can't access the proxy in demo mode")

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=TIMEOUT,
                headers={'content-type': 'application/json'},
                auth=OdooEdiProxyAuth(user=self)).json()
        except (ValueError, requests.exceptions.ConnectionError, requests.exceptions.MissingSchema, requests.exceptions.Timeout, requests.exceptions.HTTPError):
            raise AccountEdiProxyError('connection_error',
                _('The url that this service requested returned an error. The url it tried to contact was %s', url))

        if 'error' in response:
            message = _('The url that this service requested returned an error. The url it tried to contact was %s. %s', url, response['error']['message'])
            if response['error']['code'] == 404:
                message = _('The url that this service tried to contact does not exist. The url was %r', url)
            raise AccountEdiProxyError('connection_error', message)

        proxy_error = response['result'].pop('proxy_error', False)
        if proxy_error:
            error_code = proxy_error['code']
            if error_code == 'refresh_token_expired':
                self._renew_token()
                if not self.env.context.get('test_skip_commit'):
                    self.env.cr.commit() # We do not want to lose it if in the _make_request below something goes wrong
                return self._make_request(url, params)
            if error_code == 'no_such_user':
                # This error is also raised if the user didn't exchange data and someone else claimed the edi_identificaiton.
                self.sudo().active = False
            raise AccountEdiProxyError(error_code, proxy_error['message'] or False)

        return response['result']

    def _register_proxy_user(self, company, edi_format, edi_identification):
        ''' Generate the public_key/private_key that will be used to encrypt the file, send a request to the proxy
        to register the user with the public key and create the user with the private key.

        :param company: the company of the user.
        :param edi_identification: The unique ID that identifies this user on this edi network and to which the files will be addressed.
                                   Typically the vat.
        '''
        # public_exponent=65537 is a default value that should be used most of the time, as per the documentation of cryptography.
        # key_size=2048 is considered a reasonable default key size, as per the documentation of cryptography.
        # see https://cryptography.io/en/latest/hazmat/primitives/asymmetric/rsa/
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        if self._get_demo_state() == 'demo':
            # simulate registration
            response = {'id_client': f'demo{company.id}', 'refresh_token': 'demo'}
        else:
            try:
                # b64encode returns a bytestring, we need it as a string
                response = self._make_request(self._get_server_url() + '/iap/account_edi/1/create_user', params={
                    'dbuuid': company.env['ir.config_parameter'].get_param('database.uuid'),
                    'company_id': company.id,
                    'edi_format_code': edi_format.code,
                    'edi_identification': edi_identification,
                    'public_key': base64.b64encode(public_pem).decode()
                })
            except AccountEdiProxyError as e:
                raise UserError(e.message)
            if 'error' in response:
                raise UserError(response['error'])

        self.create({
            'id_client': response['id_client'],
            'company_id': company.id,
            'edi_format_id': edi_format.id,
            'edi_identification': edi_identification,
            'private_key': base64.b64encode(private_pem),
            'refresh_token': response['refresh_token'],
        })

    def _renew_token(self):
        ''' Request the proxy for a new refresh token.

        Request to the proxy should be made with a refresh token that expire after 24h to avoid
        that multiple database use the same credentials. When receiving an error for an expired refresh_token,
        This method makes a request to get a new refresh token.
        '''
        try:
            with self.env.cr.savepoint(flush=False):
                self.env.cr.execute('SELECT * FROM account_edi_proxy_client_user WHERE id IN %s FOR UPDATE NOWAIT', [tuple(self.ids)])
        except OperationalError as e:
            if e.pgcode == '55P03':
                return
            raise e
        response = self._make_request(self._get_server_url() + '/iap/account_edi/1/renew_token')
        if 'error' in response:
            # can happen if the database was duplicated and the refresh_token was refreshed by the other database.
            # we don't want two database to be able to query the proxy with the same user
            # because it could lead to not inconsistent data.
            _logger.error(response['error'])
        self.sudo().refresh_token = response['refresh_token']

    def _decrypt_data(self, data, symmetric_key):
        ''' Decrypt the data. Note that the data is encrypted with a symmetric key, which is encrypted with an asymmetric key.
        We must therefore decrypt the symmetric key.

        :param data:            The data to decrypt.
        :param symmetric_key:   The symmetric_key encrypted with self.private_key.public_key()
        '''
        private_key = serialization.load_pem_private_key(
            base64.b64decode(self.sudo().private_key),
            password=None,
            backend=default_backend()
        )
        key = private_key.decrypt(
            base64.b64decode(symmetric_key),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        f = Fernet(key)
        return f.decrypt(base64.b64decode(data))

    def _neutralize(self):
        super()._neutralize()
        self.env.flush_all()
        self.env.invalidate_all()
        self.env.cr.execute("""
            INSERT INTO ir_config_parameter(key, value)
            VALUES ('account_edi_proxy_client.demo', true)
            ON CONFLICT (key) DO UPDATE SET value = true
        """)
