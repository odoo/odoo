#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-TODAY OpenERP S.A. (http://www.openerp.com)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################
"""
    openerp_mailgate.py
"""

import cgitb
import time
import optparse
import sys
import xmlrpclib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from email import Encoders

class DefaultConfig(object):
    """
    Default configuration
    """
    OPENERP_DEFAULT_USER_ID = 1
    OPENERP_DEFAULT_PASSWORD = 'admin'
    OPENERP_HOSTNAME = 'localhost'
    OPENERP_PORT = 8069
    OPENERP_DEFAULT_DATABASE = 'openerp'
    MAIL_ERROR = 'error@example.com'
    MAIL_SERVER = 'smtp.example.com'
    MAIL_SERVER_PORT = 25
    MAIL_ADMINS = ('info@example.com',)

config = DefaultConfig()


def send_mail(_from_, to_, subject, text, files=None, server=config.MAIL_SERVER, port=config.MAIL_SERVER_PORT):
    assert isinstance(to_, (list, tuple))

    if files is None:
        files = []

    msg = MIMEMultipart()
    msg['From'] = _from_
    msg['To'] = COMMASPACE.join(to_)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach( MIMEText(text) )

    for file_name, file_content in files:
        part = MIMEBase('application', "octet-stream")
        part.set_payload( file_content )
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"'
                       % file_name)
        msg.attach(part)

    smtp = smtplib.SMTP(server, port=port)
    smtp.sendmail(_from_, to_, msg.as_string() )
    smtp.close()

class RPCProxy(object):
    def __init__(self, uid, passwd,
                 host=config.OPENERP_HOSTNAME,
                 port=config.OPENERP_PORT,
                 path='object',
                 dbname=config.OPENERP_DEFAULT_DATABASE):
        self.rpc = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/%s' % (host, port, path), allow_none=True)
        self.user_id = uid
        self.passwd = passwd
        self.dbname = dbname

    def __call__(self, *request, **kwargs):
        return self.rpc.execute(self.dbname, self.user_id, self.passwd, *request, **kwargs)

class EmailParser(object):
    def __init__(self, uid, password, dbname, host, port, model=False, email_default=False):
        self.rpc = RPCProxy(uid, password, host=host, port=port, dbname=dbname)
        if model:
            try:
                self.model_id = int(model)
                self.model = str(model)
            except:
                self.model_id = self.rpc('ir.model', 'search', [('model', '=', model)])[0]
                self.model = str(model)
            self.email_default = email_default


    def parse(self, message, custom_values=None, save_original=None):
        # pass message as bytes because we don't know its encoding until we parse its headers
        # and hence can't convert it to utf-8 for transport
        return self.rpc('mail.thread',
                        'message_process',
                        self.model,
                        xmlrpclib.Binary(message),
                        custom_values or {},
                        save_original or False)

def configure_parser():
    parser = optparse.OptionParser(usage='usage: %prog [options]', version='%prog v1.1')
    group = optparse.OptionGroup(parser, "Note",
        "This program parse a mail from standard input and communicate "
        "with the Odoo server for case management in the CRM module.")
    parser.add_option_group(group)
    parser.add_option("-u", "--user", dest="userid",
                      help="Odoo user id to connect with",
                      default=config.OPENERP_DEFAULT_USER_ID, type='int')
    parser.add_option("-p", "--password", dest="password",
                      help="Odoo user password",
                      default=config.OPENERP_DEFAULT_PASSWORD)
    parser.add_option("-o", "--model", dest="model",
                      help="Name or ID of destination model",
                      default="crm.lead")
    parser.add_option("-m", "--default", dest="default",
                      help="Admin email for error notifications.",
                      default=None)
    parser.add_option("-d", "--dbname", dest="dbname",
                      help="Odoo database name (default: %default)",
                      default=config.OPENERP_DEFAULT_DATABASE)
    parser.add_option("--host", dest="host",
                      help="Odoo Server hostname",
                      default=config.OPENERP_HOSTNAME)
    parser.add_option("--port", dest="port",
                      help="Odoo Server XML-RPC port number",
                      default=config.OPENERP_PORT)
    parser.add_option("--custom-values", dest="custom_values",
                      help="Dictionary of extra values to pass when creating records",
                      default=None)
    parser.add_option("-s", dest="save_original",
                      action="store_true",
                      help="Keep a full copy of the email source attached to each message",
                      default=False)

    return parser

def main():
    """
    Receive the email via the stdin and send it to the OpenERP Server
    """

    parser = configure_parser()
    (options, args) = parser.parse_args()
    email_parser = EmailParser(options.userid,
                               options.password,
                               options.dbname,
                               options.host,
                               options.port,
                               model=options.model,
                               email_default= options.default)
    msg_txt = sys.stdin.read()
    custom_values = {}
    try:
        custom_values = dict(eval(options.custom_values or "{}" ))
    except:
        import traceback
        traceback.print_exc()

    try:
        email_parser.parse(msg_txt, custom_values, options.save_original or False)
    except Exception:
        msg = '\n'.join([
            'parameters',
            '==========',
            '%r' % (options,),
            'traceback',
            '=========',
            '%s' % (cgitb.text(sys.exc_info())),
        ])

        subject = '[Odoo]:ERROR: Mailgateway - %s' % time.strftime('%Y-%m-%d %H:%M:%S')
        send_mail(
            config.MAIL_ERROR,
            config.MAIL_ADMINS,
            subject, msg, files=[('message.txt', msg_txt)]
        )
        sys.stderr.write("Failed to deliver email to Odoo Server, sending error notification to %s\n" % config.MAIL_ADMINS)

if __name__ == '__main__':
    main()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
