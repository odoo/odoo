import contextlib
import logging
import smtplib
import socket
import ssl
import textwrap
import unittest
import warnings
from base64 import b64decode, b64encode
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from socket import getaddrinfo  # keep a reference on the non-patched function

from odoo import Command, modules
from odoo.exceptions import UserError
from odoo.tools import file_path, mute_logger
from odoo.tools.misc import SENTINEL
from .common import TransactionCaseWithUserDemo

try:
    import aiosmtpd
    import aiosmtpd.controller
    import aiosmtpd.smtp
    import aiosmtpd.handlers
except ImportError:
    aiosmtpd = None


PASSWORD = 'secretpassword'
_logger = logging.getLogger(__name__)

DEFAULT_SMTP_CONFIG = {
    'email_from': False,
    'from_filter': False,
    'smtp_server': 'localhost',
    'smtp_port': 25,
    'smtp_ssl': 'none',
    'smtp_user': False,
    'smtp_password': False,
    'smtp_ssl_certificate_filename': False,
    'smtp_ssl_private_key_filename': False,
}


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
    def __init__(self, key, pubkey, cert):
        self.key = key and Path(file_path(key, filter_ext='.pem'))
        self.pubkey = Path(file_path(pubkey, filter_ext='.pem'))
        self.cert = Path(file_path(cert, filter_ext='.pem'))

    def __repr__(self):
        return f"Certificate({self.key=}, {self.cert=})"


