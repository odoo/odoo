# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from email.message import EmailMessage
from email.utils import make_msgid
import base64
import datetime
import email
import email.policy
import idna
import logging
import re
import smtplib
import ssl
import sys
import threading

from socket import gaierror, timeout
from OpenSSL import crypto as SSLCrypto
from OpenSSL.crypto import Error as SSLCryptoError, FILETYPE_PEM
from OpenSSL.SSL import Error as SSLError
from urllib3.contrib.pyopenssl import PyOpenSSLContext

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.tools import ustr, pycompat, formataddr, email_normalize, encapsulate_email, email_domain_extract, email_domain_normalize


_logger = logging.getLogger(__name__)
_test_logger = logging.getLogger('odoo.tests')

SMTP_TIMEOUT = 60


class MailDeliveryException(Exception):
    """Specific exception subclass for mail delivery errors"""


def make_wrap_property(name):
    return property(
        lambda self: getattr(self.__obj__, name),
        lambda self, value: setattr(self.__obj__, name, value),
    )


class SMTPConnection:
    """Wrapper around smtplib.SMTP and smtplib.SMTP_SSL"""
    def __init__(self, server, port, encryption, context=None):
        if encryption == 'ssl':
            self.__obj__ = smtplib.SMTP_SSL(server, port, timeout=SMTP_TIMEOUT, context=context)
        else:
            self.__obj__ = smtplib.SMTP(server, port, timeout=SMTP_TIMEOUT)


SMTP_ATTRIBUTES = [
    'auth', 'auth_cram_md5', 'auth_login', 'auth_plain', 'close', 'data', 'docmd', 'ehlo', 'ehlo_or_helo_if_needed',
    'expn', 'from_filter', 'getreply', 'has_extn', 'login', 'mail', 'noop', 'putcmd', 'quit', 'rcpt', 'rset',
    'send_message', 'sendmail', 'set_debuglevel', 'smtp_from', 'starttls', 'verify', '_host',
]
for name in SMTP_ATTRIBUTES:
    setattr(SMTPConnection, name, make_wrap_property(name))


# Python 3: patch SMTP's internal printer/debugger
def _print_debug(self, *args):
    _logger.debug(' '.join(str(a) for a in args))
smtplib.SMTP._print_debug = _print_debug

# Python 3: workaround for bpo-35805, only partially fixed in Python 3.8.
RFC5322_IDENTIFICATION_HEADERS = {'message-id', 'in-reply-to', 'references', 'resent-msg-id'}
_noFoldPolicy = email.policy.SMTP.clone(max_line_length=None)
class IdentificationFieldsNoFoldPolicy(email.policy.EmailPolicy):
    # Override _fold() to avoid folding identification fields, excluded by RFC2047 section 5
    # These are particularly important to preserve, as MTAs will often rewrite non-conformant
    # Message-ID headers, causing a loss of thread information (replies are lost)
    def _fold(self, name, value, *args, **kwargs):
        if name.lower() in RFC5322_IDENTIFICATION_HEADERS:
            return _noFoldPolicy._fold(name, value, *args, **kwargs)
        return super()._fold(name, value, *args, **kwargs)

# Global monkey-patch for our preferred SMTP policy, preserving the non-default linesep
email.policy.SMTP = IdentificationFieldsNoFoldPolicy(linesep=email.policy.SMTP.linesep)

# Python 2: replace smtplib's stderr
class WriteToLogger(object):
    def write(self, s):
        _logger.debug(s)
smtplib.stderr = WriteToLogger()

def is_ascii(s):
    return all(ord(cp) < 128 for cp in s)

address_pattern = re.compile(r'([^" ,<@]+@[^>" ,]+)')

def extract_rfc2822_addresses(text):
    """Returns a list of valid RFC2822 addresses
       that can be found in ``source``, ignoring
       malformed ones and non-ASCII ones.
    """
    if not text:
        return []
    candidates = address_pattern.findall(ustr(text))
    valid_addresses = []
    for c in candidates:
        try:
            valid_addresses.append(formataddr(('', c), charset='ascii'))
        except idna.IDNAError:
            pass
    return valid_addresses


