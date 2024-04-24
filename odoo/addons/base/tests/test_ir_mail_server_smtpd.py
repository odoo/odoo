import contextlib
import logging
import shutil
import smtplib
import socket
import ssl
import subprocess
import sys
import tempfile
import unittest
import warnings
from base64 import b64encode
from pathlib import Path
from unittest.mock import patch
from socket import getaddrinfo  # keep a reference on the non-patched function

from odoo.exceptions import UserError
from odoo.tools import file_path, mute_logger
from .common import TransactionCaseWithUserDemo

try:
    import aiosmtpd
    import aiosmtpd.controller
    import aiosmtpd.smtp
    import aiosmtpd.handlers
except ImportError:
    aiosmtpd = None


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
        self.key = key
        self.cert = cert

    def __repr__(self):
        return f"Certificate({self.key=}, {self.cert=})"


def _generate_certificates(tempdir):
    """Generate and sign a few RSA key pairs inside a temporary directory.

    It invokes the openssl command line to create a new Certification
    Authority and then use that CA to generate extra keys and
    certificates for a user, a server.

    It also creates a self-signed certificate, to test that invalid
    certificates are correctly rejected.

    It returns 4 Certificate: CA, client, server, self-signed. Each
    Certificate has two attributes: key and cert, both are paths.
    """
    certdir = Path(tempdir.name)

    # Create a fake certificate authority and use it to generate a few
    # signed certificates.
    shutil.copy(file_path('base/tests/ssl/openssl.conf'), certdir)
    shutil.copy(file_path('base/tests/ssl/gencert.sh'), certdir)
    subprocess.run(
        [shutil.which('sh'), certdir / 'gencert.sh'],
        check=True,
        cwd=certdir,
        stdout=sys.stdout if _logger.isEnabledFor(logging.DEBUG) else subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )

    # Collect files and return them
    return (
        Certificate(key=None, cert=certdir / 'ca.cert.pem'),
        Certificate(key=certdir / 'client.key.pem', cert=certdir / 'client.cert.pem'),
        Certificate(key=certdir / 'server.key.pem', cert=certdir / 'server.cert.pem'),
        Certificate(key=certdir / 'self_signed.key.pem', cert=certdir / 'self_signed.cert.pem'),
    )


# skip when optional dependencies are not found
@unittest.skipUnless(aiosmtpd, "aiosmtpd couldn't be imported")
@unittest.skipUnless(_openssl, "openssl not found in path")
# fail fast for timeout errors
@patch('odoo.addons.base.models.ir_mail_server.SMTP_TIMEOUT', .1)
# prevent the CLI from interfering with the tests
@patch.dict('odoo.tools.config.options', {'smtp_server': ''})
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

        # create a few certificates for ssl/tls+starttls and mock the
        # various smtplib classes into trusting the created root CA.
        _logger.info("Using openssl to generate fake certificates, show "
                     "subprocess output with: --log-handler %s:DEBUG", __name__)
        tempdir = tempfile.TemporaryDirectory(prefix='odoo-test-smtpd-')
        cls.addClassCleanup(tempdir.cleanup)
        cls.ssl_ca, cls.ssl_client, cls.ssl_server, cls.ssl_self_signed = \
            _generate_certificates(tempdir)

        class TEST_SMTP(smtplib.SMTP):
            def starttls(self, *, context):
                if context is None:
                    context = ssl._create_stdlib_context()  # what SMTP_SSL does
                    # context = ssl.create_default_context()  # what it should do
                context.load_verify_locations(cafile=str(cls.ssl_ca.cert))
                super().starttls(context=context)
        patcher = patch('smtplib.SMTP', TEST_SMTP)
        patcher.start()
        cls.addClassCleanup(patcher.stop)

        class TEST_SMTP_SSL(smtplib.SMTP_SSL):
            def _get_socket(self, *args, **kwargs):
                # self.context = ssl.create_default_context()  # what it should do
                self.context.load_verify_locations(cafile=str(cls.ssl_ca.cert))
                return super()._get_socket(*args, **kwargs)
        patcher = patch('smtplib.SMTP_SSL', TEST_SMTP_SSL)
        patcher.start()
        cls.addClassCleanup(patcher.stop)

        # reactivate sending emails during this test suite, make sure
        # NOT TO send emails using another ir.mail_server than the one
        # created in setUp!
        patcher = patch.object(cls.registry['ir.mail_server'], '_is_test_mode')
        mock = patcher.start()
        mock.return_value = False
        cls.addClassCleanup(patcher.stop)

        # fix runbot, docker uses a single ipv4 stack but it gives ::1
        # when resolving "localhost" (so stupid), use the following to
        # force aiosmtpd/odoo to bind/connect to a fixed ipv4 OR ipv6
        # address.
        family, _, cls.port = _find_free_local_address()
        cls.localhost = getaddrinfo('localhost', cls.port, family)
        cls.startClassPatcher(patch('socket.getaddrinfo', cls.getaddrinfo))

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
                            with self.assertRaises(UserError) as error_capture:
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
                            with self.assertRaises(UserError) as capture:
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
                    with self.assertRaises(UserError) as capture:
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
