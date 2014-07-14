# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011-2012 OpenERP S.A (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.charset import Charset
from email.header import Header
from email.utils import formatdate, make_msgid, COMMASPACE
from email import Encoders
import logging
import re
import smtplib
import threading

from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tools import html2text
import openerp.tools as tools

# ustr was originally from tools.misc.
# it is moved to loglevels until we refactor tools.
from openerp.loglevels import ustr

_logger = logging.getLogger(__name__)
_test_logger = logging.getLogger('openerp.tests')


class MailDeliveryException(osv.except_osv):
    """Specific exception subclass for mail delivery errors"""
    def __init__(self, name, value):
        super(MailDeliveryException, self).__init__(name, value)

class WriteToLogger(object):
    """debugging helper: behave as a fd and pipe to logger at the given level"""
    def __init__(self, logger, level=logging.DEBUG):
        self.logger = logger
        self.level = level

    def write(self, s):
        self.logger.log(self.level, s)


def try_coerce_ascii(string_utf8):
    """Attempts to decode the given utf8-encoded string
       as ASCII after coercing it to UTF-8, then return
       the confirmed 7-bit ASCII string.

       If the process fails (because the string
       contains non-ASCII characters) returns ``None``.
    """
    try:
        string_utf8.decode('ascii')
    except UnicodeDecodeError:
        return
    return string_utf8

def encode_header(header_text):
    """Returns an appropriate representation of the given header value,
       suitable for direct assignment as a header value in an
       email.message.Message. RFC2822 assumes that headers contain
       only 7-bit characters, so we ensure it is the case, using
       RFC2047 encoding when needed.

       :param header_text: unicode or utf-8 encoded string with header value
       :rtype: string | email.header.Header
       :return: if ``header_text`` represents a plain ASCII string,
                return the same 7-bit string, otherwise returns an email.header.Header
                that will perform the appropriate RFC2047 encoding of
                non-ASCII values.
    """
    if not header_text: return ""
    # convert anything to utf-8, suitable for testing ASCIIness, as 7-bit chars are
    # encoded as ASCII in utf-8
    header_text_utf8 = tools.ustr(header_text).encode('utf-8')
    header_text_ascii = try_coerce_ascii(header_text_utf8)
    # if this header contains non-ASCII characters,
    # we'll need to wrap it up in a message.header.Header
    # that will take care of RFC2047-encoding it as
    # 7-bit string.
    return header_text_ascii if header_text_ascii\
         else Header(header_text_utf8, 'utf-8')

def encode_header_param(param_text):
    """Returns an appropriate RFC2047 encoded representation of the given
       header parameter value, suitable for direct assignation as the
       param value (e.g. via Message.set_param() or Message.add_header())
       RFC2822 assumes that headers contain only 7-bit characters,
       so we ensure it is the case, using RFC2047 encoding when needed.

       :param param_text: unicode or utf-8 encoded string with header value
       :rtype: string
       :return: if ``param_text`` represents a plain ASCII string,
                return the same 7-bit string, otherwise returns an
                ASCII string containing the RFC2047 encoded text.
    """
    # For details see the encode_header() method that uses the same logic
    if not param_text: return ""
    param_text_utf8 = tools.ustr(param_text).encode('utf-8')
    param_text_ascii = try_coerce_ascii(param_text_utf8)
    return param_text_ascii if param_text_ascii\
         else Charset('utf8').header_encode(param_text_utf8)

name_with_email_pattern = re.compile(r'("[^<@>]+")\s*<([^ ,<@]+@[^> ,]+)>')
address_pattern = re.compile(r'([^ ,<@]+@[^> ,]+)')

def extract_rfc2822_addresses(text):
    """Returns a list of valid RFC2822 addresses
       that can be found in ``source``, ignoring 
       malformed ones and non-ASCII ones.
    """
    if not text: return []
    candidates = address_pattern.findall(tools.ustr(text).encode('utf-8'))
    return filter(try_coerce_ascii, candidates)