class IrMailServer(models.Model):
    """Represents an SMTP server, able to send outgoing emails, with SSL and TLS capabilities."""
    _name = "ir.mail_server"
    _description = 'Mail Server'
    _order = 'sequence'
    _allow_sudo_commands = False

    NO_VALID_RECIPIENT = ("At least one valid recipient address should be "
                          "specified for outgoing emails (To/Cc/Bcc)")

    name = fields.Char(string='Description', required=True, index=True)
    from_filter = fields.Char(
      "From Filter",
      help='Define for which email address or domain this server can be used.\n'
      'e.g.: "notification@odoo.com" or "odoo.com"')
    smtp_host = fields.Char(string='SMTP Server', required=True, help="Hostname or IP of SMTP server")
    smtp_port = fields.Integer(string='SMTP Port', required=True, default=25, help="SMTP Port. Usually 465 for SSL, and 25 or 587 for other cases.")
    smtp_authentication = fields.Selection([('login', 'Username'), ('certificate', 'SSL Certificate')], string='Authenticate with', required=True, default='login')
    smtp_user = fields.Char(string='Username', help="Optional username for SMTP authentication", groups='base.group_system')
    smtp_pass = fields.Char(string='Password', help="Optional password for SMTP authentication", groups='base.group_system')
    smtp_encryption = fields.Selection([('none', 'None'),
                                        ('starttls', 'TLS (STARTTLS)'),
                                        ('ssl', 'SSL/TLS')],
                                       string='Connection Security', required=True, default='none',
                                       help="Choose the connection encryption scheme:\n"
                                            "- None: SMTP sessions are done in cleartext.\n"
                                            "- TLS (STARTTLS): TLS encryption is requested at start of SMTP session (Recommended)\n"
                                            "- SSL/TLS: SMTP sessions are encrypted with SSL/TLS through a dedicated port (default: 465)")
    smtp_ssl_certificate = fields.Binary(
        'SSL Certificate', groups='base.group_system', attachment=False,
        help='SSL certificate used for authentication')
    smtp_ssl_private_key = fields.Binary(
        'SSL Private Key', groups='base.group_system', attachment=False,
        help='SSL private key used for authentication')
    smtp_debug = fields.Boolean(string='Debugging', help="If enabled, the full output of SMTP sessions will "
                                                         "be written to the server log at DEBUG level "
                                                         "(this is very verbose and may include confidential info!)")
    sequence = fields.Integer(string='Priority', default=10, help="When no specific mail server is requested for a mail, the highest priority one "
                                                                  "is used. Default priority is 10 (smaller number = higher priority)")
    active = fields.Boolean(default=True)

    @api.constrains('smtp_authentication', 'smtp_ssl_certificate', 'smtp_ssl_private_key')
    def _check_smtp_ssl_files(self):
        for mail_server in self:
            if mail_server.smtp_authentication == 'certificate':
                if not mail_server.smtp_ssl_private_key:
                    raise UserError(_('SSL private key is missing for %s.', mail_server.name))
                if not mail_server.smtp_ssl_certificate:
                    raise UserError(_('SSL certificate is missing for %s.', mail_server.name))

    def _get_test_email_addresses(self):
        self.ensure_one()
        if self.from_filter:
            if "@" in self.from_filter:
                # All emails will be sent from the same address
                return self.from_filter, "noreply@odoo.com"
            # All emails will be sent from any address in the same domain
            default_from = self.env["ir.config_parameter"].sudo().get_param("mail.default.from", "odoo")
            return f"{default_from}@{self.from_filter}", "noreply@odoo.com"
        # Fallback to current user email if there's no from filter
        email_from = self.env.user.email
        if not email_from:
            raise UserError(_('Please configure an email on the current user to simulate '
                              'sending an email message via this outgoing server'))
        return email_from, 'noreply@odoo.com'

    def test_smtp_connection(self):
        for server in self:
            smtp = False
            try:
                smtp = self.connect(mail_server_id=server.id)
                # simulate sending an email from current user's address - without sending it!
                email_from, email_to = server._get_test_email_addresses()
                # Testing the MAIL FROM step should detect sender filter problems
                (code, repl) = smtp.mail(email_from)
                if code != 250:
                    raise UserError(_('The server refused the sender address (%(email_from)s) '
                                      'with error %(repl)s') % locals())
                # Testing the RCPT TO step should detect most relaying problems
                (code, repl) = smtp.rcpt(email_to)
                if code not in (250, 251):
                    raise UserError(_('The server refused the test recipient (%(email_to)s) '
                                      'with error %(repl)s') % locals())
                # Beginning the DATA step should detect some deferred rejections
                # Can't use self.data() as it would actually send the mail!
                smtp.putcmd("data")
                (code, repl) = smtp.getreply()
                if code != 354:
                    raise UserError(_('The server refused the test connection '
                                      'with error %(repl)s') % locals())
            except UserError as e:
                # let UserErrors (messages) bubble up
                raise e
            except (UnicodeError, idna.core.InvalidCodepoint) as e:
                raise UserError(_("Invalid server name !\n %s", ustr(e)))
            except (gaierror, timeout) as e:
                raise UserError(_("No response received. Check server address and port number.\n %s", ustr(e)))
            except smtplib.SMTPServerDisconnected as e:
                raise UserError(_("The server has closed the connection unexpectedly. Check configuration served on this port number.\n %s", ustr(e.strerror)))
            except smtplib.SMTPResponseException as e:
                raise UserError(_("Server replied with following exception:\n %s", ustr(e.smtp_error)))
            except smtplib.SMTPNotSupportedError as e:
                raise UserError(_("An option is not supported by the server:\n %s", e.strerror))
            except smtplib.SMTPException as e:
                raise UserError(_("An SMTP exception occurred. Check port number and connection security type.\n %s", ustr(e)))
            except SSLError as e:
                raise UserError(_("An SSL exception occurred. Check connection security type.\n %s", ustr(e)))
            except Exception as e:
                raise UserError(_("Connection Test Failed! Here is what we got instead:\n %s", ustr(e)))
            finally:
                try:
                    if smtp:
                        smtp.close()
                except Exception:
                    # ignored, just a consequence of the previous exception
                    pass

        message = _("Connection Test Successful!")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }

    def connect(self, host=None, port=None, user=None, password=None, encryption=None,
                smtp_from=None, ssl_certificate=None, ssl_private_key=None, smtp_debug=False, mail_server_id=None):
        """Returns a new SMTP connection to the given SMTP server.
           When running in test mode, this method does nothing and returns `None`.

           :param host: host or IP of SMTP server to connect to, if mail_server_id not passed
           :param int port: SMTP port to connect to
           :param user: optional username to authenticate with
           :param password: optional password to authenticate with
           :param string encryption: optional, ``'ssl'`` | ``'starttls'``
           :param smtp_from: FROM SMTP envelop, used to find the best mail server
           :param ssl_certificate: filename of the SSL certificate used for authentication
               Used when no mail server is given and overwrite  the odoo-bin argument "smtp_ssl_certificate"
           :param ssl_private_key: filename of the SSL private key used for authentication
               Used when no mail server is given and overwrite  the odoo-bin argument "smtp_ssl_private_key"
           :param bool smtp_debug: toggle debugging of SMTP sessions (all i/o
                              will be output in logs)
           :param mail_server_id: ID of specific mail server to use (overrides other parameters)
        """
        # Do not actually connect while running in test mode
        if self._is_test_mode():
            return

        mail_server = smtp_encryption = None
        if mail_server_id:
            mail_server = self.sudo().browse(mail_server_id)
        elif not host:
            mail_server, smtp_from = self.sudo()._find_mail_server(smtp_from)

        if not mail_server:
            mail_server = self.env['ir.mail_server']
        ssl_context = None

        if mail_server:
            smtp_server = mail_server.smtp_host
            smtp_port = mail_server.smtp_port
            if mail_server.smtp_authentication == "login":
                smtp_user = mail_server.smtp_user
                smtp_password = mail_server.smtp_pass
            else:
                smtp_user = None
                smtp_password = None
            smtp_encryption = mail_server.smtp_encryption
            smtp_debug = smtp_debug or mail_server.smtp_debug
            from_filter = mail_server.from_filter
            if mail_server.smtp_authentication == "certificate":
                try:
                    ssl_context = PyOpenSSLContext(ssl.PROTOCOL_TLS)
                    smtp_ssl_certificate = base64.b64decode(mail_server.smtp_ssl_certificate)
                    certificate = SSLCrypto.load_certificate(FILETYPE_PEM, smtp_ssl_certificate)
                    smtp_ssl_private_key = base64.b64decode(mail_server.smtp_ssl_private_key)
                    private_key = SSLCrypto.load_privatekey(FILETYPE_PEM, smtp_ssl_private_key)
                    ssl_context._ctx.use_certificate(certificate)
                    ssl_context._ctx.use_privatekey(private_key)
                    # Check that the private key match the certificate
                    ssl_context._ctx.check_privatekey()
                except SSLCryptoError as e:
                    raise UserError(_('The private key or the certificate is not a valid file. \n%s', str(e)))
                except SSLError as e:
                    raise UserError(_('Could not load your certificate / private key. \n%s', str(e)))

        else:
            # we were passed individual smtp parameters or nothing and there is no default server
            smtp_server = host or tools.config.get('smtp_server')
            smtp_port = tools.config.get('smtp_port', 25) if port is None else port
            smtp_user = user or tools.config.get('smtp_user')
            smtp_password = password or tools.config.get('smtp_password')
            from_filter = self.env['ir.config_parameter'].sudo().get_param(
                'mail.default.from_filter', tools.config.get('from_filter'))
            smtp_encryption = encryption
            if smtp_encryption is None and tools.config.get('smtp_ssl'):
                smtp_encryption = 'starttls' # smtp_ssl => STARTTLS as of v7
            smtp_ssl_certificate_filename = ssl_certificate or tools.config.get('smtp_ssl_certificate_filename')
            smtp_ssl_private_key_filename = ssl_private_key or tools.config.get('smtp_ssl_private_key_filename')

            if smtp_ssl_certificate_filename and smtp_ssl_private_key_filename:
                try:
                    ssl_context = PyOpenSSLContext(ssl.PROTOCOL_TLS)
                    ssl_context.load_cert_chain(smtp_ssl_certificate_filename, keyfile=smtp_ssl_private_key_filename)
                    # Check that the private key match the certificate
                    ssl_context._ctx.check_privatekey()
                except SSLCryptoError as e:
                    raise UserError(_('The private key or the certificate is not a valid file. \n%s', str(e)))
                except SSLError as e:
                    raise UserError(_('Could not load your certificate / private key. \n%s', str(e)))

        if not smtp_server:
            raise UserError(
                (_("Missing SMTP Server") + "\n" +
                 _("Please define at least one SMTP server, "
                   "or provide the SMTP parameters explicitly.")))

        if smtp_encryption == 'ssl':
            if 'SMTP_SSL' not in smtplib.__all__:
                raise UserError(
                    _("Your Odoo Server does not support SMTP-over-SSL. "
                      "You could use STARTTLS instead. "
                       "If SSL is needed, an upgrade to Python 2.6 on the server-side "
                       "should do the trick."))
        connection = SMTPConnection(smtp_server, smtp_port, smtp_encryption, context=ssl_context)
        connection.set_debuglevel(smtp_debug)
        if smtp_encryption == 'starttls':
            # starttls() will perform ehlo() if needed first
            # and will discard the previous list of services
            # after successfully performing STARTTLS command,
            # (as per RFC 3207) so for example any AUTH
            # capability that appears only on encrypted channels
            # will be correctly detected for next step
            connection.starttls(context=ssl_context)

        if smtp_user:
            # Attempt authentication - will raise if AUTH service not supported
            local, at, domain = smtp_user.rpartition('@')
            if at:
                smtp_user = local + at + idna.encode(domain).decode('ascii')
            mail_server._smtp_login(connection, smtp_user, smtp_password or '')

        # Some methods of SMTP don't check whether EHLO/HELO was sent.
        # Anyway, as it may have been sent by login(), all subsequent usages should consider this command as sent.
        connection.ehlo_or_helo_if_needed()

        # Store the "from_filter" of the mail server / odoo-bin argument to  know if we
        # need to change the FROM headers or not when we will prepare the mail message
        connection.from_filter = from_filter
        connection.smtp_from = smtp_from

        return connection

    def _smtp_login(self, connection, smtp_user, smtp_password):
        """Authenticate the SMTP connection.

        Can be overridden in other module for different authentication methods.Can be
        called on the model itself or on a singleton.

        :param connection: The SMTP connection to authenticate
        :param smtp_user: The user to used for the authentication
        :param smtp_password: The password to used for the authentication
        """
        connection.login(smtp_user, smtp_password)

    def build_email(self, email_from, email_to, subject, body, email_cc=None, email_bcc=None, reply_to=False,
                    attachments=None, message_id=None, references=None, object_id=False, subtype='plain', headers=None,
                    body_alternative=None, subtype_alternative='plain'):
        """Constructs an RFC2822 email.message.Message object based on the keyword arguments passed, and returns it.

           :param string email_from: sender email address
           :param list email_to: list of recipient addresses (to be joined with commas)
           :param string subject: email subject (no pre-encoding/quoting necessary)
           :param string body: email body, of the type ``subtype`` (by default, plaintext).
                               If html subtype is used, the message will be automatically converted
                               to plaintext and wrapped in multipart/alternative, unless an explicit
                               ``body_alternative`` version is passed.
           :param string body_alternative: optional alternative body, of the type specified in ``subtype_alternative``
           :param string reply_to: optional value of Reply-To header
           :param string object_id: optional tracking identifier, to be included in the message-id for
                                    recognizing replies. Suggested format for object-id is "res_id-model",
                                    e.g. "12345-crm.lead".
           :param string subtype: optional mime subtype for the text body (usually 'plain' or 'html'),
                                  must match the format of the ``body`` parameter. Default is 'plain',
                                  making the content part of the mail "text/plain".
           :param string subtype_alternative: optional mime subtype of ``body_alternative`` (usually 'plain'
                                              or 'html'). Default is 'plain'.
           :param list attachments: list of (filename, filecontents) pairs, where filecontents is a string
                                    containing the bytes of the attachment
           :param list email_cc: optional list of string values for CC header (to be joined with commas)
           :param list email_bcc: optional list of string values for BCC header (to be joined with commas)
           :param dict headers: optional map of headers to set on the outgoing mail (may override the
                                other headers, including Subject, Reply-To, Message-Id, etc.)
           :rtype: email.message.EmailMessage
           :return: the new RFC2822 email message
        """
        email_from = email_from or self._get_default_from_address()
        assert email_from, "You must either provide a sender address explicitly or configure "\
                           "using the combination of `mail.catchall.domain` and `mail.default.from` "\
                           "ICPs, in the server configuration file or with the "\
                           "--email-from startup parameter."

        headers = headers or {}         # need valid dict later
        email_cc = email_cc or []
        email_bcc = email_bcc or []
        body = body or u''

        msg = EmailMessage(policy=email.policy.SMTP)
        if not message_id:
            if object_id:
                message_id = tools.generate_tracking_message_id(object_id)
            else:
                message_id = make_msgid()
        msg['Message-Id'] = message_id
        if references:
            msg['references'] = references
        msg['Subject'] = subject
        msg['From'] = email_from
        del msg['Reply-To']
        msg['Reply-To'] = reply_to or email_from
        msg['To'] = email_to
        if email_cc:
            msg['Cc'] = email_cc
        if email_bcc:
            msg['Bcc'] = email_bcc
        msg['Date'] = datetime.datetime.utcnow()
        for key, value in headers.items():
            msg[pycompat.to_text(ustr(key))] = value

        email_body = ustr(body)
        if subtype == 'html' and not body_alternative:
            msg['MIME-Version'] = '1.0'
            msg.add_alternative(tools.html2plaintext(email_body), subtype='plain', charset='utf-8')
            msg.add_alternative(email_body, subtype=subtype, charset='utf-8')
        elif body_alternative:
            msg['MIME-Version'] = '1.0'
            msg.add_alternative(ustr(body_alternative), subtype=subtype_alternative, charset='utf-8')
            msg.add_alternative(email_body, subtype=subtype, charset='utf-8')
        else:
            msg.set_content(email_body, subtype=subtype, charset='utf-8')

        if attachments:
            for (fname, fcontent, mime) in attachments:
                maintype, subtype = mime.split('/') if mime and '/' in mime else ('application', 'octet-stream')
                msg.add_attachment(fcontent, maintype, subtype, filename=fname)
        return msg

    @api.model
    def _get_default_bounce_address(self):
        '''Compute the default bounce address.

        The default bounce address is used to set the envelop address if no
        envelop address is provided in the message.  It is formed by properly
        joining the parameters "mail.bounce.alias" and
        "mail.catchall.domain".

        If "mail.bounce.alias" is not set it defaults to "postmaster-odoo".

        If "mail.catchall.domain" is not set, return None.

        '''
        get_param = self.env['ir.config_parameter'].sudo().get_param
        postmaster = get_param('mail.bounce.alias', default='postmaster-odoo')
        domain = get_param('mail.catchall.domain')
        if postmaster and domain:
            return '%s@%s' % (postmaster, domain)

    @api.model
    def _get_default_from_address(self):
        """Compute the default from address.

        Used for the "header from" address when no other has been received.

        :return str/None:
            If the config parameter ``mail.default.from`` contains
            a full email address, return it.
            Otherwise, combines config parameters ``mail.default.from`` and
            ``mail.catchall.domain`` to generate a default sender address.

            If some of those parameters is not defined, it will default to the
            ``--email-from`` CLI/config parameter.
        """
        get_param = self.env['ir.config_parameter'].sudo().get_param
        email_from = get_param("mail.default.from")
        if email_from and "@" in email_from:
            return email_from
        domain = get_param("mail.catchall.domain")
        if email_from and domain:
            return "%s@%s" % (email_from, domain)
        return tools.config.get("email_from")

    def _prepare_email_message(self, message, smtp_session):
        """Prepare the SMTP information (from, to, message) before sending.

        :param message: the email.message.Message to send, information like the
            Return-Path, the From, etc... will be used to find the smtp_from and to smtp_to
        :param smtp_session: the opened SMTP session to use to authenticate the sender
        :return: smtp_from, smtp_to_list, message
            smtp_from: email to used during the authentication to the mail server
            smtp_to_list: list of email address which will receive the email
            message: the email.message.Message to send
        """
        # Use the default bounce address **only if** no Return-Path was
        # provided by caller.  Caller may be using Variable Envelope Return
        # Path (VERP) to detect no-longer valid email addresses.
        bounce_address = message['Return-Path'] or self._get_default_bounce_address() or message['From']
        smtp_from = message['From'] or bounce_address
        assert smtp_from, "The Return-Path or From header is required for any outbound email"

        email_to = message['To']
        email_cc = message['Cc']
        email_bcc = message['Bcc']
        del message['Bcc']

        # All recipient addresses must only contain ASCII characters
        smtp_to_list = [
            address
            for base in [email_to, email_cc, email_bcc]
            for address in extract_rfc2822_addresses(base)
            if address
        ]
        assert smtp_to_list, self.NO_VALID_RECIPIENT

        x_forge_to = message['X-Forge-To']
        if x_forge_to:
            # `To:` header forged, e.g. for posting on mail.channels, to avoid confusion
            del message['X-Forge-To']
            del message['To']           # avoid multiple To: headers!
            message['To'] = x_forge_to

        # Try to not spoof the mail from headers
        from_filter = getattr(smtp_session, 'from_filter', False)
        smtp_from = getattr(smtp_session, 'smtp_from', False) or smtp_from

        notifications_email = email_normalize(self._get_default_from_address())
        if notifications_email and smtp_from == notifications_email and message['From'] != notifications_email:
            smtp_from = encapsulate_email(message['From'], notifications_email)

        if message['From'] != smtp_from:
            del message['From']
            message['From'] = smtp_from

        # Check if it's still possible to put the bounce address as smtp_from
        if self._match_from_filter(bounce_address, from_filter):
            # Mail headers FROM will be spoofed to be able to receive bounce notifications
            # Because the mail server support the domain of the bounce address
            smtp_from = bounce_address

        # The email's "Envelope From" (Return-Path) must only contain ASCII characters.
        smtp_from_rfc2822 = extract_rfc2822_addresses(smtp_from)
        assert smtp_from_rfc2822, (
            f"Malformed 'Return-Path' or 'From' address: {smtp_from} - "
            "It should contain one valid plain ASCII email")
        smtp_from = smtp_from_rfc2822[-1]

        return smtp_from, smtp_to_list, message

    @api.model
    def send_email(self, message, mail_server_id=None, smtp_server=None, smtp_port=None,
                   smtp_user=None, smtp_password=None, smtp_encryption=None,
                   smtp_ssl_certificate=None, smtp_ssl_private_key=None,
                   smtp_debug=False, smtp_session=None):
        """Sends an email directly (no queuing).

        No retries are done, the caller should handle MailDeliveryException in order to ensure that
        the mail is never lost.

        If the mail_server_id is provided, sends using this mail server, ignoring other smtp_* arguments.
        If mail_server_id is None and smtp_server is None, use the default mail server (highest priority).
        If mail_server_id is None and smtp_server is not None, use the provided smtp_* arguments.
        If both mail_server_id and smtp_server are None, look for an 'smtp_server' value in server config,
        and fails if not found.

        :param message: the email.message.Message to send. The envelope sender will be extracted from the
                        ``Return-Path`` (if present), or will be set to the default bounce address.
                        The envelope recipients will be extracted from the combined list of ``To``,
                        ``CC`` and ``BCC`` headers.
        :param smtp_session: optional pre-established SMTP session. When provided,
                             overrides `mail_server_id` and all the `smtp_*` parameters.
                             Passing the matching `mail_server_id` may yield better debugging/log
                             messages. The caller is in charge of disconnecting the session.
        :param mail_server_id: optional id of ir.mail_server to use for sending. overrides other smtp_* arguments.
        :param smtp_server: optional hostname of SMTP server to use
        :param smtp_encryption: optional TLS mode, one of 'none', 'starttls' or 'ssl' (see ir.mail_server fields for explanation)
        :param smtp_port: optional SMTP port, if mail_server_id is not passed
        :param smtp_user: optional SMTP user, if mail_server_id is not passed
        :param smtp_password: optional SMTP password to use, if mail_server_id is not passed
        :param smtp_ssl_certificate: filename of the SSL certificate used for authentication
        :param smtp_ssl_private_key: filename of the SSL private key used for authentication
        :param smtp_debug: optional SMTP debug flag, if mail_server_id is not passed
        :return: the Message-ID of the message that was just sent, if successfully sent, otherwise raises
                 MailDeliveryException and logs root cause.
        """
        smtp = smtp_session
        if not smtp:
            smtp = self.connect(
                smtp_server, smtp_port, smtp_user, smtp_password, smtp_encryption,
                smtp_from=message['From'], ssl_certificate=smtp_ssl_certificate, ssl_private_key=smtp_ssl_private_key,
                smtp_debug=smtp_debug, mail_server_id=mail_server_id,)

        smtp_from, smtp_to_list, message = self._prepare_email_message(message, smtp)

        # Do not actually send emails in testing mode!
        if self._is_test_mode():
            _test_logger.info("skip sending email in test mode")
            return message['Message-Id']

        try:
            message_id = message['Message-Id']

            if sys.version_info < (3, 7, 4):
                # header folding code is buggy and adds redundant carriage
                # returns, it got fixed in 3.7.4 thanks to bpo-34424
                message_str = message.as_string()
                message_str = re.sub('\r+(?!\n)', '', message_str)

                mail_options = []
                if any((not is_ascii(addr) for addr in smtp_to_list + [smtp_from])):
                    # non ascii email found, require SMTPUTF8 extension,
                    # the relay may reject it
                    mail_options.append("SMTPUTF8")
                smtp.sendmail(smtp_from, smtp_to_list, message_str, mail_options=mail_options)
            else:
                smtp.send_message(message, smtp_from, smtp_to_list)

            # do not quit() a pre-established smtp_session
            if not smtp_session:
                smtp.quit()
        except smtplib.SMTPServerDisconnected:
            raise
        except Exception as e:
            params = (ustr(smtp_server), e.__class__.__name__, ustr(e))
            msg = _("Mail delivery failed via SMTP server '%s'.\n%s: %s", *params)
            _logger.info(msg)
            raise MailDeliveryException(_("Mail Delivery Failed"), msg)
        return message_id

    def _find_mail_server(self, email_from, mail_servers=None):
        """Find the appropriate mail server for the given email address.

        Returns: Record<ir.mail_server>, email_from
        - Mail server to use to send the email (None if we use the odoo-bin arguments)
        - Email FROM to use to send the email (in some case, it might be impossible
          to use the given email address directly if no mail server is configured for)
        """
        email_from_normalized = email_normalize(email_from)
        email_from_domain = email_domain_extract(email_from_normalized)
        notifications_email = email_normalize(self._get_default_from_address())
        notifications_domain = email_domain_extract(notifications_email)

        if mail_servers is None:
            mail_servers = self.sudo().search([], order='sequence')

        # 1. Try to find a mail server for the right mail from
        mail_server = mail_servers.filtered(lambda m: email_normalize(m.from_filter) == email_from_normalized)
        if mail_server:
            return mail_server[0], email_from

        mail_server = mail_servers.filtered(lambda m: email_domain_normalize(m.from_filter) == email_from_domain)
        if mail_server:
            return mail_server[0], email_from

        # 2. Try to find a mail server for <notifications@domain.com>
        if notifications_email:
            mail_server = mail_servers.filtered(lambda m: email_normalize(m.from_filter) == notifications_email)
            if mail_server:
                return mail_server[0], notifications_email

            mail_server = mail_servers.filtered(lambda m: email_domain_normalize(m.from_filter) == notifications_domain)
            if mail_server:
                return mail_server[0], notifications_email

        # 3. Take the first mail server without "from_filter" because
        # nothing else has been found... Will spoof the FROM because
        # we have no other choices (will use the notification email if available
        # otherwise we will use the user email)
        mail_server = mail_servers.filtered(lambda m: not m.from_filter)
        if mail_server:
            return mail_server[0], notifications_email or email_from

        # 4. Return the first mail server even if it was configured for another domain
        if mail_servers:
            _logger.warning(
                "No mail server matches the from_filter, using %s as fallback",
                notifications_email or email_from)
            return mail_servers[0], notifications_email or email_from

        # 5: SMTP config in odoo-bin arguments
        from_filter = self.env['ir.config_parameter'].sudo().get_param(
            'mail.default.from_filter', tools.config.get('from_filter'))

        if self._match_from_filter(email_from, from_filter):
            return None, email_from

        if notifications_email and self._match_from_filter(notifications_email, from_filter):
            return None, notifications_email

        _logger.warning(
            "The from filter of the CLI configuration does not match the notification email "
            "or the user email, using %s as fallback",
            notifications_email or email_from)
        return None, notifications_email or email_from

    @api.model
    def _match_from_filter(self, email_from, from_filter):
        """Return True is the given email address match the "from_filter" field.

        The from filter can be Falsy (always match),
        a domain name or an full email address.
        """
        if not from_filter:
            return True

        normalized_mail_from = email_normalize(email_from)
        if '@' in from_filter:
            return email_normalize(from_filter) == normalized_mail_from

        return email_domain_extract(normalized_mail_from) == email_domain_normalize(from_filter)

    @api.onchange('smtp_encryption')
    def _onchange_encryption(self):
        result = {}
        if self.smtp_encryption == 'ssl':
            self.smtp_port = 465
            if not 'SMTP_SSL' in smtplib.__all__:
                result['warning'] = {
                    'title': _('Warning'),
                    'message': _('Your server does not seem to support SSL, you may want to try STARTTLS instead'),
                }
        else:
            self.smtp_port = 25
        return result

    def _is_test_mode(self):
        """Return True if we are running the tests, so we do not send real emails.

        Can be overridden in tests after mocking the SMTP lib to test in depth the
        outgoing mail server.
        """
        return getattr(threading.current_thread(), 'testing', False) or self.env.registry.in_test_mode()
