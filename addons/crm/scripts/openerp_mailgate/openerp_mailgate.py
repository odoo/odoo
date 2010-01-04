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

email_re = re.compile(r"""
    ([a-zA-Z][\w\.-]*[a-zA-Z0-9]     # username part
    @                                # mandatory @ sign
    [a-zA-Z0-9][\w\.-]*              # domain must start with a letter ... Ged> why do we include a 0-9 then?
     \.
     [a-z]{2,3}                      # TLD
    )
    """, re.VERBOSE)
case_re = re.compile(r"\[([0-9]+)\]", re.UNICODE)
command_re = re.compile("^Set-([a-z]+) *: *(.+)$", re.I + re.UNICODE)
reference_re = re.compile("<.*-tinycrm-(\\d+)@(.*)>", re.UNICODE)

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
        title = link.renderContents()
        for url in [x[1] for x in link.attrs if x[0]=='href']:
            urls.append(dict(url=url, tag=str(link), title=title))

    html = soup.__str__()
            
    url_index = []
    i = 0
    for d in urls:
        if d['title'] == d['url'] or 'http://'+d['title'] == d['url']:
            html = html.replace(d['tag'], d['url'])
        else:
            i += 1
            html = html.replace(d['tag'], '%s [%s]' % (d['title'], i))
            url_index.append(d['url'])

    html = html.replace('<strong>','*').replace('</strong>','*')
    html = html.replace('<b>','*').replace('</b>','*')
    html = html.replace('<h3>','*').replace('</h3>','*')
    html = html.replace('<h2>','**').replace('</h2>','**')
    html = html.replace('<h1>','**').replace('</h1>','**')
    html = html.replace('<em>','/').replace('</em>','/')
    

    # the only line breaks we respect is those of ending tags and 
    # breaks
    
    html = html.replace('\n',' ')
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

    def __call__(self, *request):
        return self.rpc.execute(self.dbname, self.user_id, self.passwd, *request)

class email_parser(object):
    def __init__(self, uid, password, section, email, email_default, dbname, host, port):        
        self.rpc = rpc_proxy(uid, password, host=host, port=port, dbname=dbname)
        try:
            self.section_id = int(section)
        except:
            self.section_id = self.rpc('crm.case.section', 'search', [('code','=',section)])[0]
        self.email = email
        self.email_default = email_default
        self.canal_id = False

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
            'partner_id': adr[0].get('partner_id',False) and adr[0]['partner_id'][0] or False
        }

    def _decode_header(self, s):
        from email.Header import decode_header
        s = decode_header(s)
        return ''.join(map(lambda x:x[0].decode(x[1] or 'ascii', 'replace'), s))

    def msg_new(self, msg):
        message = self.msg_body_get(msg)
        data = {
            'name': self._decode_header(msg['Subject']),
            'section_id': self.section_id,
            'email_from': self._decode_header(msg['From']),
            'email_cc': self._decode_header(msg['Cc'] or ''),
            'canal_id': self.canal_id,
            'user_id': False,
            'description': message['body'],
            'history_line': [(0, 0, {'description': message['body'], 'email': msg['From'] })],
        }
        try:
            data.update(self.partner_get(self._decode_header(msg['From'])))
        except Exception, e:
            import netsvc
            netsvc.Logger().notifyChannel('mailgate', netsvc.LOG_ERROR, "%s" % e)

        try:
            id = self.rpc('crm.case', 'create', data)
            self.rpc('crm.case','case_open', [id])    
        except Exception,e:
            if getattr(e,'faultCode','') and 'AccessError' in e.faultCode:
                e = '\n\nThe Specified user does not have an access to the CRM case.'
            print e
        attachments = message['attachment']

        for attach in attachments or []:
            data_attach = {
                'name': str(attach),
                'datas':binascii.b2a_base64(str(attachments[attach])),
                'datas_fname': str(attach),
                'description': 'Mail attachment',
                'res_model': 'crm.case',
                'res_id': id
            }
            self.rpc('ir.attachment', 'create', data_attach)

        return id

