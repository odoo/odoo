# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 OpenERP S.A (<http://www.openerp.com>)
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

from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.Header import Header
from email.Utils import formatdate, make_msgid, COMMASPACE
from email import Encoders
import logging
import smtplib

from osv import osv
from osv import fields
from openerp.tools.translate import _
from openerp.tools import html2text
from openerp.tools.func import wraps
import openerp.tools as tools

# ustr was originally from tools.misc.
# it is moved to loglevels until we refactor tools.
from openerp.loglevels import ustr

_logger = logging.getLogger('ir.mail_server')

class MailDeliveryException(osv.except_osv):
    """Specific exception subclass for mail delivery errors"""
    def __init__(self, name, value, exc_type='warning'):
        super(MailDeliveryException, self).__init__(name, value, exc_type=exc_type)

class WriteToLogger(object):
    """debugging helper: behave as a fd and pipe to logger at the given level"""
    def __init__(self, logger, level=logging.DEBUG):
        self.logger = logger
        self.level = level

    def write(self, s):
        self.logger.log(self.level, s)

def encode_header(header_text):
    """Returns an appropriate representation of the given header value,
       suitable for direct assignment as a header value in an
       email.message.Message. RFC2822 assumes that headers contain
       only 7-bit characters, so we ensure it is the case, using
       RFC2047 encoding when needed.

       :param header_text: unicode or utf-8 encoded string with header value
       :rtype: string | email.header.Header
       :return: if ``header_text`` represents a plain ASCII string,
                return a 7-bit string, otherwise returns an email.header.Header
                that will perform the appropriate RFC2047 encoding of
                non-ASCII values.
    """
    if not header_text: return ""

    # convert anything to utf-8, suitable for
    # testing ASCIIness, as 7-bit chars are
    # encoded as ASCII in utf-8
    header_text_utf8 = tools.ustr(header_text).encode('utf-8')

    # check for non-ascii content in the header value
    try:
        header_text_utf8.decode('ascii')
        # was plain ascii, we can use it verbatim as 
        # a header
        return header_text_utf8
    except UnicodeDecodeError:
        # this header contains non-ASCII characters, so
        # we need to wrap it up in a message.header.Header
        # that will take care of RFC2047-encoding it as
        # 7-bit string.
        return Header(header_text_utf8, 'utf-8')
 
