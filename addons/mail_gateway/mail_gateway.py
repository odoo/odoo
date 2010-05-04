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


class mailgate_thread(osv.osv):
    '''
    Mailgateway Thread
    '''
    _name = 'mailgate.thread'
    _description = 'Mailgateway Thread'
    
    def _get_log_ids(self, cr, uid, ids, field_names, arg, context=None):
        """Gets id for case log from history of particular case
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Case IDs
        @param context: A standard dictionary for contextual values
        @return:Dictionary of History Ids
        """
        if not context:
            context = {}

        result = {}
        domain = []
        history_obj = False
        model_obj = self.pool.get('ir.model')
        history_obj = self.pool.get('mailgate.message')

        if 'message_ids' in field_names:
            name = 'message_ids'
            domain += [('email_to', '!=', False)]
            
        if 'log_ids' in field_names:
            name = 'log_ids'
            domain += [('email_to', '=', False)]
        
        model_ids = model_obj.search(cr, uid, [('model', '=', self._name)])
        domain +=  [('model_id', '=', model_ids[0])]
        for case in self.browse(cr, uid, ids, context):
            domain1 =  domain + [('res_id', '=', case.id)]
            history_ids = history_obj.search(cr, uid, domain1, context=context)
            if history_ids:
                result[case.id] = {name: history_ids}
            else:
                result[case.id] = {name: []}
        return result

    _columns = {
        'name':fields.char('Name', size=64), 
        'active': fields.boolean('Active'), 
#        'message_ids':fields.one2many('mailgate.message', 'thread_id', 'Message'),
        'message_ids': fields.function(_get_log_ids, method=True, type='one2many', \
                         multi="message_ids", relation="mailgate.message", string="Messages"), 
        'log_ids': fields.function(_get_log_ids, method=True, type='one2many', \
                         multi="log_ids", relation="mailgate.message", string="Logs"),
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
                'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'model_id' : model_ids and model_ids[0] or False,
                'res_id': case.id,
                'section_id': case.section_id.id,
                'message_id':message_id
            }

            if history:
                data['description'] = details or case.description
                data['email_to'] = email or \
                        (case.section_id and case.section_id.reply_to) or \
                        (case.user_id and case.user_id.address_id and \
                            case.user_id.address_id.email) or tools.config.get('email_from', False)
                data['email_from'] = email_from or \
                        (case.section_id and case.section_id.reply_to) or \
                        (case.user_id and case.user_id.address_id and \
                            case.user_id.address_id.email) or tools.config.get('email_from', False)
            res = obj.create(cr, uid, data, context)
        return True
    
    _history = __history
    history = __history
    
    def onchange_partner_id(self, cr, uid, ids, part, email=False):
        """This function returns value of partner address based on partner
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case IDs
        @param part: Partner's id
        @email: Partner's email ID 
        """
        if not part:
            return {'value': {'partner_address_id': False, 
                            'email_from': False, 
                            }}
        addr = self.pool.get('res.partner').address_get(cr, uid, [part], ['contact'])
        data = {'partner_address_id': addr['contact']}
        data.update(self.onchange_partner_address_id(cr, uid, ids, addr['contact'])['value'])
        return {'value': data}

    def onchange_partner_address_id(self, cr, uid, ids, add, email=False):
        """This function returns value of partner email based on Partner Address
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case IDs
        @param add: Id of Partner's address
        @email: Partner's email ID 
        """
        if not add:
            return {'value': {'email_from': False}}
        address = self.pool.get('res.partner.address').browse(cr, uid, add)
        return {'value': {'email_from': address.email}}
    
mailgate_thread()

class mailgate_message(osv.osv):
    '''
    Mailgateway Message
    '''
    _name = 'mailgate.message'
    _description = 'Mailgateway Message'
    
    _columns = {
        'name':fields.char('Message', size=64),
        'thread_id':fields.many2one('mailgate.thread', 'Thread'),
        'date': fields.datetime('Date'),
        'model_id': fields.many2one('ir.model', "Model"),
        'res_id': fields.integer('Resource ID'),
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
