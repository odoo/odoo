#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import re
import smtplib
import email, mimetypes
from email.Header import decode_header
from email.MIMEText import MIMEText
import xmlrpclib
import os
import binascii
import time, socket


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

def html2plaintext(html, body_id=None, encoding='utf-8'):
    ## (c) Fry-IT, www.fry-it.com, 2007
    ## <peter@fry-it.com>
    ## download here: http://www.peterbe.com/plog/html2plaintext
    
    
    """ from an HTML text, convert the HTML to plain text.
    If @body_id is provided then this is the tag where the 
    body (not necessarily <body>) starts.
    """
    try:
        from BeautifulSoup import BeautifulSoup, SoupStrainer, Comment
    except:
        return html
            
    urls = []
    if body_id is not None:
        strainer = SoupStrainer(id=body_id)
    else:
        strainer = SoupStrainer('body')
    
    soup = BeautifulSoup(html, parseOnlyThese=strainer, fromEncoding=encoding)
    for link in soup.findAll('a'):
        title = unicode(link)
        for url in [x[1] for x in link.attrs if x[0]=='href']:
            urls.append(dict(url=url, tag=unicode(link), title=title))

    html = unicode(soup)
            
    url_index = []
    i = 0
    for d in urls:
        if d['title'] == d['url'] or 'http://'+d['title'] == d['url']:
            html = html.replace(d['tag'], d['url'])
        else:
            i += 1
            html = html.replace(d['tag'], '%s [%s]' % (d['title'], i))
            url_index.append(d['url'])

    html = html.replace('<strong>', '*').replace('</strong>', '*')
    html = html.replace('<b>', '*').replace('</b>', '*')
    html = html.replace('<h3>', '*').replace('</h3>', '*')
    html = html.replace('<h2>', '**').replace('</h2>', '**')
    html = html.replace('<h1>', '**').replace('</h1>', '**')
    html = html.replace('<em>', '/').replace('</em>', '/')
    

    # the only line breaks we respect is those of ending tags and 
    # breaks
    
    html = html.replace('\n', ' ')
    html = html.replace('<br>', '\n')
    html = html.replace('<tr>', '\n')
    html = html.replace('</p>', '\n\n')
    html = re.sub('<br\s*/>', '\n', html)
    html = html.replace(' ' * 2, ' ')


    # for all other tags we failed to clean up, just remove then and 
    # complain about them on the stderr
    def desperate_fixer(g):
        #print >>sys.stderr, "failed to clean up %s" % str(g.group())
        return ' '

    html = re.sub('<.*?>', desperate_fixer, html)

    # lstrip all lines
    html = '\n'.join([x.lstrip() for x in html.splitlines()])

    for i, url in enumerate(url_index):
        if i == 0:
            html += '\n\n'
        html += '[%s] %s\n' % (i+1, url)       
    return html

