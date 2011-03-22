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

import inspect
import subprocess
import logging
import os
import re
import smtplib
import socket
import sys
import threading
import time
import warnings
import zipfile
from datetime import datetime
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.Header import Header
from email.Utils import formatdate, COMMASPACE
from email import Utils
from email import Encoders
from itertools import islice, izip
from lxml import etree
if sys.version_info[:2] < (2, 4):
    from threadinglocal import local
else:
    from threading import local
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

# List of etree._Element subclasses that we choose to ignore when parsing XML.
# We include the *Base ones just in case, currently they seem to be subclasses of the _* ones.
SKIPPED_ELEMENT_TYPES = (etree._Comment, etree._ProcessingInstruction, etree.CommentBase, etree.PIBase)


class ir_mail_server(osv.osv):
    """
    mail server
    """
    _name = "ir.mail_server"

    _columns = {
        'name': fields.char('Name',
                        size=64, required=True,
                        select=True,
                        help="The Name is used as the Sender name along with the provided From Email, \
unless it is already specified in the From Email, e.g: John Doe <john@doe.com>",
                        ),
        'smtp_host': fields.char('Server',
                        size=120, required=True,
                        help="Enter name of outgoing server, eg: smtp.yourdomain.com"),
        'smtp_port': fields.integer('SMTP Port',
                        size=64, required=True,
                        help="Enter port number, eg: 25 or 587"),
        'smtp_user': fields.char('User Name',
                        size=120, required=False,
                        help="Specify the username if your SMTP server requires authentication, "
                        "otherwise leave it empty."),
        'smtp_pass': fields.char('Password',
                        size=120,
                        required=False),
        'smtp_tls':fields.boolean('TLS'),
        'smtp_ssl':fields.boolean('SSL/TLS'),
        'priority': fields.integer('Priority', help=""),
    }

    _defaults = {
         'name':lambda self, cursor, user, context:self.pool.get( 'res.users'
                                                ).read(cursor, user, user, ['name'], context)['name'],
         'smtp_port': tools.config.get('smtp_port',25),
         'smtp_host': tools.config.get('smtp_server','localhost'),
         'smtp_ssl': tools.config.get('smtp_ssl',False),
         'smtp_tls': True,
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
        try:
            for smtp_server in self.browse(cr, uid, ids, context=context):
                smtp = self.connect_smtp_server(smtp_server.smtp_host, smtp_server.smtp_port,  user_name=smtp_server.smtp_user,
                                user_password=smtp_server.smtp_pass, ssl=smtp_server.smtp_ssl, tls=smtp_server.smtp_tls)
                try:
                    smtp.quit()
                except Exception:
                    # ignored, just a consequence of the previous exception
                    pass
        except Exception, error:
            raise osv.except_osv(
                                 _("SMTP Connection: Test failed"),
                                 _("Reason: %s") % error
                                 )

        raise osv.except_osv(_("SMTP Connection: Test Successfully!"), '')

    def connect_smtp_server(server_host, server_port,  user_name=None, user_password=None, ssl=False, tls=False, debug=False):
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

    def _email_send(smtp_from, smtp_to_list, message, ssl=False, debug=False,
                smtp_server=None, smtp_port=None, smtp_user=None, smtp_password=None):
        """Low-level method to send directly a Message through the configured smtp server.
            :param smtp_from: RFC-822 envelope FROM (not displayed to recipient)
            :param smtp_to_list: RFC-822 envelope RCPT_TOs (not displayed to recipient)
            :param message: an email.message.Message to send
            :param debug: True if messages should be output to stderr before being sent,
                          and smtplib.SMTP put into debug mode.
            :return: True if the mail was delivered successfully to the smtp,
                     else False (+ exception logged)
        """
        print '_email::'
        class WriteToLogger(object):
            def __init__(self):
                self.logger = loglevels.Logger()

            def write(self, s):
                self.logger.notifyChannel('email_send', loglevels.LOG_DEBUG, s)

        try:
            smtp_server = smtp_server or config['smtp_server']

            if smtp_server.startswith('maildir:/'):
                from mailbox import Maildir
                maildir_path = smtp_server[8:]
                mdir = Maildir(maildir_path,factory=None, create = True)
                mdir.add(message.as_string(True))
                return True

            if debug:
                oldstderr = smtplib.stderr
                smtplib.stderr = WriteToLogger()

            if not ssl: ssl = config.get('smtp_ssl', False)
            smtp = self.connect_smtp_server(smtp_server, smtp_port, smtp_user, smtp_password, ssl=ssl, tls=True, debug=debug)
            try:
                smtp.sendmail(smtp_from, smtp_to_list, message.as_string())
            except Exception:
                _logger.error('could not deliver Email(s)', exc_info=True)
                return False
            finally:
                try:
                    smtp.quit()
                except Exception:
                    # ignored, just a consequence of the previous exception
                    pass

            if debug:
                smtplib.stderr = oldstderr
        except Exception:
            _logger.error('Error on Send Emails Services', exc_info=True)
            return False

        return True

    def send_email(self, cr, uid, smtp_from, smtp_to_list, message, id=None, subject=None, ssl=False,
                    debug=False, smtp_server=None, smtp_port=None, smtp_user=None, smtp_password=None):

        """Send an email.
        """

        if not (smtp_from or config['email_from']):
            raise ValueError("Sending an email requires either providing a sender "
                             "address or having configured one")
        if not smtp_from: smtp_from = config.get('email_from', False)

        smtp_from = ustr(smtp_from).encode('utf-8')

        email_body = ustr(message).encode('utf-8')
        email_text = MIMEText(email_body or '',_charset='utf-8')
        msg = MIMEMultipart()

#        if not message_id and openobject_id:
#            message_id = generate_tracking_message_id(openobject_id)
#        else:
        message_id = Utils.make_msgid()
        msg['Message-Id'] = message_id
        if subject:
            msg['Subject'] = Header(ustr(subject), 'utf-8')
        msg['From'] = smtp_from
        msg['To'] = COMMASPACE.join(smtp_to_list)
        msg['Date'] = formatdate(localtime=True)

        if html2text and subtype == 'html':
            text = html2text(email_body.decode('utf-8')).encode('utf-8')
            alternative_part = MIMEMultipart(_subtype="alternative")
            alternative_part.attach(MIMEText(text, _charset='utf-8', _subtype='plain'))
            alternative_part.attach(email_text)
            msg.attach(alternative_part)
        else:
            msg.attach(email_text)
        res = self._email_send(smtp_from, smtp_to_list, msg)
        if res:
            return message_id
        return False


ir_mail_server()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