class ir_mail_server(osv.osv):
    """Represents an SMTP server, able to send outgoing e-mails, with SSL and TLS capabilities."""
    _name = "ir.mail_server"

    _columns = {
        'name': fields.char('Description', size=64, required=True, select=True),
        'smtp_host': fields.char('Server Name', size=128, required=True, help="Hostname or IP of SMTP server"),
        'smtp_port': fields.integer('SMTP Port', size=5, required=True, help="SMTP Port. Usually 465 for SSL, and 25 or 587 for other cases."),
        'smtp_user': fields.char('Username', size=64, help="Optional username for SMTP authentication"),
        'smtp_pass': fields.char('Password', size=64, help="Optional password for SMTP authentication"),
        'smtp_encryption': fields.selection([('none','None'),
                                             ('starttls','TLS (STARTTLS)'),
                                             ('ssl','SSL/TLS')],
                                            string='Connection Security',
                                            help="Choose the connection encryption scheme:\n"
                                                 "- None: SMTP sessions are done in cleartext.\n"
                                                 "- TLS (STARTTLS): TLS encryption is requested at start of SMTP session (Recommended)\n"
                                                 "- SSL/TLS: SMTP sessions are encrypted with SSL/TLS through a dedicated port (default: 465)"),
        'smtp_debug': fields.boolean('Debugging', help="If enabled, the full output of SMTP sessions will "
                                                       "be written to the server log at DEBUG level"
                                                       "(this is very verbose and may include confidential info!)"),
        'sequence': fields.integer('Priority', help="When no specific mail server is requested for a mail, the highest priority one "
                                                    "is used. Default priority is 10 (smaller number = higher priority)"),
    }

    _defaults = {
         'smtp_port': 25,
         'sequence': 10,
         'smtp_encryption': 'none',
     }

    def __init__(self, *args, **kwargs):
        # Make sure we pipe the smtplib outputs to our own DEBUG logger
        if not isinstance(smtplib.stderr, WriteToLogger):
            logpiper = WriteToLogger(_logger)
            smtplib.stderr = logpiper
            smtplib.stdout = logpiper
        return super(ir_mail_server, self).__init__(*args,**kwargs)

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
                raise osv.except_osv(_("Connection test failed!"), _("Here is what we got instead:\n %s") % e)
            finally:
                try:
                    if smtp: smtp.quit()
                except Exception:
                    # ignored, just a consequence of the previous exception
                    pass
        raise osv.except_osv(_("Connection test succeeded!"), _("Everything seems properly set up!"))

    def connect(self, host, port, user=None, password=None, encryption=False, smtp_debug=False):
        """Returns a new SMTP connection to the give SMTP server, authenticated
           with ``user`` and ``password`` if provided, and encrypted as requested
           by the ``encryption`` parameter.
        
           :param host: host or IP of SMTP server to connect to
           :param int port: SMTP port to connect to
           :param user: optional username to authenticate with
           :param password: optional password to authenticate with
           :param string encryption: optional: ``'ssl'`` | ``'starttls'``
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
            connection.login(user, password)
        return connection

    def build_email(self, email_from, email_to, subject, body, email_cc=None, email_bcc=None, reply_to=False,
               attachments=None, message_id=None, references=None, object_id=False, subtype='plain', headers=None):
        """Constructs an RFC2822 email.message.Message object based on the keyword arguments passed, and returns it.

           :param string email_from: sender email address
           :param list email_from: list of recipient addresses (to be joined with commas) 
           :param string subject: email subject (no pre-encoding/quoting necessary)
           :param string body: email body, according to the ``subtype`` (by default, plaintext).
                               If html subtype is used, the message will be automatically converted
                               to plaintext and wrapped in multipart/alternative.
           :param string reply_to: optional value of Reply-To header
           :param string object_id: optional tracking identifier, to be included in the message-id for
                                    recognizing replies. Suggested format for object-id is "res_id-model",
                                    e.g. "12345-crm.lead".
           :param string subtype: optional mime subtype for the text body (usually 'plain' or 'html'),
                                  must match the format of the ``body`` parameter. Default is 'plain',
                                  making the content part of the mail "text/plain".
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
        email_text_part = MIMEText(email_body_utf8 or '', _subtype=subtype, _charset='utf-8')
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
        msg['From'] = encode_header(email_from)
        del msg['Reply-To']
        if reply_to:
            msg['Reply-To'] = encode_header(reply_to)
        else:
            msg['Reply-To'] = msg['From']
        msg['To'] = encode_header(COMMASPACE.join(email_to))
        if email_cc:
            msg['Cc'] = encode_header(COMMASPACE.join(email_cc))
        if email_bcc:
            msg['Bcc'] = encode_header(COMMASPACE.join(email_bcc))
        msg['Date'] = formatdate(localtime=True)
        # Custom headers may override normal headers or provide additional ones
        for key, value in headers.iteritems():
            msg[ustr(key).encode('utf-8')] = encode_header(value)

        if html2text and subtype == 'html':
            # Always provide alternative text body if possible.
            text_utf8 = tools.html2text(email_body_utf8.decode('utf-8')).encode('utf-8')
            alternative_part = MIMEMultipart(_subtype="alternative")
            alternative_part.attach(MIMEText(text_utf8, _charset='utf-8', _subtype='plain'))
            alternative_part.attach(email_text_part)
            msg.attach(alternative_part)
        else:
            msg.attach(email_text_part)

        if attachments:
            for (fname, fcontent) in attachments:
                filename_utf8 = ustr(fname).encode('utf-8')
                part = MIMEBase('application', "octet-stream")
                part.set_payload(fcontent)
                Encoders.encode_base64(part)
                # Force RFC2231 encoding for attachment filename
                # See email.message.Message.add_header doc
                part.add_header('Content-Disposition', 'attachment',
                                filename=('utf-8',None,filename_utf8)) 
                msg.attach(part)
        return msg

    def send_email(self, cr, uid, message, mail_server_id=None, smtp_server=None, smtp_port=None,
                   smtp_user=None, smtp_password=None, smtp_encryption='none', smtp_debug=False,
                   context=None):
        """Sends an email directly (no queuing).

        No retries are done, the caller should handle MailDeliveryException in order to ensure that
        the mail is never lost.

        If the mail_server_id is provided, sends using this mail server, ignoring other smtp_* arguments.
        If mail_server_id is None and smtp_server is None, use the default mail server (highest priority).
        If mail_server_id is None and smtp_server is not None, use the provided smtp_* arguments.
        If both mail_server_id and smtp_server are None, look for an 'smtp_server' value in server config,
        and fails if not found.

        :param message: the email.message.Message to send
        :param mail_server_id: optional id of ir.mail_server to use for sending. overrides other smtp_* arguments.
        :param smtp_server: optional hostname of SMTP server to use
        :param smtp_encryption: one of 'none', 'starttls' or 'ssl' (see ir.mail_server fields for explanation)
        :param smtp_port: optional SMTP port, if mail_server_id is not passed
        :param smtp_user: optional SMTP user, if mail_server_id is not passed
        :param smtp_password: optional SMTP password to use, if mail_server_id is not passed
        :param smtp_debug: optional SMTP debug flag, if mail_server_id is not passed
        :param debug: whether to turn on the SMTP level debugging, output to DEBUG log level
        :return: the Message-ID of the message that was just sent, if successfully sent, otherwise raises
                 MailDeliveryException and logs root cause.
        """
        smtp_from = message['From']
        assert smtp_from, "The From header is required in any outbound e-mail"
        email_to = message['To']
        email_cc = message['Cc']
        email_bcc = message['Bcc']
        smtp_to_list = filter(None,tools.flatten([email_to, email_cc, email_bcc]))

        # Get SMTP Server Details from Mail Server
        mail_server = None
        if mail_server_id:
            mail_server = self.browse(cr, uid, mail_server_id)
        elif not smtp_server:
            mail_server_ids = self.search(cr, uid, [], order='sequence', limit=1)
            if mail_server_ids:
                mail_server = self.browse(cr, uid, mail_server_ids[0])
        else:
            # we were passed an explicit smtp_server or nothing at all
            smtp_server = smtp_server or tools.config.get('smtp_server')
            smtp_port = tools.config.get('smtp_port', 25) if smtp_port is None else smtp_port
            smtp_user = smtp_user or tools.config.get('smtp_user')
            smtp_password = smtp_password or tools.config.get('smtp_password')

        if mail_server:
            smtp_server = mail_server.smtp_host
            smtp_user = mail_server.smtp_user
            smtp_password = mail_server.smtp_pass
            smtp_port = mail_server.smtp_port
            smtp_encryption = mail_server.smtp_encryption
            smtp_debug = smtp_debug or mail_server.smtp_debug

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

            try:
                smtp = self.connect(smtp_server, smtp_port, smtp_user, smtp_password, smtp_encryption, smtp_debug)
                smtp.sendmail(smtp_from, smtp_to_list, message.as_string())
            finally:
                try:
                    # Close Connection of SMTP Server
                    smtp.quit()
                except Exception:
                    # ignored, just a consequence of the previous exception
                    pass
        except Exception, e:
            msg = _("Mail delivery failed via SMTP server '%s'.\n%s: %s") % (smtp_server, e.__class__.__name__, e)
            _logger.exception(msg)
            raise MailDeliveryException(_("Mail delivery failed"), msg)
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
