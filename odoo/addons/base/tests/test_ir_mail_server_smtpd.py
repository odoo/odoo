import contextlib
import logging
import shutil
import smtplib
import socket
import ssl
import unittest
import warnings
from base64 import b64encode
from pathlib import Path
from unittest.mock import patch
from socket import getaddrinfo  # keep a reference on the non-patched function

from odoo import modules
from odoo.exceptions import UserError
from odoo.tools import config, file_path, mute_logger
from .common import TransactionCaseWithUserDemo

try:
    import aiosmtpd
    import aiosmtpd.controller
    import aiosmtpd.smtp
    import aiosmtpd.handlers
except ImportError:
    aiosmtpd = None


SMTP_TIMEOUT = 5
PASSWORD = 'secretpassword'
_openssl = shutil.which('openssl')
_logger = logging.getLogger(__name__)


def _find_free_local_address():
    """ Get a triple (family, address, port) on which it possible to bind
    a local tcp service. """
    addr = aiosmtpd.controller.get_localhost()  # it returns 127.0.0.1 or ::1
    family = socket.AF_INET if addr == '127.0.0.1' else socket.AF_INET6
    with socket.socket(family, socket.SOCK_STREAM) as sock:
        sock.bind((addr, 0))
        port = sock.getsockname()[1]
    return family, addr, port


def _smtp_authenticate(server, session, enveloppe, mechanism, data):
    """ Callback method used by aiosmtpd to validate a login/password pair. """
    result = aiosmtpd.smtp.AuthResult(success=data.password == PASSWORD.encode())
    _logger.debug("AUTH %s", "successfull" if result.success else "failed")
    return result


class Certificate:
    def __init__(self, key, cert):
        self.key = key and Path(file_path(key, filter_ext='.pem'))
        self.cert = Path(file_path(cert, filter_ext='.pem'))

    def __repr__(self):
        return f"Certificate({self.key=}, {self.cert=})"