class Mixin:
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
            Certificate(None,
                        'base/tests/ssl/ca.pub.pem',
                        'base/tests/ssl/ca.cert.pem'),
            Certificate('base/tests/ssl/client.key.pem',
                        'base/tests/ssl/client.pub.pem',
                        'base/tests/ssl/client.cert.pem'),
            Certificate('base/tests/ssl/server.key.pem',
                        'base/tests/ssl/server.pub.pem',
                        'base/tests/ssl/server.cert.pem'),
            Certificate('base/tests/ssl/self_signed.key.pem',
                        'base/tests/ssl/self_signed.pub.pem',
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

        # reactivate sending emails during this test suite, make sure
        # NOT TO send emails using another ir.mail_server than the one
        # created in setUp!
        patcher = patch.object(modules.module, 'current_test', False)
        patcher.start()
        cls.addClassCleanup(patcher.stop)

        # fix runbot, docker uses a single ipv4 stack but it gives ::1
        # when resolving "localhost" (so stupid), use the following to
        # force aiosmtpd/odoo to bind/connect to a fixed ipv4 OR ipv6
        # address.
        family, _, cls.port = _find_free_local_address()
        cls.localhost = getaddrinfo('localhost', cls.port, family)
        cls.startClassPatcher(patch('socket.getaddrinfo', cls.getaddrinfo))

    def setUp(self):
        super().setUp()

        # prevent the current configuration from interfering with the tests
        self.config = self.startPatcher(
            patch.dict('odoo.tools.config.options', DEFAULT_SMTP_CONFIG)
        )

        self.mail_server = self.env['ir.mail_server'].create({'name': 'test smtpd'})
        self.mail_server_write({
            'from_filter': 'localhost',
            'smtp_host': 'localhost',
            'smtp_port': self.port,
        })

    def mail_server_write(self):
        raise NotImplementedError("abstract method")

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
        self.mail_server_write({
            'smtp_authentication': 'login',
            'smtp_user': '',
            'smtp_pass': '',
        })

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(self.ssl_server.cert, self.ssl_server.key)
        ssl_context.load_verify_locations(cafile=self.ssl_ca.cert)
        ssl_context.verify_mode = ssl.CERT_REQUIRED

        matrix = [
            # authentication, name, certificate, private key, error pattern
            ('login', "missing", '', '',
                r"The server has closed the connection unexpectedly\. "
                r"Check configuration served on this port number\.\n "
                r"Connection unexpectedly closed"),
            ('certificate', "self signed", self.ssl_self_signed.cert, self.ssl_self_signed.key,
                r"The server has closed the connection unexpectedly\. "
                r"Check configuration served on this port number\.\n "
                r"Connection unexpectedly closed"),
            ('certificate', "valid client", self.ssl_client.cert, self.ssl_client.key, None),
        ]

        for encryption, check in [
            ('starttls', True),
            ('starttls', False),
            ('ssl', True),
            ('ssl', False)
        ]:
            with self.start_smtpd(encryption, ssl_context, auth_required=False):
                for authentication, name, certificate, private_key, error_pattern in matrix:
                    with self.subTest(encryption=encryption, certificate=name):
                        self.mail_server_write({
                            'smtp_encryption': encryption,
                            'smtp_authentication': authentication,
                            'smtp_ssl_certificate': certificate,
                            'smtp_ssl_private_key': private_key,
                            'smtp_ssl_check_certificate': check,
                        })
                        if error_pattern:
                            with self.assertRaises(UserError) as error_capture:
                                self.mail_server.test_smtp_connection()
                            self.assertRegex(error_capture.exception.args[0], error_pattern)
                        else:
                            self.mail_server.test_smtp_connection()


    def test_authentication_login_matrix(self):
        """
        Connect to a server that is authenticating users via a login/pwd
        pair. Test the various possible configurations (missing pair,
        invalid pair and valid pair) against both a SMTP server without
        encryption, a STARTTLS and a SSL/TLS SMTP server.
        """
        self.mail_server_write({
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
                r"The server refused the sender address \(\w+@[\w.]+\) "
                r"with error b'5\.7\.0 Authentication required'"),
            (True, INVALID,
                r"The server has closed the connection unexpectedly\. "
                r"Check configuration served on this port number\.\n "
                r"Connection unexpectedly closed:.* timed out"),
            (True, PASSWORD, None),
        ]

        for encryption, check_cert in (('none', False), ('starttls', False), ('starttls', True), ('ssl', False), ('ssl', True)):
            for auth_required, password, error_pattern in matrix:
                self.mail_server_write({
                    'smtp_encryption': encryption,
                    'smtp_user': password and self.user_demo.email,
                    'smtp_pass': password,
                    'smtp_ssl_check_certificate': check_cert,
                })
                with self.subTest(encryption=encryption,
                                  auth_required=auth_required,
                                  password=password):
                    with self.start_smtpd(encryption, ssl_context, auth_required):
                        if error_pattern:
                            with self.assertRaises(UserError) as capture:
                                self.mail_server.test_smtp_connection()
                            self.assertRegex(capture.exception.args[0], error_pattern)
                        else:
                            self.mail_server.test_smtp_connection()

    @mute_logger('mail.log')
    def test_encryption_matrix(self):
        """
        Connect to a server on a different encryption configuration than
        the server is configured. Verify that it crashes with a good
        error message.
        """
        self.mail_server_write({
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
                r"The server refused the sender address \(\w+@[\w.]+\) with error "
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
                self.mail_server_write({'smtp_encryption': client_encryption})
                with self.start_smtpd(server_encryption, ssl_context, auth_required=False):
                    with self.assertRaises(UserError) as capture:
                        self.mail_server.test_smtp_connection()
                    self.assertRegex(capture.exception.args[0], error_pattern)

    @mute_logger('mail.log')
    def test_man_in_the_middle_matrix(self):
        """
        Simulate that a pirate was successful at intercepting the live
        traffic in between the Odoo server and the legitimate SMTP
        server.
        """
        cert_good = self.ssl_server
        cert_bad = self.ssl_self_signed
        host_good = 'localhost'
        host_bad = 'notlocalhost'

        matrix = [
            # strict?, authentication, certificate, hostname, error_pattern
            (False, 'login', cert_bad, host_good, None),
            (False, 'login', cert_good, host_bad, None),
            (False, 'certificate', cert_bad, host_good, None),
            (False, 'certificate', cert_good, host_bad, None),
            (True, 'login', cert_bad, host_good,
                r"^An SSL exception occurred\. Check connection security type\.\n "
                r".*certificate verify failed"),
            (True, 'login', cert_good, host_bad,
                r"^An SSL exception occurred\. Check connection security type\.\n "
                r".*("
                    r"Hostname mismatch, certificate is not valid for 'notlocalhost'"
                r"|"
                    r"hostname 'notlocalhost' doesn't match 'localhost'"
                r")"
            ),
            (True, 'certificate', cert_bad, host_good,
                r"^An SSL exception occurred\. Check connection security type\.\n "
                r".*certificate verify failed"),
            (True, 'certificate', cert_good, host_bad,
                r"^An SSL exception occurred\. Check connection security type\.\n "
                r".*("
                    r"Hostname mismatch, certificate is not valid for 'notlocalhost'"
                r"|"
                    r"hostname 'notlocalhost' doesn't match 'localhost'"
                r")"
                ),
        ]

        for encryption in ('starttls', 'ssl'):
            for strict, authentication, certificate, hostname, error_pattern in matrix:
                self.mail_server_write({
                    'smtp_host': hostname,
                    'smtp_authentication': authentication,
                    'smtp_encryption': encryption,
                    'smtp_ssl_check_certificate': strict,
                    **({
                        'smtp_user': self.user_demo.email,
                        'smtp_pass': PASSWORD,
                        'smtp_ssl_certificate': '',
                        'smtp_ssl_private_key': '',
                    } if authentication == 'login' else {
                        'smtp_user': '',
                        'smtp_pass': '',
                        'smtp_ssl_certificate': self.ssl_client.cert,
                        'smtp_ssl_private_key': self.ssl_client.key,
                    })
                })
                with self.subTest(
                    encryption=encryption,
                    check_cert=strict,
                    authentication=authentication,
                    cert_good=certificate == cert_good,
                    host_good=hostname == host_good,
                ):
                    mitm_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                    mitm_context.load_cert_chain(certificate.cert, certificate.key)
                    auth_required = authentication == 'login'
                    with self.start_smtpd(encryption, mitm_context, auth_required=auth_required):
                        if error_pattern:
                            with self.assertRaises(UserError) as capture:
                                self.mail_server.test_smtp_connection()
                            self.assertRegex(capture.exception.args[0], error_pattern)
                        else:
                            self.mail_server.test_smtp_connection()


# skip when optional dependencies are not found
@unittest.skipUnless(aiosmtpd, "aiosmtpd couldn't be imported")
# fail fast for timeout errors
@patch('odoo.addons.base.models.ir_mail_server.SMTP_TIMEOUT', .1)
class TestIrMailServerSMTPD(Mixin, TransactionCaseWithUserDemo):
    def mail_server_write(self, values):
        # this method is override in TestCliMailServerSMTPD so it writes
        # the values in the config instead of on the recordset.
        cert = values.get('smtp_ssl_certificate')
        if cert:
            values['smtp_ssl_certificate'] = b64encode(cert.read_bytes())
        key = values.get('smtp_ssl_private_key')
        if key:
            values['smtp_ssl_private_key'] = b64encode(key.read_bytes())
        self.mail_server.write(values)

    @mute_logger('mail.log')
    def test_download_remote_certificate(self):
        """
        Add a security exception for a mail server that is using an
        invalid certificate.
        """
        # The remote mail server is using an untrusted certificate
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.ssl_self_signed.cert, self.ssl_self_signed.key)

        for encryption in ('ssl', 'starttls'):
            with (self.subTest(encryption=encryption),
                  self.start_smtpd(encryption, context, auth_required=False)):
                self.mail_server.write({
                    'smtp_authentication': 'login',
                    'smtp_user': '',
                    'smtp_pass': '',
                    'smtp_encryption': encryption,
                    'smtp_ssl_check_certificate': True,
                    'smtp_ssl_trusted_public_keys': [Command.clear()],
                })

                # Connection must be rejected
                with self.assertRaises(UserError) as error_capture:
                    self.mail_server.test_smtp_connection()
                self.assertIn("certificate verify failed", error_capture.exception.args[0])

                # Download the certificate of the remote mail server
                x509 = self.env['base.x509.wizard'].create({
                    'mail_server_id': self.mail_server.id,
                })
                action = x509.download()
                self.assertEqual(action['res_id'], x509.id)

                # Check the information extracted from the certificate,
                # and public key, you access them running:
                #   openssl x509 -text -in odoo/addons/base/tests/ssl/self_signed.cert.pem
                #   openssl rsa -text -pubin -in odoo/addons/base/tests/ssl/self_signed.pub.pem
                self.assertEqual(b64decode(x509.certificate_pem),
                                 self.ssl_self_signed.cert.read_bytes())
                self.assertEqual(b64decode(x509.public_key_pem),
                                 self.ssl_self_signed.pubkey.read_bytes())
                self.assertEqual(x509.subject, "CN=SelfSigned Lmtd")
                self.assertEqual(x509.subject_alternative_names, "")
                self.assertEqual(x509.issuer, "CN=SelfSigned Lmtd")
                self.assertEqual(x509.not_valid_before, datetime(2024, 4, 22, 15, 14, 57))
                self.assertEqual(x509.not_valid_after, datetime(3023, 8, 24, 15, 14, 57))
                self.assertEqual(x509.signature, textwrap.dedent("""\
                    c0:0c:02:82:63:85:83:85:52:67:45:ec:8f:d9:f7:3f:13:f3:
                    76:59:ad:bd:04:27:51:f4:b6:71:4b:6b:0d:77:98:32:42:76:
                    49:14:72:ea:bb:54:7e:b4:c0:02:b5:71:b8:ab:50:04:b8:dd:
                    32:9f:b8:6c:a8:27:f2:de:14:07:e6:61:4b:a9:0c:cd:aa:85:
                    85:e8:70:d0:af:66:fb:91:fc:3f:13:54:b7:6c:7f:ca:fb:a2:
                    9b:bb:97:c4:61:64:59:36:8e:53:8b:ad:a6:10:78:52:4b:6b:
                    41:c3:4a:a6:37:da:5c:79:3f:d9:16:16:29:7b:8e:11:43:3b:
                    b1:11:c9:0e:5c:1a:71:83:52:7c:34:0a:af:92:77:ef:97:d9:
                    ee:df:50:bc:61:ef:7c:5e:5b:07:0c:6c:ff:a9:4b:e6:20:fa:
                    97:0a:69:a0:db:a3:5c:4f:f3:44:db:a0:3b:ea:d8:1e:81:40:
                    e8:53:f2:b8:58:53:ab:e5:cc:87:70:87:da:61:61:60:db:f4:
                    8a:ba:4b:9d:42:57:70:53:dd:99:bc:93:92:c1:8b:e7:dc:c2:
                    a2:c6:0f:d8:64:62:be:d0:cc:33:32:6e:1c:f9:92:ad:b4:bd:
                    4f:c2:e6:f8:1a:df:59:68:5a:f3:ac:cd:6d:d8:d4:53:80:c8:
                    8a:53:69:50"""))

                # Add the public key to the trusted ones, check it is
                # the right public key that was added.
                x509.save()
                [pubkey] = self.mail_server.smtp_ssl_trusted_public_keys
                self.assertEqual(pubkey.raw, self.ssl_self_signed.pubkey.read_bytes())
                self.assertEqual(pubkey.name, "SelfSigned Lmtd.pub.pem")
                self.assertEqual(pubkey.mimetype, "application/x-pem-file")
                self.assertEqual(pubkey.description, textwrap.dedent("""\
                    This public key was extracted from the following certificate.

                    Subject: CN=SelfSigned Lmtd
                    Subject alternative names: 
                    Issuer: CN=SelfSigned Lmtd
                    Not valid before: Apr 22, 2024, 5:14:57 PM
                    Not valid after: Aug 24, 3023, 4:14:57 PM
                    Signature:
                    %s
                    """) % x509.signature)  # noqa: W291

                # Attempt to connect again, this time it must work.
                self.mail_server.test_smtp_connection()

    def test_download_remote_certificate_failure(self):
        """
        Prevent users from downloading/installing the certificate of a
        remote mail server when it is possible to connect to that server
        already.
        """

        self.mail_server.write({
            'smtp_encryption': 'none',
            'smtp_authentication': 'login',
            'smtp_user': '',
            'smtp_pass': '',
        })
        with self.start_smtpd('none', auth_required=False):
            with self.assertRaises(UserError) as error_capture:
                self.env['base.x509.wizard'].create({
                    'mail_server_id': self.mail_server.id
                }).download()
        self.assertEqual(error_capture.exception.args[0],
            "The connection can be established already. "
            "Certificate importation cancelled.")


IR_TO_CLI = {
    'smtp_host': 'smtp_server',
    'smtp_pass': 'smtp_password',
    'smtp_encryption': 'smtp_ssl',
    'smtp_ssl_certificate': 'smtp_ssl_certificate_filename',
    'smtp_ssl_private_key': 'smtp_ssl_private_key_filename',
}


# skip when optional dependencies are not found
@unittest.skipUnless(aiosmtpd, "aiosmtpd couldn't be imported")
# fail fast for timeout errors
@patch('odoo.addons.base.models.ir_mail_server.SMTP_TIMEOUT', .1)
class TestCliMailServerSMTPD(Mixin, TransactionCaseWithUserDemo):
    def setUp(self):
        super().setUp()
        self.mail_server.smtp_authentication = 'cli'

    def mail_server_write(self, values):
        for ir, cli in IR_TO_CLI.items():
            value = values.pop(ir, SENTINEL)
            if value is not SENTINEL:
                values[cli] = str(value)
        values.pop('smtp_authentication', None)
        if values.pop('smtp_ssl_check_certificate', None):
            values['smtp_ssl'] += '_strict'
        self.assertFalse(set(values) - set(DEFAULT_SMTP_CONFIG))
        self.config.update(values)
