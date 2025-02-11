from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools import index_exists
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
    edi_identification = fields.Char(required=True, help="The unique id that identifies this user, typically the vat")
    private_key = fields.Binary(required=True, attachment=False, groups="base.group_system", help="The key to encrypt all the user's data")
    private_key_filename = fields.Char(compute='_compute_private_key_filename')
    refresh_token = fields.Char(groups="base.group_system")
    proxy_type = fields.Selection(selection=[], required=True)
    edi_mode = fields.Selection(
        selection=[
            ('prod', 'Production mode'),
            ('test', 'Test mode'),
            ('demo', 'Demo mode'),
        ],
        string='EDI operating mode',
    )

    _sql_constraints = [
        ('unique_id_client', 'unique(id_client)', 'This id_client is already used on another user.'),
        ('unique_active_edi_identification', '', 'This edi identification is already assigned to an active user'),
        ('unique_active_company_proxy', '', 'This company has an active user already created for this EDI type'),
    ]

    def _auto_init(self):
        super()._auto_init()
        if not index_exists(self.env.cr, 'account_edi_proxy_client_user_unique_active_edi_identification'):
            self.env.cr.execute("""
                CREATE UNIQUE INDEX account_edi_proxy_client_user_unique_active_edi_identification
                                 ON account_edi_proxy_client_user(edi_identification, proxy_type, edi_mode)
                              WHERE (active = True)
            """)
        if not index_exists(self.env.cr, 'account_edi_proxy_client_user_unique_active_company_proxy'):
            self.env.cr.execute("""
                CREATE UNIQUE INDEX account_edi_proxy_client_user_unique_active_company_proxy
                                 ON account_edi_proxy_client_user(company_id, proxy_type, edi_mode)
                              WHERE (active = True)
            """)

    def _compute_private_key_filename(self):
        for record in self:
            record.private_key_filename = f'{record.id_client}_{record.edi_identification}.key'

    def _get_proxy_urls(self):
        # To extend
        return {}

    def _get_server_url(self, proxy_type=None, edi_mode=None):
        proxy_type = proxy_type or self.proxy_type
        edi_mode = edi_mode or self.edi_mode
        proxy_urls = self._get_proxy_urls()
        # letting this traceback in case of a KeyError, as that would mean something's wrong with the code
        return proxy_urls[proxy_type][edi_mode]

    def _get_proxy_users(self, company, proxy_type):
        '''Returns proxy users associated with the given company and proxy type.
        '''
        return company.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == proxy_type)

    def _get_proxy_identification(self, company, proxy_type):
        '''Returns the key that will identify company uniquely
        within a specific proxy type and edi operating mode.
        or raises a UserError (if the user didn't fill the related field).
        TO OVERRIDE
        '''
        return False

    def _make_request(self, url, params=False):
        ''' Make a request to proxy and handle the generic elements of the reponse (errors, new refresh token).
        '''
        payload = {
            'jsonrpc': '2.0',
            'method': 'call',
            'params': params or {},
            'id': uuid.uuid4().hex,
        }

        # Last barrier : in case the demo mode is not handled by the caller, we block access.
        if self.edi_mode == 'demo':
            raise AccountEdiProxyError("block_demo_mode", "Can't access the proxy in demo mode")

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
                self.env.cr.commit() # We do not want to lose it if in the _make_request below something goes wrong
                return self._make_request(url, params)
            if error_code == 'no_such_user':
                # This error is also raised if the user didn't exchange data and someone else claimed the edi_identificaiton.
                self.sudo().active = False
            raise AccountEdiProxyError(error_code, proxy_error['message'] or False)

        return response['result']

    def _register_proxy_user(self, company, proxy_type, edi_mode):
        ''' Generate the public_key/private_key that will be used to encrypt the file, send a request to the proxy
        to register the user with the public key and create the user with the private key.

        :param company: the company of the user.
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
        edi_identification = self._get_proxy_identification(company, proxy_type)
        if edi_mode == 'demo':
            # simulate registration
            response = {'id_client': f'demo{company.id}{proxy_type}', 'refresh_token': 'demo'}
        else:
            try:
                # b64encode returns a bytestring, we need it as a string
                response = self._make_request(self._get_server_url(proxy_type, edi_mode) + '/iap/account_edi/2/create_user', params={
                    'dbuuid': company.env['ir.config_parameter'].get_param('database.uuid'),
                    'company_id': company.id,
                    'edi_identification': edi_identification,
                    'public_key': base64.b64encode(public_pem).decode(),
                    'proxy_type': proxy_type,
                })
            except AccountEdiProxyError as e:
                raise UserError(e.message)
            if 'error' in response:
                raise UserError(response['error'])

        return self.create({
            'id_client': response['id_client'],
            'company_id': company.id,
            'proxy_type': proxy_type,
            'edi_mode': edi_mode,
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
