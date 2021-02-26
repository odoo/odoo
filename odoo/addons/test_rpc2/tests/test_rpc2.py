import base64
import secrets
import textwrap
import time

from http import HTTPStatus
from lxml import etree
from urllib.parse import urlparse

from freezegun import freeze_time

from odoo.tests.common import get_db_name, tagged, HttpCase, new_test_user
from odoo.tools import config, mute_logger, submap

from odoo.addons.auth_totp.models import totp
from odoo.addons.base.controllers.rpc2 import admin

CT_JSON = 'application/json; charset=utf-8'
CT_XML = 'text/xml; charset=utf-8'
HEADER_JSON = {'Content-Type': CT_JSON}
HEADER_XML = {'Content-Type': CT_XML}


def xmlrpc_req(method, params):
    return textwrap.dedent(f"""\
        <?xml version="1.0"?>
        <methodCall>
            <methodName>{method}</methodName>
            <params>
                {params}
            </params>
        </methodCall>
    """)

def xmlrpc_fault(code, string):
    return textwrap.dedent(f"""\
        <?xml version="1.0"?>
        <methodResponse>
            <fault>
                <value>
                    <struct>
                        <member>
                            <name>faultCode</name>
                            <value><int>{code}</int></value>
                        </member>
                        <member>
                            <name>faultString</name>
                            <value><string>{string}</string></value>
                        </member>
                    </struct>
                </value>
            </fault>
        </methodResponse>
    """)

def jsonrpc_req(method, params):
    return {
        "version": "2.0",
        "method": method,
        "params": params,
        "id": None
    }