# skip when optional dependencies are not found
@unittest.skipUnless(aiosmtpd, "aiosmtpd couldn't be imported")
@unittest.skipUnless(_openssl, "openssl not found in path")
# fail fast for timeout errors
@patch('odoo.addons.base.models.ir_mail_server.SMTP_TIMEOUT', SMTP_TIMEOUT)
# prevent the CLI from interfering with the tests
@patch.dict(config.options, {'smtp_server': ''})
class TestIrMailServerSMTPD(TransactionCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # aiosmtpd emits deprecation warnings because it uses its own
        # deprecated features, mute those logs.
        # https://github.com/aio-libs/aiosmtpd/issues/347
        class Session(aiosmtpd.smtp.Session):
            @property
            def login_data(self):
                return self._login_data
            @login_data.setter
            def login_data(self, value):
                self._login_data = value
        patcher = patch('aiosmtpd.smtp.Session', Session)
        patcher.start()
        cls.addClassCleanup(patcher.stop)

        # aiosmtpd emits warnings for some unusual configuration, like
        # requiring AUTH on a clear-text transport. Mute those logs
        # since we also test those unusual configurations.
        warnings.filterwarnings(
            'ignore',
            "Requiring AUTH while not requiring TLS can lead to security vulnerabilities!",
            category=UserWarning
        )
        class CustomFilter(logging.Filter):
            def filter(self, record):
                if record.msg == "auth_required == True but auth_require_tls == False":
                    return False
                if record.msg == "tls_context.verify_mode not in {CERT_NONE, CERT_OPTIONAL}; this might cause client connection problems":
                    return False
                return True
        logging.getLogger('mail.log').addFilter(CustomFilter())

        # decrease aiosmtpd verbosity, odoo INFO = aiosmtpd WARNING
        logging.getLogger('mail.log').setLevel(_logger.getEffectiveLevel() + 10)

        # Get various TLS keys and certificates. CA was used to sign
        # both client and server. self_signed is... self signed.
        cls.ssl_ca, cls.ssl_client, cls.ssl_server, cls.ssl_self_signed = [
            Certificate(None, 'base/tests/ssl/ca.cert.pem'),
            Certificate('base/tests/ssl/client.key.pem',
                        'base/tests/ssl/client.cert.pem'),
            Certificate('base/tests/ssl/server.key.pem',
                        'base/tests/ssl/server.cert.pem'),
            Certificate('base/tests/ssl/self_signed.key.pem',
                        'base/tests/ssl/self_signed.cert.pem'),
        ]

        # Patch the two SMTP client classes into trusting the above CA
        class TEST_SMTP(smtplib.SMTP):
            def starttls(self, *, context):
                if context is None:
                    context = ssl._create_stdlib_context()  # what SMTP_SSL does
                    # context = ssl.create_default_context()  # what it should do
                context.load_verify_locations(cafile=str(cls.ssl_ca.cert))
                super().starttls(context=context)
        class TEST_SMTP_SSL(smtplib.SMTP_SSL):
            def _get_socket(self, *args, **kwargs):
                # self.context = ssl.create_default_context()  # what it should do
                self.context.load_verify_locations(cafile=str(cls.ssl_ca.cert))
                return super()._get_socket(*args, **kwargs)
        patcher = patch('smtplib.SMTP', TEST_SMTP)
        patcher.start()
        cls.addClassCleanup(patcher.stop)
        patcher = patch('smtplib.SMTP_SSL', TEST_SMTP_SSL)
        patcher.start()
        cls.addClassCleanup(patcher.stop)

        # fix runbot, docker uses a single ipv4 stack but it gives ::1
        # when resolving "localhost" (so stupid), use the following to
        # force aiosmtpd/odoo to bind/connect to a fixed ipv4 OR ipv6
        # address.
        family, addr, cls.port = _find_free_local_address()
        cls.localhost = getaddrinfo(addr, cls.port, family)
        cls.startClassPatcher(patch('socket.getaddrinfo', cls.getaddrinfo))

    def setUp(self):
        super().setUp()
        # reactivate sending emails during this test suite, make sure
        # NOT TO send emails using another ir.mail_server than the one
        # created in setUp!
        patcher = patch.object(modules.module, 'current_test', False)
        patcher.start()
        self.addCleanup(patcher.stop)

    @classmethod
    def getaddrinfo(cls, host, port, *args, **kwargs):
        """
        Resolve both "localhost" and "notlocalhost" on the ip address
        bound by aiosmtpd inside `start_smtpd`.
        """
        if host in ('localhost', 'notlocalhost') and port == cls.port:
            return cls.localhost
        return getaddrinfo(host, port, family=0, type=0, proto=0, flags=0)

    @contextlib.contextmanager
    def start_smtpd(
        self, encryption, ssl_context=None, auth_required=True, stop_on_cleanup=True
    ):
        """
        Start a smtp daemon in a background thread, stop it upon exiting
        the context manager.

        :param encryption: 'none', 'ssl' or 'starttls', the kind of
            server to start.
        :param ssl_context: the ``ssl.SSLContext`` object to use with
            'ssl' or 'starttls'.
        :param auth_required: whether the server enforces password
            authentication or not.
        """
        assert encryption in ('none', 'ssl', 'starttls')
        assert encryption == 'none' or ssl_context

        kwargs = {}
        if encryption == 'starttls':
            # for aiosmtpd.smtp.SMTP
            kwargs.update({
                'require_starttls': True,
                'tls_context': ssl_context,
            })
        elif encryption == 'ssl':
            # for aiosmtpd.controller.InetMixin
            kwargs['ssl_context'] = ssl_context
        if auth_required:
            kwargs['authenticator'] = _smtp_authenticate

        smtpd_thread = aiosmtpd.controller.Controller(
            aiosmtpd.handlers.Debugging(),
            hostname=aiosmtpd.controller.get_localhost(),
            server_hostname='localhost',
            port=self.port,
            auth_required=auth_required,
            auth_require_tls=False,
            enable_SMTPUTF8=True,
            **kwargs,
        )
        try:
            smtpd_thread.start()
            yield smtpd_thread
        finally:
            smtpd_thread.stop()

    @mute_logger('mail.log')
    def test_authentication_certificate_matrix(self):
        """
        Connect to a server that is authenticating users via a TLS
        certificate. Test the various possible configurations (missing
        cert, invalid cert and valid cert) against both a STARTTLS and
        a SSL/TLS SMTP server.
        """
        mail_server = self.env['ir.mail_server'].create({
            'name': 'test smtpd',
            'from_filter': 'localhost',
            'smtp_host': 'localhost',
            'smtp_port': self.port,
            'smtp_authentication': 'login',
            'smtp_user': '',
            'smtp_pass': '',
        })

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(self.ssl_server.cert, self.ssl_server.key)
        ssl_context.load_verify_locations(cafile=self.ssl_ca.cert)
        ssl_context.verify_mode = ssl.CERT_REQUIRED

        self_signed_key = b64encode(self.ssl_self_signed.key.read_bytes())
        self_signed_cert = b64encode(self.ssl_self_signed.cert.read_bytes())
        client_key = b64encode(self.ssl_client.key.read_bytes())
        client_cert = b64encode(self.ssl_client.cert.read_bytes())
        matrix = [
            # authentication, name, certificate, private key, error pattern
            ('login', "missing", '', '',
                r"The server has closed the connection unexpectedly\. "
                r"Check configuration served on this port number\.\n "
                r"Connection unexpectedly closed"),
            ('certificate', "self signed", self_signed_cert, self_signed_key,
                r"The server has closed the connection unexpectedly\. "
                r"Check configuration served on this port number\.\n "
                r"Connection unexpectedly closed"),
            ('certificate', "valid client", client_cert, client_key, None),
        ]

        for encryption in ('starttls', 'ssl'):
            mail_server.smtp_encryption = encryption
            with self.start_smtpd(encryption, ssl_context, auth_required=False):
                for authentication, name, certificate, private_key, error_pattern in matrix:
                    with self.subTest(encryption=encryption, certificate=name):
                        mail_server.write({
                            'smtp_authentication': authentication,
                            'smtp_ssl_certificate': certificate,
                            'smtp_ssl_private_key': private_key,
                        })
                        if error_pattern:
                            timeout = .1 if 'timed out' in error_pattern else SMTP_TIMEOUT
                            with self.assertRaises(UserError) as error_capture, \
                                 patch('odoo.addons.base.models.ir_mail_server.SMTP_TIMEOUT', timeout):
                                mail_server.test_smtp_connection()
                            self.assertRegex(error_capture.exception.args[0], error_pattern)
                        else:
                            mail_server.test_smtp_connection()

    def test_authentication_login_matrix(self):
        """
        Connect to a server that is authenticating users via a login/pwd
        pair. Test the various possible configurations (missing pair,
        invalid pair and valid pair) against both a SMTP server without
        encryption, a STARTTLS and a SSL/TLS SMTP server.
        """
        mail_server = self.env['ir.mail_server'].create({
            'name': 'test smtpd',
            'from_filter': 'localhost',
            'smtp_host': 'localhost',
            'smtp_port': self.port,
            'smtp_authentication': 'login',
            'smtp_user': '',
            'smtp_pass': '',
        })

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(self.ssl_server.cert, self.ssl_server.key)

        MISSING = ''
        INVALID = 'bad password'
        matrix = [
            # auth_required, password, error_pattern
            (False, MISSING, None),
            (True, MISSING,
                r"The server refused the sender address \(noreply@localhost\) "
                r"with error b'5\.7\.0 Authentication required'"),
            (True, INVALID,
                r"The server has closed the connection unexpectedly\. "
                r"Check configuration served on this port number\.\n "
                r"Connection unexpectedly closed:.* timed out"),
            (True, PASSWORD, None),
        ]

        for encryption in ('none', 'starttls', 'ssl'):
            mail_server.smtp_encryption = encryption
            for auth_required, password, error_pattern in matrix:
                mail_server.smtp_user = password and self.user_demo.email
                mail_server.smtp_pass = password
                with self.subTest(encryption=encryption,
                                  auth_required=auth_required,
                                  password=password):
                    with self.start_smtpd(encryption, ssl_context, auth_required):
                        if error_pattern:
                            timeout = .1 if 'timed out' in error_pattern else SMTP_TIMEOUT
                            with self.assertRaises(UserError) as capture, \
                                 patch('odoo.addons.base.models.ir_mail_server.SMTP_TIMEOUT', timeout):
                                mail_server.test_smtp_connection()
                            self.assertRegex(capture.exception.args[0], error_pattern)
                        else:
                            mail_server.test_smtp_connection()

    @mute_logger('mail.log')
    def test_encryption_matrix(self):
        """
        Connect to a server on a different encryption configuration than
        the server is configured. Verify that it crashes with a good
        error message.
        """
        mail_server = self.env['ir.mail_server'].create({
            'name': 'test smtpd',
            'from_filter': 'localhost',
            'smtp_host': 'localhost',
            'smtp_port': self.port,
            'smtp_authentication': 'login',
            'smtp_user': '',
            'smtp_pass': '',
        })

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(self.ssl_server.cert, self.ssl_server.key)

        matrix = [
            # client, server, error_pattern
            ('none', 'ssl',
                r"The server has closed the connection unexpectedly\. "
                r"Check configuration served on this port number\.\n "
                r"Connection unexpectedly closed: timed out"),
            ('none', 'starttls',
                r"The server refused the sender address \(noreply@localhost\) with error "
                r"b'Must issue a STARTTLS command first'"),
            ('starttls', 'none',
                r"An option is not supported by the server:\n "
                r"STARTTLS extension not supported by server\."),
            ('starttls', 'ssl',
                r"The server has closed the connection unexpectedly\. "
                r"Check configuration served on this port number\.\n "
                r"Connection unexpectedly closed: timed out"),
            ('ssl', 'none',
                r"An SSL exception occurred\. "
                r"Check connection security type\.\n "
                r".*?wrong version number"),
            ('ssl', 'starttls',
                r"An SSL exception occurred\. "
                r"Check connection security type\.\n "
                r".*?wrong version number"),
        ]

        for client_encryption, server_encryption, error_pattern in matrix:
            with self.subTest(server_encryption=server_encryption,
                              client_encryption=client_encryption):
                mail_server.smtp_encryption = client_encryption
                with self.start_smtpd(server_encryption, ssl_context, auth_required=False):
                    timeout = .1 if 'timed out' in error_pattern else SMTP_TIMEOUT
                    with self.assertRaises(UserError) as capture, \
                         patch('odoo.addons.base.models.ir_mail_server.SMTP_TIMEOUT', timeout):
                        mail_server.test_smtp_connection()
                    self.assertRegex(capture.exception.args[0], error_pattern)

    def test_man_in_the_middle_matrix(self):
        """
        Simulate that a pirate was successful at intercepting the live
        traffic in between the Odoo server and the legitimate SMTP
        server.
        """
        mail_server = self.env['ir.mail_server'].create({
            'name': 'test smtpd',
            'from_filter': 'localhost',
            'smtp_host': 'localhost',
            'smtp_port': self.port,
            'smtp_authentication': 'login',
            'smtp_user': self.user_demo.email,
            'smtp_pass': PASSWORD,
            'smtp_ssl_certificate': b64encode(self.ssl_client.cert.read_bytes()),
            'smtp_ssl_private_key': b64encode(self.ssl_client.key.read_bytes()),
        })

        cert_good = self.ssl_server
        cert_bad = self.ssl_self_signed
        host_good = 'localhost'
        host_bad = 'notlocalhost'

        # for now it doesn't raise any error for bad cert/host
        matrix = [
            # authentication, certificate, hostname, error_pattern
            ('login', cert_bad, host_good, None),
            ('login', cert_good, host_bad, None),
            ('certificate', cert_bad, host_good, None),
            ('certificate', cert_good, host_bad, None),
        ]

        for encryption in ('starttls', 'ssl'):
            for authentication, certificate, hostname, error_pattern in matrix:
                mail_server.smtp_host = hostname
                mail_server.smtp_authentication = authentication
                mail_server.smtp_encryption = encryption
                with self.subTest(
                    encryption=encryption,
                    authentication=authentication,
                    cert_good=certificate == cert_good,
                    host_good=hostname == host_good,
                ):
                    mitm_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                    mitm_context.load_cert_chain(certificate.cert, certificate.key)
                    auth_required = authentication == 'login'
                    with self.start_smtpd(encryption, mitm_context, auth_required):
                        if error_pattern:
                            with self.assertRaises(UserError) as capture:
                                mail_server.test_smtp_connection()
                            self.assertRegex(capture.exception.args[0], error_pattern)
                        else:
                            mail_server.test_smtp_connection()
