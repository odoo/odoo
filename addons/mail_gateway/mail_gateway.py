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
import email, mimetypes
from email.Header import decode_header
from email.MIMEText import MIMEText
import xmlrpclib
import os
import binascii
import time, socket

from tools.translate import _

import tools
from osv import fields,osv,orm
from osv.orm import except_orm
import email
import netsvc
from poplib import POP3, POP3_SSL
from imaplib import IMAP4, IMAP4_SSL   

class mail_gateway_server(osv.osv):
    _name = "mail.gateway.server"
    _description = "Email Gateway Server"
    _columns = {
        'name': fields.char('Server Address',size=64,required=True ,help="IMAP/POP Address Of Email gateway Server"),
        'login': fields.char('User',size=64,required=True,help="User Login Id of Email gateway"),
        'password': fields.char('Password',size=64,required=True,help="User Password Of Email gateway"),
        'server_type': fields.selection([("pop","POP"),("imap","Imap")],"Type of Server", required=True, help="Type of Email gateway Server"),
        'port': fields.integer("Port" , help="Port Of Email gateway Server. If port is omitted, the standard POP3 port (110) is used for POP EMail Server and the standard IMAP4 port (143) is used for IMAP Sever."),
        'ssl': fields.boolean('SSL',help ="Use Secure Authentication"),
        'active': fields.boolean('Active', help="If the active field is set to true, it will allow you to hide the email gateway server without removing it."),
    }
    _defaults = {
        'server_type':lambda * a:'pop',
        'active':lambda * a:True,
    }
    
    def check_duplicate(self, cr, uid, ids):
        vals = self.read(cr, uid, ids, ['name', 'login'])[0]
        cr.execute("select count(id) from mail_gateway_server \
                        where name='%s' and login='%s'" % \
                        (vals['name'], vals['login']))
        res = cr.fetchone()
        if res:
            if res[0] > 1:
                return False
        return True 

    _constraints = [
        (check_duplicate, 'Warning! Can\'t have duplicate server configuration!', ['name', 'login'])
    ]
    
    def onchange_server_type(self, cr, uid, ids, server_type=False, ssl=False):
        port = 0
        if server_type == 'pop':
            port = ssl and 995 or 110
        elif server_type == 'imap':
            port = ssl and 993 or 143
        return {'value':{'port':port}}
    
mail_gateway_server()