#   #change the return type format to dictionary
#   {
#       'body':'body part',
#       'attachment':{
#                       'file_name':'file data',
#                       'file_name':'file data',
#                       'file_name':'file data',
#                   }
#   }
#   #
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
                    txt = buf.decode(part.get_charsets()[0] or 'ascii', 'replace')
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
    #end def

    def msg_user(self, msg, id):
        body = self.msg_body_get(msg)

        # handle email body commands (ex: Set-State: Draft)
        actions = {}
        body_data=''
        for line in body['body'].split('\n'):
            res = command_re.match(line)
            if res:
                actions[res.group(1).lower()] = res.group(2).lower()
            else:
                body_data += line+'\n'
        body['body'] = body_data

        data = {
            'description': body['body'],
            'history_line': [(0, 0, {'description': body['body'], 'email': msg['From']})],
        }
        act = 'case_pending'
        if 'state' in actions:
            if actions['state'] in ['draft','close','cancel','open','pending']:
                act = 'case_' + actions['state']

        for k1,k2 in [('cost','planned_cost'),('revenue','planned_revenue'),('probability','probability')]:
            try:
                data[k2] = float(actions[k1])
            except:
                pass

        if 'priority' in actions:
            if actions['priority'] in ('1','2','3','4','5'):
                data['priority'] = actions['priority']

        if 'partner' in actions:
            data['email_from'] = actions['partner'][:128]

        if 'user' in actions:
            uids = self.rpc('res.users', 'name_search', actions['user'])
            if uids:
                data['user_id'] = uids[0][0]

        self.rpc('crm.case', act, [id])
        self.rpc('crm.case', 'write', [id], data)
        return id

    def msg_send(self, msg, emails, priority=None):
        if not len(emails):
            return False
        del msg['To']
        msg['To'] = emails[0]
        if len(emails)>1:
            if 'Cc' in msg:
                del msg['Cc']
            msg['Cc'] = ','.join(emails[1:])
        del msg['Reply-To']
        msg['Reply-To'] = self.email
        if priority:
            msg['X-Priority'] = priorities.get(priority, '3 (Normal)')
        s = smtplib.SMTP()
        s.connect()
        s.sendmail(self.email, emails, msg.as_string())
        s.close()
        return True

    def msg_partner(self, msg, id):
        message = self.msg_body_get(msg)
        body = message['body']
        act = 'case_open'
        self.rpc('crm.case', act, [id])
        body2 = '\n'.join(map(lambda l: '> '+l, (body or '').split('\n')))
        data = {
            'description':body,
            'history_line': [(0, 0, {'description': body, 'email': msg['From'][:84]})],
        }
        self.rpc('crm.case', 'write', [id], data)
        return id

    def msg_test(self, msg, case_str):
        if not case_str:
            return (False, False)
        emails = self.rpc('crm.case', 'emails_get', int(case_str))
        return (int(case_str), emails)

    def parse(self, msg):
        case_str = reference_re.search(msg.get('References', ''))
        if case_str:
            case_str = case_str.group(1)
        else:
            case_str = case_re.search(msg.get('Subject', ''))
            if case_str:
                case_str = case_str.group(1)
        (case_id, emails) = self.msg_test(msg, case_str)
        if case_id:
            if emails[0] and self.email_get(emails[0])==self.email_get(self._decode_header(msg['From'])):
                self.msg_user(msg, case_id)
            else:
                self.msg_partner(msg, case_id)
        else:
            case_id = self.msg_new(msg)
            subject = self._decode_header(msg['subject'])
            if msg.get('Subject', ''):
                del msg['Subject']
            msg['Subject'] = '['+str(case_id)+'] '+subject
            msg['Message-Id'] = '<'+str(time.time())+'-tinycrm-'+str(case_id)+'@'+socket.gethostname()+'>'

        emails = self.rpc('crm.case', 'emails_get', case_id)
        priority = emails[3]
        em = [emails[0], emails[1]] + (emails[2] or '').split(',')
        emails = map(self.email_get, filter(None, em))

        mm = [self._decode_header(msg['From']), self._decode_header(msg['To'])]+self._decode_header(msg.get('Cc','')).split(',')
        msg_mails = map(self.email_get, filter(None, mm))

        emails = filter(lambda m: m and m not in msg_mails, emails)
        try:
            self.msg_send(msg, emails, priority)
        except:
            if self.email_default:
                a = self._decode_header(msg['Subject'])
                del msg['Subject']
                msg['Subject'] = '[OpenERP-CaseError] ' + a
                self.msg_send(msg, self.email_default.split(','))
        return case_id, emails

if __name__ == '__main__':
    import sys, optparse
    parser = optparse.OptionParser(
        usage='usage: %prog [options]',
        version='%prog v1.0')

    group = optparse.OptionGroup(parser, "Note",
        "This program parse a mail from standard input and communicate "
        "with the Open ERP server for case management in the CRM module.")
    parser.add_option_group(group)

    parser.add_option("-u", "--user", dest="userid", help="ID of the user in Open ERP", default=1, type='int')
    parser.add_option("-p", "--password", dest="password", help="Password of the user in Open ERP", default='admin')
    parser.add_option("-e", "--email", dest="email", help="Email address used in the From field of outgoing messages")
    parser.add_option("-s", "--section", dest="section", help="ID or code of the case section", default="support")
    parser.add_option("-m", "--default", dest="default", help="Default eMail in case of any trouble.", default=None)
    parser.add_option("-d", "--dbname", dest="dbname", help="Database name (default: terp)", default='terp')
    parser.add_option("--host", dest="host", help="Hostname of the Open ERP Server", default="localhost")
    parser.add_option("--port", dest="port", help="Port of the Open ERP Server", default="8069")


    (options, args) = parser.parse_args()
    parser = email_parser(options.userid, options.password, options.section, options.email, options.default, dbname=options.dbname, host=options.host, port=options.port)

    msg_txt = email.message_from_file(sys.stdin)

    try :
        parser.parse(msg_txt)
    except Exception,e:
        if getattr(e,'faultCode','') and 'Connection unexpectedly closed' in e.faultCode:
            print e
 
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