@tagged('-at_install', 'post_install')
class TestRpc2(HttpCase):
    @mute_logger('odoo.http')
    def test_rpc2_unsupported_media_type(self):
        res = self.url_open('/RPC2', data={'method': 'version', 'params': []})
        self.assertEqual(res.status_code, HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        self.assertIn(CT_XML, res.headers.get('Accept', ''))
        self.assertIn(CT_JSON, res.headers.get('Accept', ''))
        self.assertIn("mime type not supported", res.text)

    def test_rpc2_db(self):
        db = get_db_name()

        with self.subTest(dblist=[]), self.nodb():
            res = self.opener.post(
                self.base_url() + '/RPC2',
                json=jsonrpc_req('version', []))
            self.assertEqual(res.status_code, HTTPStatus.OK,
                "The rpc2 controllers should always be accessible.")

        dblist = [db, f'definitely_not_{db}']
        with self.subTest(dblist=dblist), self.multidb(dblist):
            res = self.opener.post(
                self.base_url() + f'/RPC2?db={get_db_name()}',
                json=jsonrpc_req('system.noop', []),
                auth=('admin', 'admin'))
            self.assertEqual(res.status_code, HTTPStatus.OK,
                "Accessing its own db in multi-db mode works")

        dblist = [f'definitely_not_{db}1', f'definitely_not_{db}2']
        with self.subTest(dblist=dblist), self.multidb(dblist):
            res = self.opener.post(
                self.base_url() + f'/RPC2?db={db}',
                json=jsonrpc_req('system.noop', []),
                auth=('admin', 'admin'))
            self.assertEqual(res.status_code, HTTPStatus.NOT_FOUND)

    def test_rpc2_auth_admin(self):
        version_func = admin._functions['version']
        assert not version_func.admin_only
        version_func.admin_only = True
        self.addCleanup(version_func.__setattr__, 'admin_only', False)

        with self.subTest(missing='auth header'):
            res = self.opener.post(
                f'{self.base_url()}/RPC2',
                json=jsonrpc_req('version', []))
            self.assertEqual(res.status_code, HTTPStatus.UNAUTHORIZED)
            self.assertEqual(res.headers.get('WWW-Authenticate'), 'Basic realm="Odoo-RPC"')

        with self.subTest(bad='password'):
            res = self.opener.post(
                f'{self.base_url()}/RPC2',
                json=jsonrpc_req('version', []),
                auth=('', 'bad password')
            )
            self.assertEqual(res.status_code, HTTPStatus.FORBIDDEN)

        with self.subTest(good='password'):
            res = self.opener.post(
                f'{self.base_url()}/RPC2',
                json=jsonrpc_req('version', []),
                auth=('', config['admin_passwd'])
            )
            self.assertEqual(res.status_code, HTTPStatus.OK)

    @mute_logger('odoo.addons.base.controllers.rpc')
    def test_rpc2_auth_model(self):
        db = get_db_name()

        with self.subTest(missing='auth header'):
            res = self.opener.post(
                f'{self.base_url()}/RPC2?db={db}',
                json=jsonrpc_req('system.noop', []))
            self.assertEqual(res.status_code, HTTPStatus.UNAUTHORIZED)
            self.assertEqual(res.headers.get('WWW-Authenticate'), 'Basic realm="Odoo-RPC"')

        with self.subTest(bad='user'):
            res = self.opener.post(
                f'{self.base_url()}/RPC2?db={db}',
                json=jsonrpc_req('system.noop', []),
                auth=('baduser', 'admin'))
            self.assertEqual(res.status_code, HTTPStatus.FORBIDDEN)

        with self.subTest(bad='password'):
            res = self.opener.post(
                f'{self.base_url()}/RPC2?db={db}',
                json=jsonrpc_req('system.noop', []),
                auth=('admin', 'badpassword'))
            self.assertEqual(res.status_code, HTTPStatus.FORBIDDEN)

        with self.subTest(good='user/pwd'):
            res = self.opener.post(
                f'{self.base_url()}/RPC2?db={db}',
                json=jsonrpc_req('system.noop', []),
                auth=('admin', 'admin'))
            self.assertEqual(res.status_code, HTTPStatus.OK)

    @mute_logger('odoo.addons.base.controllers.rpc')
    @freeze_time('2022-12-07 16:18:10')
    def test_rpc2_basic_auth_mfa(self):
        jack = new_test_user(self.env, 'jackoneill', context={'lang': 'en_US'})

        # Enable TOTP and add an API key
        totp_secret = secrets.token_bytes()
        totp_secret_humain = base64.b32encode(totp_secret).decode()
        totp_code = totp.hotp(totp_secret, int(time.time() / totp.TIMESTEP))
        jack.with_user(jack)._totp_try_setting(totp_secret_humain, totp_code)
        ApiKeys = self.env['res.users.apikeys'].with_user(jack)
        apikey = ApiKeys._generate('rpc', 'test_rpc2')
        self.assertTrue(jack._rpc_api_keys_only())

        db = get_db_name()
        with self.subTest(bad='login/pwd'):
            res = self.opener.post(
                f'{self.base_url()}/RPC2?db={db}',
                json=jsonrpc_req('system.noop', []),
                auth=('jackoneill', 'jackoneill'))
            self.assertEqual(res.status_code, HTTPStatus.FORBIDDEN)

        with self.subTest(good='login/apikey'):
            res = self.opener.post(
                f'{self.base_url()}/RPC2?db={db}',
                json=jsonrpc_req('system.noop', []),
                auth=('jackoneill', apikey))
            self.assertEqual(res.status_code, HTTPStatus.OK)

    @mute_logger('odoo.addons.base.controllers.rpc')
    def test_xmlrpc2_transport_errors(self):
        invalid_xml = "invalid xml"
        unknown_charset = xmlrpc_req('version', '').encode('ascii')
        bad_encoding = xmlrpc_req('vérsion', '').encode('utf-8')
        invalid_request = """<?xml version="1.0"?><methodCall></methodCall>"""

        test_matrix = [
            # pylint: disable=bad-whitespace
            # payload,        charset, expected http status, expected fault code, expected fault string
            (invalid_xml,     'utf-8', -32700, "xml.parsers.expat.ExpatError: syntax error: line 1, column 0"),
            (unknown_charset, 'ansi',  -32701, "LookupError: unknown encoding: ansi"),
            (bad_encoding,    'ascii', -32702, "UnicodeDecodeError: 'ascii' codec can't decode byte 0xc3 in position 52: ordinal not in range(128)"),
            (invalid_request, 'utf-8', -32600, "ValueError: malformed XML-RPC request"),
        ]

        for payload, charset, fault_code, fault_string in test_matrix:
            with self.subTest(fault=fault_string):
                res = self.url_open(
                    '/RPC2',
                    headers={'Content-Type': f'text/xml; charset={charset}'},
                    data=payload,
                )
                if fault_code == -32701:
                    self.assertEqual(res.status_code, HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
                    self.assertIn(CT_XML, res.headers.get('Accept'))
                else:
                    self.assertEqual(res.status_code, HTTPStatus.BAD_REQUEST)
                self.assertEqual(res.headers['Content-Type'], CT_XML)
                self.assertTreesEqual(
                    etree.fromstring(res.text),
                    etree.fromstring(xmlrpc_fault(fault_code, fault_string))
                )

    @mute_logger('odoo.addons.base.controllers.rpc')
    def test_jsonrpc2_transport_errors(self):
        invalid_json = "invalid json"
        unknown_charset = str(jsonrpc_req('version', [])).encode('ascii')
        bad_encoding = str(jsonrpc_req('vérsion', [])).encode('utf-8')
        invalid_request = 'null'

        test_matrix = [
            # pylint: disable=bad-whitespace
            # payload,        charset, expected error code, expected error message
            (invalid_json,    'utf-8', -32700, "json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)"),
            (unknown_charset, 'ansi',  -32701, "LookupError: unknown encoding: ansi"),
            (bad_encoding,    'ascii', -32702, "UnicodeDecodeError: 'ascii' codec can't decode byte 0xc3 in position 31: ordinal not in range(128)"),
            (invalid_request, 'utf-8', -32600, "ValueError: malformed JSON-RPC request"),
        ]

        for payload, charset, error_code, error_message in test_matrix:
            with self.subTest(fault=error_message):
                res = self.url_open(
                    '/RPC2',
                    headers={'Content-Type': f'application/json; charset={charset}'},
                    data=payload,
                )
                if error_code == -32701:
                    self.assertEqual(res.status_code, HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
                    self.assertIn(CT_JSON, res.headers.get('Accept'))
                else:
                    self.assertEqual(res.status_code, HTTPStatus.BAD_REQUEST)
                self.assertEqual(res.headers['Content-Type'], CT_JSON)
                self.assertEqual(
                    submap(res.json()['error'], {'code', 'message'}),
                    {'code': error_code, 'message': error_message}
                )

    @mute_logger('odoo.addons.base.controllers.rpc')
    def test_rpc2_routing_errors(self):
        unknown_admin_method = 'idontexist', []
        invalid_admin_params = 'version', [('string', 'bad')]
        old_admin_params = 'version', [('string', 'bad'), ('string', 'bad')]
        wrong_model_on_admin = 'res.partner.search', []
        unknown_model_name = 'i.dont.exist', []
        unknown_model_method = 'res.partner.idontexist', []
        wrong_admin_on_model = 'version', []
        invalid_model_params = 'res.partner.search', []
        bad_model_subject = 'res.partner.search', [('int', 1)]
        private_model_method = 'res.partner._search', []

        base_url = urlparse(self.base_url())
        admin_url = f'{base_url.scheme}://{base_url.netloc}/RPC2'
        model_url = f'{base_url.scheme}://admin:admin@{base_url.netloc}/RPC2?db={get_db_name()}'

        test_matrix = [
            # pylint: disable=bad-whitespace
            # client,  call,                  expected fault code, expected fault string
            ('admin', unknown_admin_method, -32601, "NameError: no admin function 'idontexist' found"),
            ('admin', invalid_admin_params, -32602, "TypeError: the RPC2 endpoint takes a single parameter: a dict with args and kwargs (both optional) keys"),
            ('admin', old_admin_params,     -32602, "TypeError: the RPC2 endpoint takes a single parameter: a dict with args and kwargs (both optional) keys. Did you mean {'args': ['bad', 'bad']}?"),
            ('admin', wrong_model_on_admin, -32601, "NameError: 'res.partner.search' is not a valid admin function"),
            ('model', unknown_admin_method, -32601, "NameError: 'idontexist' is not a valid model name"),
            ('model', unknown_model_name,   -32601, "NameError: no model 'i.dont' found"),
            ('model', unknown_model_method, -32601, "NameError: no method 'idontexist' found on model 'res.partner'"),
            ('model', wrong_admin_on_model, -32601, "NameError: 'version' is not a valid model name"),
            ('model', invalid_model_params, -32602, "TypeError: missing a required argument: 'domain'"),
            ('model', bad_model_subject,    -32602, "TypeError: the RPC2 endpoint takes a single parameter: a dict with records, context, args and kwargs (all optional) keys"),
            ('model', private_model_method, -32102, "odoo.exceptions.AccessError: '_search' is a private method and can not be called over RPC"),
        ]

        for client, (method, params), fault_code, fault_string in test_matrix:
            with self.subTest(type='xmlrpc', fault=fault_string):
                url = admin_url if client == 'admin' else model_url
                payload = xmlrpc_req(method, '\n        '.join(
                    f'<param><value><{ptype}>{pvalue}</{ptype}></value></param>'
                    for ptype, pvalue in params
                ))
                res = self.url_open(url, headers=HEADER_XML, data=payload)
                res.raise_for_status()
                self.assertEqual(res.headers['Content-Type'], CT_XML)
                self.assertTreesEqual(
                    etree.fromstring(res.text),
                    etree.fromstring(xmlrpc_fault(fault_code, fault_string))
                )

            with self.subTest(type='jsonrpc', fault=fault_string):
                url = admin_url if client == 'admin' else model_url
                payload = jsonrpc_req(method, [pvalue for ptype, pvalue in params])
                res = self.opener.post(url, json=payload)
                res.raise_for_status()
                self.assertEqual(res.headers['Content-Type'], CT_JSON)
                self.assertEqual(
                    submap(res.json()['error'], {'code', 'message'}),
                    {'code': fault_code, 'message': fault_string}
                )

    @mute_logger('odoo.addons.base.controllers.rpc')
    def test_rpc2_application_errors(self):
        func = 'test.exceptions.model.generate'
        test_matrix = [
            # pylint: disable=bad-whitespace
            # method                     expected fault code, expected fault string
            (f'{func}_user_error',       -32100, "odoo.exceptions.UserError: description"),
            (f'{func}_access_denied',    -32101, "odoo.exceptions.AccessDenied: Access Denied"),
            (f'{func}_access_error',     -32102, "odoo.exceptions.AccessError: description"),
            (f'{func}_missing_error',    -32103, "odoo.exceptions.MissingError: description"),
            (f'{func}_validation_error', -32104, "odoo.exceptions.ValidationError: description"),
            (f'{func}_undefined',        -32500, "AttributeError: 'test.exceptions.model' object has no attribute 'surely_undefined_symbol'"),
        ]

        base_url = urlparse(self.base_url())
        url = f'{base_url.scheme}://admin:admin@{base_url.netloc}/RPC2?db={get_db_name()}'
        for method, fault_code, fault_string in test_matrix:
            with self.subTest(type='xmlrpc', fault=fault_string):
                res = self.url_open(url, headers=HEADER_XML, data=xmlrpc_req(method, ''))
                res.raise_for_status()
                self.assertEqual(res.headers['Content-Type'], CT_XML)
                self.assertTreesEqual(
                    etree.fromstring(res.text),
                    etree.fromstring(xmlrpc_fault(fault_code, fault_string))
                )

            with self.subTest(type='jsonrpc', fault=fault_string):
                res = self.opener.post(url, json=jsonrpc_req(method, []))
                res.raise_for_status()
                self.assertEqual(res.headers['Content-Type'], CT_JSON)
                self.assertEqual(
                    submap(res.json()['error'], {'code', 'message'}),
                    {'code': fault_code, 'message': fault_string}
                )

    def test_rpc2_context(self):
        models = self.get_xmlrpc_models_proxy('admin', 'admin')
        self.env['res.lang']._activate_lang('fr_FR')

        title = self.env['res.partner.title'].create({'name': 'Major'})
        title.with_context(lang='fr_FR').name = 'Commandant'

        self.assertEqual(
            models.res.partner.title.name_get(
                {'records': title.ids, 'context': {'lang': 'fr_FR'}}),
            [[title.id, "Commandant"]],
            "subject can be a dict with a list of ids and a context"
        )
