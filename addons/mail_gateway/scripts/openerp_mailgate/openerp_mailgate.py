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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
###########################################################################################

from email.header import decode_header
import email as EMAIL
import re
import smtplib
import time, socket
import xmlrpclib


email_re = re.compile(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6})")
case_re = re.compile(r"\[([0-9]+)\]", re.UNICODE)
command_re = re.compile("^Set-([a-z]+) *: *(.+)$", re.I + re.UNICODE)
reference_re = re.compile("<.*-openobject-(\\d+)@(.*)>", re.UNICODE)

priorities = {
    '1': '1 (Highest)', 
    '2': '2 (High)', 
    '3': '3 (Normal)', 
    '4': '4 (Low)', 
    '5': '5 (Lowest)', 
}

class rpc_proxy(object):
    def __init__(self, uid, passwd, host='localhost', port=8069, path='object', dbname='terp'):
        self.rpc = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/%s' % (host, port, path), allow_none=True)
        self.user_id = uid
        self.passwd = passwd
        self.dbname = dbname

    def __call__(self, *request, **kwargs):
        return self.rpc.execute(self.dbname, self.user_id, self.passwd, *request, **kwargs)

class email_parser(object):
    def __init__(self, uid, password, model, email, email_default, dbname, host, port, smtp_server=None, smtp_port=None, smtp_ssl=None, smtp_user=None, smtp_password=None):
        self.rpc = rpc_proxy(uid, password, host=host, port=port, dbname=dbname)
        try:
            self.model_id = int(model)
            self.model = str(model)
        except:
            self.model_id = self.rpc('ir.model', 'search', [('model', '=', model)])[0]
            self.model = str(model)
        self.email = email
        self.email_default = email_default
        self.canal_id = False
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_ssl = smtp_ssl
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        
        
    def email_get(self, email_from):
        return self.rpc('email.server.tools', 'to_email', email_from)

    def _to_decode(self, s, charsets):
        for charset in charsets:
            if charset:
                try:
                    return s.decode(charset)
                except UnicodeError:
                    pass
        return s.decode('latin1')

    def _decode_header(self, s):
        if s:
            s = decode_header(s.replace('\r', '')) 
        return ''.join(map(lambda x:self._to_decode(x[0], [x[1]]), s or []))

    def msg_send(self, msg, emails, priority=None):
        if not emails:
            return False

        msg['To'] = emails[0]
        if len(emails)>1:
            if 'Cc' in msg:
                del msg['Cc']
            msg['Cc'] = ','.join(emails[1:])

        del msg['Reply-To']
        msg['Reply-To'] = self.email
        if self.smtp_user and self.smtp_password:
            s = smtplib.SMTP(self.smtp_server, self.smtp_port)
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(self.smtp_user, self.smtp_password)
            s.sendmail(self.email, emails, msg.as_string())
            s.close()
            return True
        return False


    def parse(self, message):
        try:
            res_id = self.rpc('email.server.tools', 'process_email', self.model, message)
        except Exception, e:
            res_id = False

        msg = EMAIL.message_from_string(str(message))
        subject = self._decode_header(msg['Subject'])
        if msg.get('Subject', ''):
            del msg['Subject']

       #Changed for sending reply mail
        if res_id:
            msg['Subject'] = '['+str(res_id)+'] '+subject
            msg['Message-Id'] = '<'+str(time.time())+'-openerpcrm-'+str(res_id)+'@'+socket.gethostname()+'>'

        mm = [self._decode_header(msg['From']), self._decode_header(msg['To'])]+self._decode_header(msg.get('Cc', '')).split(',')
        msg_mails = map(self.email_get, filter(None, mm))

        try:
            self.msg_send(msg, msg_mails)
        except Exception, e:
            if self.email_default:
                a = self._decode_header(msg['Subject'])
                del msg['Subject']
                msg['Subject'] = '[OpenERP-FetchError] ' + a
                self.msg_send(msg, self.email_default.split(','))
        return res_id, msg_mails

if __name__ == '__main__':
    parser = optparse.OptionParser(usage='usage: %prog [options]', version='%prog v1.0')
    group = optparse.OptionGroup(parser, "Note", 
        "This program parse a mail from standard input and communicate "
        "with the Open ERP server for case management in the CRM module.")
    parser.add_option_group(group)
    parser.add_option("-u", "--user", dest="userid", help="ID of the user in Open ERP", default=1, type='int')
    parser.add_option("-p", "--password", dest="password", help="Password of the user in Open ERP", default='admin')
    parser.add_option("-e", "--email", dest="email", help="Email address used in the From field of outgoing messages")
    parser.add_option("-o", "--model", dest="model", help="Name or ID of crm model", default="crm.lead")
    parser.add_option("-m", "--default", dest="default", help="Default eMail in case of any trouble.", default=None)
    parser.add_option("-d", "--dbname", dest="dbname", help="Database name (default: terp)", default='terp')
    parser.add_option("--host", dest="host", help="Hostname of the Open ERP Server", default="localhost")
    parser.add_option("--port", dest="port", help="Port of the Open ERP Server", default="8069")
    parser.add_option('--smtp', dest='smtp_server', default='', help='specify the SMTP server for sending email')
    parser.add_option('--smtp-port', dest='smtp_port', default='25', help='specify the SMTP port', type="int")
    parser.add_option('--smtp-ssl', dest='smtp_ssl', default='', help='specify the SMTP server support SSL or not')
    parser.add_option('--smtp-user', dest='smtp_user', default='', help='specify the SMTP username for sending email')
    parser.add_option('--smtp-password', dest='smtp_password', default='', help='specify the SMTP password for sending email')

    (options, args) = parser.parse_args()
    parser = email_parser(options.userid, options.password, options.model, options.email, options.default, dbname=options.dbname, host=options.host, port=options.port, smtp_server=options.smtp_server, smtp_port=options.smtp_port, smtp_ssl=options.smtp_ssl, smtp_user=options.smtp_user, smtp_password=options.smtp_password)

    msg_txt = sys.stdin.read().decode('utf8')

    parser.parse(msg_txt)
 
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
