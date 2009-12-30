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


from tools.translate import _

import tools
from osv import fields,osv,orm
from osv.orm import except_orm

from scripts.openerp_mailgate import openerp_mailgate
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
        'to_email_id': fields.char('TO', size=64, help="Email address used in the From field of outgoing messages"),
        'cc_email_id': fields.char('CC',size=64,help="Default eMail in case of any trouble."),        
        'mail_history': fields.one2many("mail.gateway.history","gateway_id","History", readonly=True)
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

    def parse_mail(self, cr, uid, gateway_id, email_message, email_parser=None, context={}):
        msg_id = case_id = note = False
        user_obj = self.pool.get('res.users')
        mail_history_obj = self.pool.get('mail.gateway.history')
        users = user_obj.read(cr, uid, uid, ['password'])
        mailgateway = self.browse(cr, uid, gateway_id, context=context)
        try :
            if not email_parser:
                email_parser = openerp_mailgate.email_parser(uid, users['password'], 
                                mailgateway.to_email_id or '', mailgateway.cc_email_id or '', dbname=cr.dbname,
                                host=tools.config['interface'] or 'localhost', port=tools.config['port'] or '8069')

            msg_txt = email.message_from_string(email_message)
            msg_id =  msg_txt['Message-ID']
            res_id = email_parser.parse(msg_txt)[0]
            res_model = False
        except Exception, e:
            note = "Error in Parsing Mail: %s " %(str(e))
            netsvc.Logger().notifyChannel('Emailgate: Parsing mail:%s' % (mailgateway.name or
                         '%s (%s)'%(mailgateway.server_id.login, mailgateway.server_id.name)), netsvc.LOG_ERROR, str(e))

        mail_history_obj.create(cr, uid, {'name':msg_id, 'res_id': res_id, 'res_model': res_model,'gateway_id':mailgateway.id, 'note':note})
        return res_id, res_model, note

    def fetch_mails(self, cr, uid, ids=[], context={}):        
        log_messages = []
        for mailgateway in self.browse(cr, uid, ids):
            try :
                mailgate_server = mailgateway.server_id
                if not mailgate_server.active:
                    continue
                mailgate_name =  mailgateway.name or "%s (%s)" % (mailgate_server.login, mailgate_server.name)
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
                        res_id, res_model, note = self.parse_mail(cr, uid, mailgateway.id, '\n'.join(msges))
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
                        res_id, res_model, note = self.parse_mail(cr, uid, mailgateway.id, data[0][1])
                        log = ''
                        if res_id:
                            log = _('Object Successfully Created : %d of %s'% (res_id, res_model))
                        if note:
                            log = note
                        log_messages.append(log)
                        new_messages.append(num)
                    imap_server.close()
                    imap_server.logout()

            except Exception, e:
                 log_messages.append("Error in Fetching Mail: %s " %(str(e)))
                 netsvc.Logger().notifyChannel('Emailgate: Fetching mail:[%d]%s' % (mailgate_server.id, mailgate_server.name), netsvc.LOG_ERROR, str(e))

            log_messages.append("-"*25)
            log_messages.append("Total Read Mail: %d\n\n" %(len(new_messages)))
        return log_messages

mail_gateway()

class mail_gateway_history(osv.osv):
    _name = "mail.gateway.history"
    _description = "Mail Gateway History"
    _columns = {
        'name': fields.char('Message Id', size=64, help="Message Id in Email Server."),
        'res_id': fields.integer("Resource ID"),
        'res_model': fields.many2one('ir.model',"Model"),
        'gateway_id': fields.many2one('mail.gateway',"Mail Gateway", required=True),
        'note': fields.text('Notes'),
    }
    _order = 'id desc'
mail_gateway_history()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

