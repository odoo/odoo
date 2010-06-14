# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>)
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

from osv import osv, fields
import time
import  base64
import re
import tools
import binascii

import email
from email.header import decode_header
import netsvc

logger = netsvc.Logger()


class mailgate_thread(osv.osv):
    '''
    Mailgateway Thread
    '''
    _name = 'mailgate.thread'
    _description = 'Mailgateway Thread'
    _rec_name = 'thread' 

    _columns = {
        'thread': fields.char('Thread', size=32, required=False), 
        'message_ids': fields.one2many('mailgate.message', 'thread_id', 'Messages', domain=[('history', '=', True)], required=False), 
        'log_ids': fields.one2many('mailgate.message', 'thread_id', 'Logs', domain=[('history', '=', False)], required=False), 
        'model': fields.char('Model Name', size=64, required=False),  
        'res_id': fields.integer('Resource ID'), 
        }
        
    def _history(self, cr, uid, cases, keyword, history=False, subject=None, email=False, details=None, email_from=False, message_id=False, attach=None, context=None):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param cases: a browse record list
        @param keyword: Case action keyword e.g.: If case is closed "Close" keyword is used
        @param history: Value True/False, If True it makes entry in case History otherwise in Case Log
        @param email: Email address if any
        @param details: Details of case history if any 
        @param atach: Attachment sent in email
        @param context: A standard dictionary for contextual values"""
        if context is None:
            context = {}
        if attach is None:
            attach = []

        # The mailgate sends the ids of the cases and not the object list

        if all(isinstance(case_id, (int, long)) for case_id in cases):
            cases = self.browse(cr, uid, cases, context=context)

        att_obj = self.pool.get('ir.attachment')
        obj = self.pool.get('mailgate.message')

        for case in cases:
            data = {
                'name': keyword, 
                'user_id': uid, 
                'model' : case._name, 
                'res_id': case.id, 
                'date': time.strftime('%Y-%m-%d %H:%M:%S'), 
                'thread_id': case.thread_id.id,
                'message_id': message_id, 
            }
            attachments = []
            if history:
                for att in attach:
                    attachments.append(att_obj.create(cr, uid, {'name': att[0], 'datas': base64.encodestring(att[1])}))
                
                data = {
                        'name': subject or 'History', 
                        'history': True, 
                        'user_id': uid, 
                        'model' : case._name, 
                        'res_id': case.id,
                        'date': time.strftime('%Y-%m-%d %H:%M:%S'), 
                        'description': details or (hasattr(case, 'description') and case.description or False), 
                        'email_to': email or \
                                (hasattr(case, 'user_id') and case.user_id and case.user_id.address_id and \
                                    case.user_id.address_id.email) or tools.config.get('email_from', False), 
                        'email_from': email_from or \
                                (hasattr(case, 'user_id') and case.user_id and case.user_id.address_id and \
                                    case.user_id.address_id.email) or tools.config.get('email_from', False), 
                        'partner_id': hasattr(case, 'partner_id') and (case.partner_id and case.partner_id.id or False) or False, 
                        'thread_id': case.thread_id.id, 
                        'message_id': message_id, 
                        'attachment_ids': [(6, 0, attachments)]
                        }
            res = obj.create(cr, uid, data, context)
            case._table.log(cr, uid, case.id, case._description + " '" + case.name + "': " + keyword, context=context)
        return True
    
    __history = history = _history
    

mailgate_thread()

class mailgate_message(osv.osv):
    '''
    Mailgateway Message
    '''
    _name = 'mailgate.message'
    _description = 'Mailgateway Message'
    _order = 'date desc'
    _log_create=True

    _columns = {
        'name':fields.char('Message', size=64), 
        'thread_id':fields.many2one('mailgate.thread', 'Thread'), 
        'ref_id': fields.char('Reference Id', size=256, readonly=True, help="Message Id in Email Server.", select=True),
        'date': fields.datetime('Date'), 
        'history': fields.boolean('Is History?', required=False), 
        'user_id': fields.many2one('res.users', 'User Responsible', readonly=True), 
        'message': fields.text('Description'), 
        'email_from': fields.char('Email From', size=84), 
        'email_to': fields.char('Email To', size=84), 
        'email_cc': fields.char('Email CC', size=84), 
        'email_bcc': fields.char('Email BCC', size=84), 
        'message_id': fields.char('Message Id', size=1024, readonly=True, help="Message Id on Email Server.", select=True), 
        'description': fields.text('Description'), 
        'partner_id': fields.many2one('res.partner', 'Partner', required=False), 
        'attachment_ids': fields.many2many('ir.attachment', 'message_attachment_rel', 'message_id', 'attachment_id', 'Attachments'),
        'model': fields.char('Model Name', size=64, required=False),  
        'res_id': fields.integer('Resource ID'), 
    }

mailgate_message()


class mailgate_tool(osv.osv):

    _name = 'email.server.tools'
    _description = "Email Tools"
    _auto = False

    def to_email(self, cr, uid, text):
        _email = re.compile(r'.*<.*@.*\..*>', re.UNICODE)
        def record(path):
            eml = path.group()
            index = eml.index('<')
            eml = eml[index:-1].replace('<', '').replace('>', '')
            return eml

        bits = _email.sub(record, text)
        return bits
    
    def history(self, cr, uid, model, new_id, msg, attach, server_id=None, server_type=None):
        try:
            thread_id = self.pool.get(model).read(cr, uid, new_id, ['thread_id'])['thread_id'][0]
        except Exception, e:
            thread_id = None
        msg_data = {
                    'name': msg.get('subject', 'No subject'), 
                    'date': msg.get('date') , # or time.strftime('%Y-%m-%d %H:%M:%S')??
                    'description': msg.get('body', msg.get('from')), 
                    'history': True,
                    'model': model, 
                    'email_cc': msg.get('cc'), 
                    'email_from': msg.get('from'), 
                    'email_to': msg.get('to'), 
                    'message_id': msg.get('message-id'), 
                    'ref_id': msg.get('references', msg.get('id')), 
                    'res_id': new_id, 
                    'server_id': server_id, 
                    'thread_id': thread_id, 
                    'type': server_type, 
                    'user_id': uid, 
                    'attachment_ids': [(6, 0, attach)]
                    }
        msg_id = self.pool.get('mailgate.message').create(cr, uid, msg_data)
        return True

    def process_email(self, cr, uid, model, message, attach=True, server_id=None, server_type=None, context=None):
        if not context:
            context = {}
        context.update({
            'server_id': server_id
        })
        res_id = False
        def create_record(msg):
            model_pool = self.pool.get(model)
            if hasattr(model_pool, 'message_new'):
                res_id = model_pool.message_new(cr, uid, msg, context)
            else:
                data = {
                    'name': msg.get('subject'), 
                    'email_from': msg.get('from'), 
                    'email_cc': msg.get('cc'), 
                    'user_id': False, 
                    'description': msg.get('body'), 
                    'state' : 'draft', 
                }
                data.update(self.get_partner(cr, uid, msg.get('from'), context=context))
                res_id = model_pool.create(cr, uid, data, context=context)
                logger.notifyChannel('imap', netsvc.LOG_WARNING, 'method def message_new is not define in model %s. Using default method' % (model_pool._name))
            att_ids = []
            if attach:
                for attachment in msg.get('attachments', []):
                    data_attach = {
                        'name': attachment, 
                        'datas': binascii.b2a_base64(str(attachments.get(attachment))), 
                        'datas_fname': attachment, 
                        'description': 'Mail attachment', 
                        'res_model': model, 
                        'res_id': res_id, 
                    }
                    att_ids.append(self.pool.get('ir.attachment').create(cr, uid, data_attach))

            if hasattr(model_pool, 'history'):
                model_pool.history(cr, uid, [res_id], 'Receive', True, msg.get('to'), msg.get('body'), msg.get('from'), False, {'model' : model})
            else:
                self.history(cr, uid, model, res_id, msg, att_ids, server_id=server_id, server_type=server_type)
            
            return res_id

        history_pool = self.pool.get('mailgate.message')
        msg_txt = email.message_from_string(message)
        message_id = msg_txt.get('Message-ID', False)

        msg = {}
        if not message_id:
            return False

        fields = msg_txt.keys()
        msg['id'] = message_id
        msg['message-id'] = message_id

        def _decode_header(txt):
            txt = txt.replace('\r', '')
            return ' '.join(map(lambda (x, y): unicode(x, y or 'ascii'), decode_header(txt)))

        if 'Subject' in fields:
            msg['subject'] = _decode_header(msg_txt.get('Subject'))

        if 'Content-Type' in fields:
            msg['content-type'] = msg_txt.get('Content-Type')

        if 'From' in fields:
            msg['from'] = _decode_header(msg_txt.get('From'))

        if 'Delivered-To' in fields:
            msg['to'] = _decode_header(msg_txt.get('Delivered-To'))

        if 'Cc' in fields:
            msg['cc'] = _decode_header(msg_txt.get('Cc'))

        if 'Reply-To' in fields:
            msg['reply'] = _decode_header(msg_txt.get('Reply-To'))

        if 'Date' in fields:
            msg['date'] = msg_txt.get('Date')

        if 'Content-Transfer-Encoding' in fields:
            msg['encoding'] = msg_txt.get('Content-Transfer-Encoding')

        if 'References' in fields:
            msg['references'] = msg_txt.get('References')

        if 'X-openerp-caseid' in fields:
            msg['caseid'] = msg_txt.get('X-openerp-caseid')

        if 'X-Priority' in fields:
            msg['priority'] = msg_txt.get('X-priority', '3 (Normal)').split(' ')[0]

        if not msg_txt.is_multipart() or 'text/plain' in msg.get('content-type', None):
            encoding = msg_txt.get_content_charset()
            msg['body'] = msg_txt.get_payload(decode=True)
            if encoding:
                msg['body'] = msg['body'].decode(encoding).encode('utf-8')

        attachments = {}
        if msg_txt.is_multipart() or 'multipart/alternative' in msg.get('content-type', None):
            body = ""
            counter = 1
            for part in msg_txt.walk():
                if part.get_content_maintype() == 'multipart':
                    continue

                encoding = part.get_content_charset()

                if part.get_content_maintype()=='text':
                    content = part.get_payload(decode=True)
                    filename = part.get_filename()
                    if filename :
                        attachments[filename] = content
                    else:
                        if encoding:
                            content = unicode(content, encoding)
                        if part.get_content_subtype() == 'html':
                            body = tools.html2plaintext(content)
                        elif part.get_content_subtype() == 'plain':
                            body = content
                elif part.get_content_maintype()=='application' or part.get_content_maintype()=='image' or part.get_content_maintype()=='text':
                    filename = part.get_filename();
                    if filename :
                        attachments[filename] = part.get_payload(decode=True)
                    else:
                        res = part.get_payload(decode=True)
                        if encoding:
                            res = res.decode(encoding).encode('utf-8')

                        body += res

            msg['body'] = body
            msg['attachments'] = attachments

        if msg.get('references', False):
            id = False
            ref = msg.get('references')
            if '\r\n' in ref:
                ref = msg.get('references').split('\r\n')
            else:
                ref = msg.get('references').split(' ')
            if ref:
                hids = history_pool.search(cr, uid, [('name', '=', ref[0].strip())])
                if hids:
                    id = hids[0]
                    history = history_pool.browse(cr, uid, id)
                    model_pool = self.pool.get(model)
                    context.update({
                        'references_id':ref[0]
                    })
                    vals = {}
                    if hasattr(model_pool, 'message_update'):
                        model_pool.message_update(cr, uid, [history.res_id], vals, msg, context=context)
                    else:
                        logger.notifyChannel('imap', netsvc.LOG_WARNING, 'method def message_update is not define in model %s' % (model_pool._name))
                        return False
                else:
                    res_id = create_record(msg)

        else:
            res_id = create_record(msg)

        return res_id

    def get_partner(self, cr, uid, from_email, context=None):
        """This function returns partner Id based on email passed
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks
        @param from_email: email address based on that function will search for the correct
        """
        res = {
            'partner_address_id': False, 
            'partner_id': False
        }
        from_email = self.to_email(cr, uid, from_email)
        address_ids = self.pool.get('res.partner.address').search(cr, uid, [('email', '=', from_email)])
        if address_ids:
            address = self.pool.get('res.partner.address').browse(cr, uid, address_ids[0])
            res['partner_address_id'] = address_ids[0]
            res['partner_id'] = address.partner_id.id

        return res

mailgate_tool()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
