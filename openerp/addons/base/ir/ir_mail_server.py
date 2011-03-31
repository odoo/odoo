# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 Tiny SPRL (<http://tiny.be>)
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

from osv import osv
from osv import fields
from tools.translate import _
import tools
from tools import ustr
from tools import config
import netsvc

import base64
import subprocess
import logging
import smtplib
import socket
import sys
import time
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.Header import Header
from email.Utils import formatdate, COMMASPACE
from email import Utils
from email import Encoders
try:
    from html2text import html2text
except ImportError:
    html2text = None

import openerp.loglevels as loglevels
from tools import config
from email.generator import Generator

# get_encodings, ustr and exception_to_unicode were originally from tools.misc.
# There are moved to loglevels until we refactor tools.
from openerp.loglevels import get_encodings, ustr, exception_to_unicode

_logger = logging.getLogger('tools')
priorities = {
        '1': '1 (Highest)',
        '2': '2 (High)',
        '3': '3 (Normal)',
        '4': '4 (Low)',
        '5': '5 (Lowest)',
}


class ir_mail_server(osv.osv):
    """
    mail server
    """
    _name = "ir.mail_server"

    _columns = {
        'name': fields.char('Name',
                        size=64, required=True,
                        select=True,
                        ),
        'smtp_host': fields.char('Server',
                        size=120, required=True,
                        help="Hostname or IP of SMTP server"),
        'smtp_port': fields.integer('SMTP Port',
                        size=64, required=True,
                        help="SMTP Port of SMPT server"),
        'smtp_user': fields.char('User Name',
                        size=120, required=False,
                        help="Username for SMTP authentication"),
        'smtp_pass': fields.char('Password',
                        size=120,
                        required=False, help="Password for SMTP authentication"),
        'smtp_tls': fields.boolean('TLS', help="If True, TLS encryption will be requested at \
                  beginning of SMTP transactions. Do not use if SSL is \
                  enabled, or if the server does not support it."),
        'smtp_ssl':fields.boolean('SSL/TLS', help="If True, SMTPS (Secure SMTP over SSL encryption) \
                  will be used. When selected, change smtp_port to 465. \
                  Do not use with TLS or if the server does not support it."),
        'priority': fields.integer('Priority', help="If no specific \
                  server is requested for a mail, the highest priority one \
                  is used. Default priority is 10"),
    }

    _defaults = {
         'smtp_port': 25,
         'priority': 10,
     }

    _sql_constraints = [
    ]


    def name_get(self, cr, uid, ids, context=None):
        return [(a["id"], "(%s)" % (a['name'])) for a in self.read(cr, uid, ids, ['name'], context=context)]

    def test_smtp_connection(self, cr, uid, ids, context=None):
        """
        Test SMTP connection works
        """
        for smtp_server in self.browse(cr, uid, ids, context=context):
            smtp = False
            try:
                smtp = self.connect_smtp_server(smtp_server.smtp_host,
                   smtp_server.smtp_port, user_name=smtp_server.smtp_user,
                   user_password=smtp_server.smtp_pass, ssl=smtp_server.smtp_ssl,
                   tls=smtp_server.smtp_tls, debug=False)
            except Exception, error:
                raise osv.except_osv(
                                 _("SMTP Connection: Test failed"),
                                 _("Reason: %s") % error )
            finally:
                try:
                    if smtp:smtp.quit()
                except Exception:
                    # ignored, just a consequence of the previous exception
                    pass

        raise osv.except_osv(_("SMTP Connection: Test Successfully!"), '')

    def connect_smtp_server(self, server_host, server_port, user_name=None,
                        user_password=None, ssl=False, tls=False, debug=False):
        """
        Connect SMTP Server and returned the (SMTP) object
        """
        smtp_server = None
        try:
            if ssl:
                # In Python 2.6
                smtp_server = smtplib.SMTP_SSL(server_host, server_port)
            else:
                smtp_server = smtplib.SMTP(server_host, server_port)

            smtp_server.set_debuglevel(int(bool(debug)))  # 0 or 1


            if tls:
                smtp_server.ehlo()
                smtp_server.starttls()
                smtp_server.ehlo()

            #smtp_server.connect(server_host, server_port)

            if smtp_server.has_extn('AUTH') or user_name or user_password:
                smtp_server.login(user_name, user_password)


        except Exception, error:
            _logger.error('Could not connect to smtp server : %s' %(error), exc_info=True)
            raise error
        return smtp_server

    def pack_message(self, cr, uid, email_from, email_to, subject, body, email_cc=None, email_bcc=None, reply_to=False,
               attach=None, message_id=None, references=None, openobject_id=False, debug=False, subtype='plain', x_headers=None, priority='3'):

        """
        Pack all message attributes into one object.
        Return email.message object after packed all email attribure.
        """
        if x_headers is None:
            x_headers = {}

        if not email_cc: email_cc = []
        if not email_bcc: email_bcc = []
        if not body: body = u''

        email_body = ustr(body).encode('utf-8')
        email_text = MIMEText(email_body or '', _subtype=subtype,_charset='utf-8')
        msg = MIMEMultipart()

        if not message_id and openobject_id:
            message_id = tools.generate_tracking_message_id(openobject_id)
        else:
            message_id = Utils.make_msgid()
        if references:
            msg['references'] = references
        msg['Message-Id'] = message_id
        msg['Subject'] = Header(ustr(subject), 'utf-8')
        msg['From'] = email_from
        del msg['Reply-To']
        if reply_to:
            msg['Reply-To'] = reply_to
        else:
            msg['Reply-To'] = msg['From']
        msg['To'] = COMMASPACE.join(email_to)
        if email_cc:
            msg['Cc'] = COMMASPACE.join(email_cc)
        if email_bcc:
            msg['Bcc'] = COMMASPACE.join(email_bcc)
        msg['Date'] = formatdate(localtime=True)

        msg['X-Priority'] = priorities.get(priority, '3 (Normal)')

        # Add dynamic X Header
        for key, value in x_headers.iteritems():
            msg['%s' % key] = str(value)

        if html2text and subtype == 'html':
            text = tools.html2text(email_body.decode('utf-8')).encode('utf-8')
            alternative_part = MIMEMultipart(_subtype="alternative")
            alternative_part.attach(MIMEText(text, _charset='utf-8', _subtype='plain'))
            alternative_part.attach(email_text)
            msg.attach(alternative_part)
        else:
            msg.attach(email_text)

        if attach:
            for (fname, fcontent) in attach:
                part = MIMEBase('application', "octet-stream")
                part.set_payload( fcontent )
                Encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment; filename="%s"' % (fname,))
                msg.attach(part)
        return msg

    def send_email(self, cr, uid, smtp_from, smtp_to_list, message,
           mail_server_id=None, smtp_server=None, smtp_port=None,
           smtp_user=None, smtp_password=None, ssl=False, tls=True, debug=False):

        """Send an email.
        If the id of a mail server is provided, send using this mail server, ignoring other smtp_* arguments.
        If mail_server_id == None and smtp_server == None, use the default mail server (highest priority).
        If mail_server_id == None and smtp_server is not None, use the provided smtp_* arguments.
        Return messageID of message if Successfully sent Email otherwise return False
        """
        if not (smtp_from or config.get('email_from', False)):
            raise ValueError("Sending an email requires either providing a sender "
                             "address or having configured one")
        if not smtp_from: smtp_from = config.get('email_from', False)
        smtp_from = tools.ustr(smtp_from).encode('utf-8')

        # Get SMTP Server Details from Mail Server
        mail_server = False
        if mail_server_id:
            mail_server = self.browse(cr, uid, mail_server_id)
        elif not (mail_server_id and smtp_server):
            mail_server_ids = self.search(cr, uid, [], order='priority', limit=1)
            mail_server = self.browse(cr, uid, mail_server_ids[0])
        if mail_server:
            smtp_server = mail_server.smtp_host
            smtp_user = mail_server.smtp_user
            smtp_password = mail_server.smtp_pass
            smtp_port = mail_server.smtp_port
            ssl = mail_server.smtp_ssl
            tls = mail_server.smtp_tls

        class WriteToLogger(object):
            def __init__(self):
                self.logger = loglevels.Logger()

            def write(self, s):
                self.logger.notifyChannel('email_send', loglevels.LOG_DEBUG, s)


        try:
            message_id = message['Message-Id']
            smtp_server = smtp_server or config.get('smtp_server')

            # Add email in Maildir if smtp_server contains maildir.
            if smtp_server.startswith('maildir:/'):
                from mailbox import Maildir
                maildir_path = smtp_server[8:]
                mdir = Maildir(maildir_path, factory=None, create = True)
                mdir.add(message.as_string(True))
                return message_id

            if debug:
                oldstderr = smtplib.stderr
                smtplib.stderr = WriteToLogger()

            # Open Connection of SMTP Server
            smtp = self.connect_smtp_server(
                    smtp_server,
                    smtp_port or config.get('smtp_port', 25),
                    user_name=smtp_user or config.get('smtp_user', False),
                    user_password=smtp_password or config.get('smtp_password', False),
                    ssl=ssl or config.get('smtp_ssl', False),
                    tls=tls, debug=debug)
            try:
                # Send Email
                smtp.sendmail(smtp_from, smtp_to_list, message.as_string())
            except Exception:
                _logger.error('could not deliver Email(s)', exc_info=True)
                return False
            finally:
                try:
                    # Close Connection of SMTP Server
                    smtp.quit()
                except Exception:
                    # ignored, just a consequence of the previous exception
                    pass

            if debug:
                smtplib.stderr = oldstderr
        except Exception:
            _logger.error('Error on Send Emails Services', exc_info=True)

        return message_id

    def on_change_ssl(self, cr, uid, ids, smtp_ssl):
        smtp_port = 0
        if smtp_ssl:
            smtp_port = 465
        return {'value': {'smtp_ssl':smtp_ssl, 'smtp_tls':False, 'smtp_port':smtp_port}}

    def on_change_tls(self, cr, uid, ids, smtp_tls):
        smtp_port = 0
        if smtp_tls:
            smtp_port = 0
        return {'value': {'smtp_tls':smtp_tls, 'smtp_ssl':False, 'smtp_port':smtp_port}}


ir_mail_server()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