def encode_rfc2822_address_header(header_text):
    """If ``header_text`` contains non-ASCII characters,
       attempts to locate patterns of the form
       ``"Name" <address@domain>`` and replace the
       ``"Name"`` portion by the RFC2047-encoded
       version, preserving the address part untouched.
    """
    header_text_utf8 = tools.ustr(header_text).encode('utf-8')
    header_text_ascii = try_coerce_ascii(header_text_utf8)
    if header_text_ascii:
        return header_text_ascii
    # non-ASCII characters are present, attempt to
    # replace all "Name" patterns with the RFC2047-
    # encoded version
    def replace(match_obj):
        name, email = match_obj.group(1), match_obj.group(2)
        name_encoded = str(Header(name, 'utf-8'))
        return "%s <%s>" % (name_encoded, email)
    header_text_utf8 = name_with_email_pattern.sub(replace,
                                                   header_text_utf8)
    # try again after encoding
    header_text_ascii = try_coerce_ascii(header_text_utf8)
    if header_text_ascii:
        return header_text_ascii
    # fallback to extracting pure addresses only, which could
    # still cause a failure downstream if the actual addresses
    # contain non-ASCII characters
    return COMMASPACE.join(extract_rfc2822_addresses(header_text_utf8))

 
class ir_mail_server(osv.osv):
    """Represents an SMTP server, able to send outgoing emails, with SSL and TLS capabilities."""
    _name = "ir.mail_server"

    _columns = {
        'name': fields.char('Description', required=True, select=True),
        'smtp_host': fields.char('SMTP Server', required=True, help="Hostname or IP of SMTP server"),
        'smtp_port': fields.integer('SMTP Port', size=5, required=True, help="SMTP Port. Usually 465 for SSL, and 25 or 587 for other cases."),
        'smtp_user': fields.char('Username', size=64, help="Optional username for SMTP authentication"),
        'smtp_pass': fields.char('Password', size=64, help="Optional password for SMTP authentication"),
        'smtp_encryption': fields.selection([('none','None'),
                                             ('starttls','TLS (STARTTLS)'),
                                             ('ssl','SSL/TLS')],
                                            string='Connection Security', required=True,
                                            help="Choose the connection encryption scheme:\n"
                                                 "- None: SMTP sessions are done in cleartext.\n"
                                                 "- TLS (STARTTLS): TLS encryption is requested at start of SMTP session (Recommended)\n"
                                                 "- SSL/TLS: SMTP sessions are encrypted with SSL/TLS through a dedicated port (default: 465)"),
        'smtp_debug': fields.boolean('Debugging', help="If enabled, the full output of SMTP sessions will "
                                                       "be written to the server log at DEBUG level"
                                                       "(this is very verbose and may include confidential info!)"),
        'sequence': fields.integer('Priority', help="When no specific mail server is requested for a mail, the highest priority one "
                                                    "is used. Default priority is 10 (smaller number = higher priority)"),
        'active': fields.boolean('Active')
    }

    _defaults = {
         'smtp_port': 25,
         'active': True,
         'sequence': 10,
         'smtp_encryption': 'none',
     }

    def __init__(self, *args, **kwargs):
        # Make sure we pipe the smtplib outputs to our own DEBUG logger
        if not isinstance(smtplib.stderr, WriteToLogger):
            logpiper = WriteToLogger(_logger)
            smtplib.stderr = logpiper
            smtplib.stdout = logpiper
        super(ir_mail_server, self).__init__(*args,**kwargs)

    def name_get(self, cr, uid, ids, context=None):
        return [(a["id"], "(%s)" % (a['name'])) for a in self.read(cr, uid, ids, ['name'], context=context)]

    def test_smtp_connection(self, cr, uid, ids, context=None):
        for smtp_server in self.browse(cr, uid, ids, context=context):
            smtp = False
            try:
                smtp = self.connect(smtp_server.smtp_host, smtp_server.smtp_port, user=smtp_server.smtp_user,
                                    password=smtp_server.smtp_pass, encryption=smtp_server.smtp_encryption,
                                    smtp_debug=smtp_server.smtp_debug)
            except Exception, e:
                raise osv.except_osv(_("Connection Test Failed!"), _("Here is what we got instead:\n %s") % tools.ustr(e))
            finally:
                try:
                    if smtp: smtp.quit()
                except Exception:
                    # ignored, just a consequence of the previous exception
                    pass
        raise osv.except_osv(_("Connection Test Succeeded!"), _("Everything seems properly set up!"))

    def connect(self, host, port, user=None, password=None, encryption=False, smtp_debug=False):
        """Returns a new SMTP connection to the give SMTP server, authenticated
           with ``user`` and ``password`` if provided, and encrypted as requested
           by the ``encryption`` parameter.
        
           :param host: host or IP of SMTP server to connect to
           :param int port: SMTP port to connect to
           :param user: optional username to authenticate with
           :param password: optional password to authenticate with
           :param string encryption: optional, ``'ssl'`` | ``'starttls'``
           :param bool smtp_debug: toggle debugging of SMTP sessions (all i/o
                              will be output in logs)
        """
        if encryption == 'ssl':
            if not 'SMTP_SSL' in smtplib.__all__:
                raise osv.except_osv(
                             _("SMTP-over-SSL mode unavailable"),
                             _("Your OpenERP Server does not support SMTP-over-SSL. You could use STARTTLS instead."
                               "If SSL is needed, an upgrade to Python 2.6 on the server-side should do the trick."))
            connection = smtplib.SMTP_SSL(host, port)
        else:
            connection = smtplib.SMTP(host, port)
        connection.set_debuglevel(smtp_debug)
        if encryption == 'starttls':
            # starttls() will perform ehlo() if needed first
            # and will discard the previous list of services
            # after successfully performing STARTTLS command,
            # (as per RFC 3207) so for example any AUTH
            # capability that appears only on encrypted channels
            # will be correctly detected for next step
            connection.starttls()

        if user:
            # Attempt authentication - will raise if AUTH service not supported
            # The user/password must be converted to bytestrings in order to be usable for
            # certain hashing schemes, like HMAC.
            # See also bug #597143 and python issue #5285
            user = tools.ustr(user).encode('utf-8')
            password = tools.ustr(password).encode('utf-8') 
            connection.login(user, password)
        return connection

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
           :rtype: email.message.Message (usually MIMEMultipart)
           :return: the new RFC2822 email message
        """
        email_from = email_from or tools.config.get('email_from')
        assert email_from, "You must either provide a sender address explicitly or configure "\
                           "a global sender address in the server configuration or with the "\
                           "--email-from startup parameter."

        # Note: we must force all strings to to 8-bit utf-8 when crafting message,
        #       or use encode_header() for headers, which does it automatically.

        headers = headers or {} # need valid dict later

        if not email_cc: email_cc = []
        if not email_bcc: email_bcc = []
        if not body: body = u''

        email_body_utf8 = ustr(body).encode('utf-8')
        email_text_part = MIMEText(email_body_utf8, _subtype=subtype, _charset='utf-8')
        msg = MIMEMultipart()

        if not message_id:
            if object_id:
                message_id = tools.generate_tracking_message_id(object_id)
            else:
                message_id = make_msgid()
        msg['Message-Id'] = encode_header(message_id)
        if references:
            msg['references'] = encode_header(references)
        msg['Subject'] = encode_header(subject)
        msg['From'] = encode_rfc2822_address_header(email_from)
        del msg['Reply-To']
        if reply_to:
            msg['Reply-To'] = encode_rfc2822_address_header(reply_to)
        else:
            msg['Reply-To'] = msg['From']
        msg['To'] = encode_rfc2822_address_header(COMMASPACE.join(email_to))
        if email_cc:
            msg['Cc'] = encode_rfc2822_address_header(COMMASPACE.join(email_cc))
        if email_bcc:
            msg['Bcc'] = encode_rfc2822_address_header(COMMASPACE.join(email_bcc))
        msg['Date'] = formatdate()
        # Custom headers may override normal headers or provide additional ones
        for key, value in headers.iteritems():
            msg[ustr(key).encode('utf-8')] = encode_header(value)

        if subtype == 'html' and not body_alternative and html2text:
            # Always provide alternative text body ourselves if possible.
            text_utf8 = tools.html2text(email_body_utf8.decode('utf-8')).encode('utf-8')
            alternative_part = MIMEMultipart(_subtype="alternative")
            alternative_part.attach(MIMEText(text_utf8, _charset='utf-8', _subtype='plain'))
            alternative_part.attach(email_text_part)
            msg.attach(alternative_part)
        elif body_alternative:
            # Include both alternatives, as specified, within a multipart/alternative part
            alternative_part = MIMEMultipart(_subtype="alternative")
            body_alternative_utf8 = ustr(body_alternative).encode('utf-8')
            alternative_body_part = MIMEText(body_alternative_utf8, _subtype=subtype_alternative, _charset='utf-8')
            alternative_part.attach(alternative_body_part)
            alternative_part.attach(email_text_part)
            msg.attach(alternative_part)
        else:
            msg.attach(email_text_part)

        if attachments:
            for (fname, fcontent) in attachments:
                filename_rfc2047 = encode_header_param(fname)
                part = MIMEBase('application', "octet-stream")

                # The default RFC2231 encoding of Message.add_header() works in Thunderbird but not GMail
                # so we fix it by using RFC2047 encoding for the filename instead.
                part.set_param('name', filename_rfc2047)
                part.add_header('Content-Disposition', 'attachment', filename=filename_rfc2047)

                part.set_payload(fcontent)
                Encoders.encode_base64(part)
                msg.attach(part)
        return msg

    def send_email(self, cr, uid, message, mail_server_id=None, smtp_server=None, smtp_port=None,
                   smtp_user=None, smtp_password=None, smtp_encryption=None, smtp_debug=False,
                   context=None):
        """Sends an email directly (no queuing).

        No retries are done, the caller should handle MailDeliveryException in order to ensure that
        the mail is never lost.

        If the mail_server_id is provided, sends using this mail server, ignoring other smtp_* arguments.
        If mail_server_id is None and smtp_server is None, use the default mail server (highest priority).
        If mail_server_id is None and smtp_server is not None, use the provided smtp_* arguments.
        If both mail_server_id and smtp_server are None, look for an 'smtp_server' value in server config,
        and fails if not found.

        :param message: the email.message.Message to send. The envelope sender will be extracted from the
                        ``Return-Path`` or ``From`` headers. The envelope recipients will be
                        extracted from the combined list of ``To``, ``CC`` and ``BCC`` headers.
        :param mail_server_id: optional id of ir.mail_server to use for sending. overrides other smtp_* arguments.
        :param smtp_server: optional hostname of SMTP server to use
        :param smtp_encryption: optional TLS mode, one of 'none', 'starttls' or 'ssl' (see ir.mail_server fields for explanation)
        :param smtp_port: optional SMTP port, if mail_server_id is not passed
        :param smtp_user: optional SMTP user, if mail_server_id is not passed
        :param smtp_password: optional SMTP password to use, if mail_server_id is not passed
        :param smtp_debug: optional SMTP debug flag, if mail_server_id is not passed
        :return: the Message-ID of the message that was just sent, if successfully sent, otherwise raises
                 MailDeliveryException and logs root cause.
        """
        smtp_from = message['Return-Path'] or message['From']
        assert smtp_from, "The Return-Path or From header is required for any outbound email"

        # The email's "Envelope From" (Return-Path), and all recipient addresses must only contain ASCII characters.
        from_rfc2822 = extract_rfc2822_addresses(smtp_from)
        assert from_rfc2822, ("Malformed 'Return-Path' or 'From' address: %r - "
                              "It should contain one valid plain ASCII email") % smtp_from
        # use last extracted email, to support rarities like 'Support@MyComp <support@mycompany.com>'
        smtp_from = from_rfc2822[-1]
        email_to = message['To']
        email_cc = message['Cc']
        email_bcc = message['Bcc']
        
        smtp_to_list = filter(None, tools.flatten(map(extract_rfc2822_addresses,[email_to, email_cc, email_bcc])))
        assert smtp_to_list, "At least one valid recipient address should be specified for outgoing emails (To/Cc/Bcc)"

        # Do not actually send emails in testing mode!
        if getattr(threading.currentThread(), 'testing', False):
            _test_logger.info("skip sending email in test mode")
            return message['Message-Id']

        # Get SMTP Server Details from Mail Server
        mail_server = None
        if mail_server_id:
            mail_server = self.browse(cr, SUPERUSER_ID, mail_server_id)
        elif not smtp_server:
            mail_server_ids = self.search(cr, SUPERUSER_ID, [], order='sequence', limit=1)
            if mail_server_ids:
                mail_server = self.browse(cr, SUPERUSER_ID, mail_server_ids[0])

        if mail_server:
            smtp_server = mail_server.smtp_host
            smtp_user = mail_server.smtp_user
            smtp_password = mail_server.smtp_pass
            smtp_port = mail_server.smtp_port
            smtp_encryption = mail_server.smtp_encryption
            smtp_debug = smtp_debug or mail_server.smtp_debug
        else:
            # we were passed an explicit smtp_server or nothing at all
            smtp_server = smtp_server or tools.config.get('smtp_server')
            smtp_port = tools.config.get('smtp_port', 25) if smtp_port is None else smtp_port
            smtp_user = smtp_user or tools.config.get('smtp_user')
            smtp_password = smtp_password or tools.config.get('smtp_password')
            if smtp_encryption is None and tools.config.get('smtp_ssl'):
                smtp_encryption = 'starttls' # STARTTLS is the new meaning of the smtp_ssl flag as of v7.0

        if not smtp_server:
            raise osv.except_osv(
                         _("Missing SMTP Server"),
                         _("Please define at least one SMTP server, or provide the SMTP parameters explicitly."))

        try:
            message_id = message['Message-Id']

            # Add email in Maildir if smtp_server contains maildir.
            if smtp_server.startswith('maildir:/'):
                from mailbox import Maildir
                maildir_path = smtp_server[8:]
                mdir = Maildir(maildir_path, factory=None, create = True)
                mdir.add(message.as_string(True))
                return message_id

            smtp = None
            try:
                smtp = self.connect(smtp_server, smtp_port, smtp_user, smtp_password, smtp_encryption or False, smtp_debug)
                smtp.sendmail(smtp_from, smtp_to_list, message.as_string())
            finally:
                if smtp is not None:
                    smtp.quit()
        except Exception, e:
            msg = _("Mail delivery failed via SMTP server '%s'.\n%s: %s") % (tools.ustr(smtp_server),
                                                                             e.__class__.__name__,
                                                                             tools.ustr(e))
            _logger.error(msg)
            raise MailDeliveryException(_("Mail Delivery Failed"), msg)
        return message_id

    def on_change_encryption(self, cr, uid, ids, smtp_encryption):
        if smtp_encryption == 'ssl':
            result = {'value': {'smtp_port': 465}}
            if not 'SMTP_SSL' in smtplib.__all__:
                result['warning'] = {'title': _('Warning'),
                                     'message': _('Your server does not seem to support SSL, you may want to try STARTTLS instead')}
        else:
            result = {'value': {'smtp_port': 25}}
        return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
