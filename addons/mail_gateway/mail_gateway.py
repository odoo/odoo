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

class one2many_domain(fields.one2many):
    def set(self, cr, obj, id, field, values, user=None, context=None):
        if not values:
            return
        return super(one2many_domain, self).set(cr, obj, id, field, values, 
                                            user=user, context=context)

    def get(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None):
        if not context:
            context = {}
        res = {}
        msg_obj = obj.pool.get('mailgate.message')
        for thread in obj.browse(cr, user, ids, context=context):
            final = msg_obj.search(cr, user, self._domain + [('thread_id', '=', thread.id)], context=context)
            res[thread.id] = final
        return res
        
        
class mailgate_thread(osv.osv):
    '''
    Mailgateway Thread
    '''
    _name = 'mailgate.thread'
    _description = 'Mailgateway Thread'
    _rec_name = 'thread' 

    _columns = {
        'thread': fields.char('Thread', size=32, required=False),  
        'message_ids': one2many_domain('mailgate.message', 'thread_id', 'Messages', domain=[('history', '=', True)], required=False), 
        'log_ids': one2many_domain('mailgate.message', 'thread_id', 'Logs', domain=[('history', '=', False)], required=False),
        }
        
    def __history(self, cr, uid, cases, keyword, history=False, email=False, details=None, email_from=False, message_id=False, context={}):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param cases: a browse record list
        @param keyword: Case action keyword e.g.: If case is closed "Close" keyword is used
        @param history: Value True/False, If True it makes entry in case History otherwise in Case Log
        @param email: Email address if any
        @param details: Details of case history if any 
        @param context: A standard dictionary for contextual values"""
        if not context:
            context = {}
        # The mailgate sends the ids of the cases and not the object list
        if all(isinstance(case_id, (int, long)) for case_id in cases) and context.get('model'):
            cases = self.pool.get(context['model']).browse(cr, uid, cases, context=context)

        model_obj = self.pool.get('ir.model')
        
        obj = self.pool.get('mailgate.message')
        for case in cases:
            model_ids = model_obj.search(cr, uid, [('model', '=', case._name)])
            data = {
                'name': keyword,
                'user_id': uid,
                'model_id' : model_ids and model_ids[0] or False,
                'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'thread_id': case.thread_id.id,                
                'message_id': message_id
            }

            if history:
                data['history'] = True
                data['description'] = details or case.description
                data['email_to'] = email or \
                        (case.user_id and case.user_id.address_id and \
                            case.user_id.address_id.email) or tools.config.get('email_from', False)
                data['email_from'] = email_from or \
                        (case.user_id and case.user_id.address_id and \
                            case.user_id.address_id.email) or tools.config.get('email_from', False)
            res = obj.create(cr, uid, data, context)
        return True
    
    _history = __history
    history = __history
    

mailgate_thread()

class mailgate_message(osv.osv):
    '''
    Mailgateway Message
    '''
    _name = 'mailgate.message'
    _description = 'Mailgateway Message'
    _order = 'date desc'

    _columns = {
        'name':fields.char('Message', size=64),
        'model_id': fields.many2one('ir.model', 'Model'),
        'thread_id':fields.many2one('mailgate.thread', 'Thread'),
        'date': fields.datetime('Date'),
        'history': fields.boolean('Is History?', required=False), 
        'user_id': fields.many2one('res.users', 'User Responsible', readonly=True),
        'message': fields.text('Description'),
        'email_from': fields.char('Email From', size=84),
        'email_to': fields.char('Email To', size=84),
        'email_cc': fields.char('Email From', size=84),
        'email_bcc': fields.char('Email From', size=84),
        'message_id': fields.char('Message Id', size=1024, readonly=True, help="Message Id on Email Server.", select=True),
        'description': fields.text('Description'), 
        'attachment_ids': fields.many2many('ir.attachment', 'message_attachment_rel', 'message_id', 'attachment_id', 'Attachments'),
    }

mailgate_message()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