class mail_gateway(osv.osv):
    _name = "mail.gateway"
    _description = "Email Gateway"

    _columns = {
        'name': fields.char('Name',size=64,help="Name of Mail Gateway."),
        'server_id': fields.many2one('mail.gateway.server',"Gateway Server", required=True),
        'object_id': fields.many2one('ir.model',"Model", required=True),
        'reply_to': fields.char('TO', size=64, help="Email address used in reply to/from of outgoing messages"),
        'email_default': fields.char('Default eMail',size=64,help="Default eMail in case of any trouble."),        
        'mail_history': fields.one2many("mail.gateway.history","gateway_id","History", readonly=True)
    }
    _defaults = {
        'reply_to': lambda * a:tools.config.get('email_from',False)
    }

    def _fetch_mails(self, cr, uid, ids=False, context={}):
        '''
        Function called by the scheduler to fetch mails
        '''
        cr.execute('select * from mail_gateway gateway \
                inner join mail_gateway_server server \
                on server.id = gateway.server_id where server.active = True')
        ids2 = map(lambda x: x[0], cr.fetchall() or [])
        return self.fetch_mails(cr, uid, ids=ids2, context=context)

    def parse_mail(self, cr, uid, gateway_id, email_message, context={}):
        msg_id, res_id, note = (False, False, False)        
        mail_history_obj = self.pool.get('mail.gateway.history')        
        mailgateway = self.browse(cr, uid, gateway_id, context=context)
        try :
            msg_txt = email.message_from_string(email_message)
            msg_id =  msg_txt['Message-ID']
            res_id = self.msg_parse(cr, uid, gateway_id, msg_txt)            
        except Exception, e:
            import traceback
            note = "Error in Parsing Mail: %s " %(str(e))            
            netsvc.Logger().notifyChannel('Emailgate: Parsing mail:%s' % (mailgateway and (mailgateway.name or
                     '%s (%s)'%(mailgateway.server_id.login, mailgateway.server_id.name))) or ''
                     , netsvc.LOG_ERROR, traceback.format_exc())

        mail_history_obj.create(cr, uid, {'name': msg_id, 'res_id': res_id, 'gateway_id': mailgateway.id, 'note': note})
        return res_id,  note

    def fetch_mails(self, cr, uid, ids=[], context={}):        
        log_messages = []
        mailgate_server = False
        new_messages = []
        for mailgateway in self.browse(cr, uid, ids):
            try :
                mailgate_server = mailgateway.server_id
                if not mailgate_server.active:
                    continue
                mailgate_name =  mailgateway.name or "%s (%s)" % (mailgate_server.login, mailgate_server.name)
                res_model = mailgateway.object_id.name
                log_messages.append("Mail Server : %s" % mailgate_name)
                log_messages.append("="*40)
                new_messages = []
                if mailgate_server.server_type == 'pop':
                    if mailgate_server.ssl:
                        pop_server = POP3_SSL(mailgate_server.name or 'localhost', mailgate_server.port or 995)
                    else:
                        pop_server = POP3(mailgate_server.name or 'localhost', mailgate_server.port or 110)
                    pop_server.user(mailgate_server.login)
                    pop_server.pass_(mailgate_server.password)
                    pop_server.list()
                    (numMsgs, totalSize) = pop_server.stat()
                    for i in range(1, numMsgs + 1):
                        (header, msges, octets) = pop_server.retr(i)
                        res_id, note = self.parse_mail(cr, uid, mailgateway.id, '\n'.join(msges))
                        log = ''
                        if res_id:
                            log = _('Object Successfully Created : %d of %s'% (res_id, res_model))
                        if note:
                            log = note
                        log_messages.append(log)
                        new_messages.append(i)
                    pop_server.quit()

                elif mailgate_server.server_type == 'imap':
                    if mailgate_server.ssl:
                        imap_server = IMAP4_SSL(mailgate_server.name or 'localhost', mailgate_server.port or 993)
                    else:
                        imap_server = IMAP4(mailgate_server.name or 'localhost', mailgate_server.port or 143)
                    imap_server.login(mailgate_server.login, mailgate_server.password)
                    imap_server.select()
                    typ, data = imap_server.search(None, '(UNSEEN)')
                    for num in data[0].split():
                        typ, data = imap_server.fetch(num, '(RFC822)')
                        res_id, note = self.parse_mail(cr, uid, mailgateway.id, data[0][1])
                        log = ''
                        if res_id:
                            log = _('Object Successfully Created/Modified: %d of %s'% (res_id, res_model))
                        if note:
                            log = note
                        log_messages.append(log)
                        new_messages.append(num)
                    imap_server.close()
                    imap_server.logout()

            except Exception, e:
                 import traceback
                 log_messages.append("Error in Fetching Mail: %s " %(str(e)))                 
                 netsvc.Logger().notifyChannel('Emailgate: Fetching mail:[%d]%s' % 
                    (mailgate_server and mailgate_server.id or 0, mailgate_server and mailgate_server.name or ''),
                     netsvc.LOG_ERROR, traceback.format_exc())

            log_messages.append("-"*25)
            log_messages.append("Total Read Mail: %d\n\n" %(len(new_messages)))
        return log_messages    

    def emails_get(self, email_from):
        res = tools.email_re.search(email_from)
        return res and res.group(1)

    def partner_get(self, cr, uid, email):
        mail = self.emails_get(email)
        adr_ids = self.pool.get('res.partner.address').search(cr, uid, [('email', '=', mail)])
        if not adr_ids:
            return {}
        adr = self.pool.get('res.partner.address').read(cr, uid, adr_ids, ['partner_id'])
        res = {}
        if len(adr):
            res = {
                'partner_address_id': adr[0]['id'],
                'partner_id': adr[0].get('partner_id',False) and adr[0]['partner_id'][0] or False
            }
        return res

    def _to_decode(self, s, charsets):
       for charset in charsets:
           if charset:
               try:
                   return s.decode(charset)
               except UnicodeError:  
                    pass         
       try:
           return s.decode('ascii')
       except UnicodeError:
           return s 

    def _decode_header(self, s):        
        from email.Header import decode_header
        s = decode_header(s)
        return ''.join(map(lambda x:self._to_decode(x[0], x[1]), s))

    def msg_new(self, cr, uid, msg, model):
        message = self.msg_body_get(msg)
        res_model = self.pool.get(model)
        res_id = res_model.msg_new(cr, uid, msg)
        if res_id:
            attachments = message['attachment']

            for attach in attachments or []:
                data_attach = {
                    'name': str(attach),
                    'datas':binascii.b2a_base64(str(attachments[attach])),
                    'datas_fname': str(attach),
                    'description': 'Mail attachment',
                    'res_model': model,
                    'res_id': res_id
                }
                self.pool.get('ir.attachment').create(cr, uid, data_attach)
        return res_id


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
                    message['body'] += tools.html2plaintext(txt)  
                
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

    def msg_update(self, cr, uid, msg, res_id, res_model, user_email):        
        if user_email and self.emails_get(user_email)==self.emails_get(self._decode_header(msg['From'])):
            return self.msg_user(cr, uid, msg, res_id, res_model)
        else:
            return self.msg_partner(cr, uid, msg, res_id, res_model)

    def msg_act_get(self, msg):
        body = self.msg_body_get(msg)

        # handle email body commands (ex: Set-State: Draft)
        actions = {}
        body_data = ''
        for line in body['body'].split('\n'):
            res = tools.command_re.match(line)
            if res:
                actions[res.group(1).lower()] = res.group(2).lower()
            else:
                body_data += line+'\n'
        return actions, body_data

    def msg_user(self, cr, uid, msg, res_id, res_model):
        actions, body_data = self.msg_act_get(msg)        
        data = {}
        if 'user' in actions:
            uids = self.pool.get('res.users').name_search(cr, uid, actions['user'])
            if uids:
                data['user_id'] = uids[0][0]

        res_model = self.pool.get(res_model)        
        return res_model.msg_update(cr, uid, res_id, msg, data=data, default_act='pending')        

    def msg_send(self, msg, reply_to, emails, priority=None, res_id=False):         
        if not emails:
            return False                
        msg_to = [emails[0]]
        msg_subject = msg['Subject']        
        msg_cc = []
        msg_body = self.msg_body_get(msg)        
        if len(emails)>1:            
            msg_cc = emails[1:]
        msg_attachment = map(lambda x: (x[0], x[1]), msg_body['attachment'].items())                  
        return tools.email_send(reply_to, msg_to, msg_subject , msg_body['body'], email_cc=msg_cc, 
                         reply_to=reply_to, attach=msg_attachment, openobject_id=res_id, priority=priority)
        

    def msg_partner(self, cr, uid, msg, res_id, res_model):
        res_model = self.pool.get(res_model)        
        return res_model.msg_update(cr, uid, res_id, msg, data={}, default_act='open')      

    

    def msg_parse(self, cr, uid, mailgateway_id, msg):
        mailgateway = self.browse(cr, uid, mailgateway_id)
        res_model = mailgateway.object_id.model
        res_str = tools.reference_re.search(msg.get('References', ''))
        if res_str:
            res_str = res_str.group(1)
        else:
            res_str = tools.res_re.search(msg.get('Subject', ''))
            if res_str:
                res_str = res_str.group(1)

        def msg_test(res_str):
            emails = ('', '', '', '')
            if not res_str:
                return (False, emails)  
            res_str = int(res_str)          
            if hasattr(self.pool.get(res_model), 'emails_get'):
                emails = self.pool.get(res_model).emails_get(cr, uid, [res_str])[0]
            return (res_str, emails)

        (res_id, emails) = msg_test(res_str)
        user_email, from_email, cc_email, priority = emails
        if res_id:
            self.msg_update(cr, uid, msg, res_id, res_model, user_email)
            
        else:
            res_id = self.msg_new(cr, uid, msg, res_model)
            (res_id, emails) = msg_test(res_id)
            user_email, from_email, cc_email, priority = emails
            subject = self._decode_header(msg['subject'])
            if msg.get('Subject', ''):
                del msg['Subject']
            msg['Subject'] = '[%s] %s' %(str(res_id), subject)            

        em = [user_email or '', from_email] + (cc_email or '').split(',')
        emails = map(self.emails_get, filter(None, em))
        mm = [self._decode_header(msg['From']), self._decode_header(msg['To'])]+self._decode_header(msg.get('Cc','')).split(',')
        msg_mails = map(self.emails_get, filter(None, mm))
        emails = filter(lambda m: m and m not in msg_mails, emails)
        try:
            self.msg_send(msg, mailgateway.reply_to, emails, priority, res_id)
            if hasattr(self.pool.get(res_model), 'msg_send'):
                emails = self.pool.get(res_model).msg_send(cr, uid, res_id)
        except Exception, e:
            if mailgateway.email_default:
                a = self._decode_header(msg['Subject'])
                del msg['Subject']
                msg['Subject'] = '[OpenERP-Error] ' + a
                self.msg_send(msg, mailgateway.reply_to, mailgateway.email_default.split(','), res_id)
            raise e 
        return res_id

mail_gateway()

class mail_gateway_history(osv.osv):
    _name = "mail.gateway.history"
    _description = "Mail Gateway History"
    _columns = {
        'name': fields.char('Message Id', size=64, help="Message Id in Email Server."),
        'res_id': fields.integer("Resource ID"),        
        'gateway_id': fields.many2one('mail.gateway',"Mail Gateway", required=True),
        'model_id':fields.related('gateway_id', 'object_id', type='many2one', relation='ir.model', string='Model'), 
        'note': fields.text('Notes'),
        'create_date': fields.datetime('Created Date'),
    }
    _order = 'id desc'
mail_gateway_history()