class rpc_proxy(object):
    def __init__(self, uid, passwd, host='localhost', port=8069, path='object', dbname='terp'):        
        self.rpc = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/%s' % (host, port, path))
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
        res = email_re.search(email_from)
        return res and res.group(1)

    def partner_get(self, email):
        mail = self.email_get(email)
        adr_ids = self.rpc('res.partner.address', 'search', [('email', '=', mail)])
        if not adr_ids:
            return {}
        adr = self.rpc('res.partner.address', 'read', adr_ids, ['partner_id'])
        return {
            'partner_address_id': adr[0]['id'], 
            'partner_id': adr[0].get('partner_id', False) and adr[0]['partner_id'][0] or False
        }

    def _to_decode(self, s, charsets):
       for charset in charsets:
           if charset:
               try:
                   return s.decode(charset)
               except UnicodeError:
                    pass
       return s.decode('latin1')

    def _decode_header(self, s):
        from email.Header import decode_header
        s = decode_header(s.replace('\r', '')) 
        return ''.join(map(lambda x:self._to_decode(x[0], [x[1]]), s or []))
    
    def history(self, model, new_id, msg_id, ref_id, subject, msg_to, msg_from, body, attach):
        try:
            thread_id = self.rpc(model, 'read', new_id, ['thread_id'])['thread_id'][0]
        except Exception, e:
            thread_id = None
        msg_data = {
                    'name': subject, 
                    'history': True, 
                    'model': model, 
                    'res_id': new_id, 
                    'thread_id': thread_id, 
                    'message_id': msg_id, 
                    'ref_id': ref_id or '', 
                    'user_id': self.rpc.user_id, 
                    'date': time.strftime('%Y-%m-%d %H:%M:%S'), 
                    'email_from': msg_from, 
                    'email_to': msg_to, 
                    'description': body, 
                    'attachment_ids': [(6, 0, attach)]
        }
        msg_id = self.rpc('mailgate.message', 'create', msg_data)
        return True
    
    def msg_new(self, msg):
        message = self.msg_body_get(msg)
        msg_subject = self._decode_header(msg['Subject'])
        msg_from = self._decode_header(msg['From'])
        msg_to = self._decode_header(msg['To'])
        msg_cc = self._decode_header(msg['Cc'] or '')
        
        data = {
            'name': msg_subject, 
            'email_from': msg_from, 
            'email_cc': msg_cc,             
            'user_id': False, 
            'description': message['body'], 
            'state' : 'draft',
        }
        data.update(self.partner_get(msg_from))

        try:
            att_ids = []
            new_id = self.rpc(self.model, 'create', data)
            attachments = message['attachment']        
            for attach in attachments or []:
                data_attach = {
                    'name': str(attach), 
                    'datas': binascii.b2a_base64(str(attachments[attach])), 
                    'datas_fname': str(attach), 
                    'description': 'Mail attachment', 
                    'res_model': self.model, 
                    'res_id': new_id
                }
                att_ids.append(self.rpc('ir.attachment', 'create', data_attach))
            try:
                self.rpc(self.model, 'history', [new_id], 'Receive', True, msg_to, message['body'], msg_from, False, {'model' : self.model})
            except Exception, e:
                self.history(self.model, new_id, msg['Message-Id'], msg['References'], msg_subject, msg_to, msg_from, message['body'], att_ids)
        except Exception, e:
            if getattr(e, 'faultCode', '') and 'AccessError' in e.faultCode:
                e = '\n\nThe Specified user does not have an access to the Model.'
            print e
        

        return new_id

#   #change the return type format to dictionary
#   {
#       'body':'body part',
#       'attachment':{
#                       'file_name':'file data',
#                       'file_name':'file data',
#                       'file_name':'file data',
#                   }
#   }

    def msg_body_get(self, msg):
        message = {};
        message['body'] = '';
        message['attachment'] = {};
        attachment = message['attachment'];
        counter = 1;
        def replace(match):
            return ''

        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue

            if part.get_content_maintype()=='text':
                buf = part.get_payload(decode=True)
                if buf:
                    txt = self._to_decode(buf, part.get_charsets())
                    txt = re.sub("<(\w)>", replace, txt)
                    txt = re.sub("<\/(\w)>", replace, txt)
                if txt and part.get_content_subtype() == 'plain':
                    message['body'] += txt 
                elif txt and part.get_content_subtype() == 'html':                                                               
                    message['body'] += html2plaintext(txt)  
                
                filename = part.get_filename();
                if filename :
                    attachment[filename] = part.get_payload(decode=True);
                    
            elif part.get_content_maintype()=='application' or part.get_content_maintype()=='image' or part.get_content_maintype()=='text':
                filename = part.get_filename();
                if filename :
                    attachment[filename] = part.get_payload(decode=True);
                else:
                    filename = 'attach_file'+str(counter);
                    counter += 1;
                    attachment[filename] = part.get_payload(decode=True);
                #end if
            #end if
            message['attachment'] = attachment
        #end for        
        return message

    def msg_send(self, msg, emails, priority=None):
        if not len(emails):
            return False
        del msg['To']
        msg['To'] = emails[0]
        msg['Subject'] = 'OpenERP Record-id:' + msg['Subject']
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


    def parse(self, msg):
        #TODO: Something with Message hierarchy 
        res_id = self.msg_new(msg)
        subject = self._decode_header(msg['subject'])
        if msg.get('Subject', ''):
            del msg['Subject']
        msg['Subject'] = '['+str(res_id)+'] '+subject
#        msg['Message-Id'] = '<'+str(time.time())+'-openerpcrm-'+str(res_id)+'@'+socket.gethostname()+'>'

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
    import sys, optparse
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

    msg_txt = email.message_from_file(sys.stdin)

    parser.parse(msg_txt)
 
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
