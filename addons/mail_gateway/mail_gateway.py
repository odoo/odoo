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
            domain1 = domain + [('res_id', '=', case.id)]
            history_ids = history_obj.search(cr, uid, domain1, context=context)
            if history_ids:
                result[case.id] = {name: history_ids}
            else:
                result[case.id] = {name: []}
        return result

    _columns = {
        'name':fields.char('Name', size=64), 
        'active': fields.boolean('Active'), 
        'message_ids': fields.function(_get_log_ids, method=True, type='one2many', \
                         multi="message_ids", relation="mailgate.message", string="Messages"), 
        'log_ids': fields.function(_get_log_ids, method=True, type='one2many', \
                         multi="log_ids", relation="mailgate.message", string="Logs"),
    }
    
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
