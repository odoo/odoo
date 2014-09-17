# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
##############################################################################

import os, sys
import re
import smtplib
import email, mimetypes
from email.header import decode_header
from email.mime.text import MIMEText
import xmlrpclib

warn_msg = """
Bonjour,

Le message avec le sujet "%s" n'a pu être archivé dans l'ERP.

""".decode('utf-8')

class EmailParser(object):

    def __init__(self, headers, dispatcher):
        self.headers = headers
        self.dispatcher = dispatcher
    
    def parse(self, msg):
        dispatcher((self.headers, msg))

class CommandDispatcher(object):

    def __init__(self, receiver):
        self.receiver = receiver
    
    def __call__(self, request):
        return self.receiver(request)

class RPCProxy(object):

    def __init__(self, uid, passwd, host='localhost', port=8069, path='object'):
        self.rpc = xmlrpclib.ServerProxy('http://%s:%s/%s' % (host, port, path))
        self.user_id = uid
        self.passwd = passwd
    
    def __call__(self, request):
        return self.rpc.execute(self.user_id, self.passwd, *request)

class ReceiverEmail2Event(object):

    email_re = re.compile(r"""
        ([a-zA-Z][\w\.-]*[a-zA-Z0-9]     # username part
        @                                # mandatory @ sign
        [a-zA-Z0-9][\w\.-]*              # domain must start with a letter
         \.
         [a-z]{2,3}                      # TLD
        )
        """, re.VERBOSE)

    project_re = re.compile(r"^ *\[?(\d{4}\.?\d{0,3})\]?", re.UNICODE)


    def __init__(self, rpc):
        self.rpc = rpc
    
    def get_addresses(self, headers, msg):
        hcontent = ''
        for header in [h for h in headers if msg.has_key(h)]:
            hcontent += msg[header]
        return self.email_re.findall(hcontent)

    def get_partners(self, headers, msg):
        alladdresses = self.get_addresses(headers, msg)
        address_ids = self.rpc(('res.partner', 'search', [('email', 'in', alladdresses)]))
        addresses = self.rpc(('res.partner', 'read', address_ids))
        return [x['partner_id'][0] for x in addresses]

    def __call__(self, request):
        headers, msg = request
        partners = self.get_partners(headers, msg)
        subject = u''
        for string, charset in decode_header(msg['Subject']):
            if charset:
                subject += string.decode(charset)
            else:
                subject += unicode(string)
        if partners:
            self.save_mail(msg, subject, partners)
        else:
            warning = MIMEText((warn_msg % (subject,)).encode('utf-8'), 'plain', 'utf-8')
            warning['Subject'] = 'Message de OpenERP'
            warning['From'] = 'erp@steel-sa.com'
            warning['To'] = msg['From']
            s = smtplib.SMTP()
            s.connect()
            s.sendmail('erp@steel-sa.com', self.email_re.findall(msg['From']), warning.as_string())
            s.close()

        if msg.is_multipart():
            for message in [m for m in msg.get_payload() if m.get_content_type() == 'message/rfc822']:
                self((headers, message.get_payload()[0]))
    
    def save_mail(self, msg, subject, partners):
        counter, description = 1, u''
        if msg.is_multipart():
            for part in msg.get_payload():
                stockdir = os.path.join('emails', msg['Message-Id'][1:-1])
                newdir = os.path.join('/tmp', stockdir)
                filename = part.get_filename()
                if not filename:
                    ext = mimetypes.guess_extension(part.get_type())
                    if not ext:
                        ext = '.bin'
                    filename = 'part-%03d%s' % (counter, ext)

                if part.get_content_maintype() == 'multipart':
                    continue
                elif part.get_content_maintype() == 'text':
                    if part.get_content_subtype() == 'plain':
                        description += part.get_payload(decode=1).decode(part.get_charsets()[0])
                        description += u'\n\nVous trouverez les éventuels fichiers dans le répertoire: %s' % stockdir
                        continue
                    else:
                        description += u'\n\nCe message est en "%s", vous trouverez ce texte dans le répertoire: %s' % (part.get_content_type(), stockdir)
                elif part.get_content_type() == 'message/rfc822':
                    continue
                if not os.path.isdir(newdir):
                    os.mkdir(newdir)

                counter += 1
                fd = file(os.path.join(newdir, filename), 'w')
                fd.write(part.get_payload(decode=1))
                fd.close()
        else:
            description = msg.get_payload(decode=1).decode(msg.get_charsets()[0])

        project = self.project_re.search(subject)
        if project:
            project = project.groups()[0]
        else:
            project = ''

        for partner in partners:
            self.rpc(('res.partner.event', 'create', {'name' : subject, 'partner_id' : partner, 'description' : description, 'project' : project}))


if __name__ == '__main__':
    rpc_dispatcher = CommandDispatcher(RPCProxy(4, 'admin'))
    dispatcher = CommandDispatcher(ReceiverEmail2Event(rpc_dispatcher))
    parser = EmailParser(['To', 'Cc', 'From'], dispatcher)
    parser.parse(email.message_from_file(sys.stdin))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

