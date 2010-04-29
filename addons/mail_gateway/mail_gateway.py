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

from osv import osv
from osv import fields


from osv import osv
from osv import fields


class mailgate_thread(osv.osv):
    '''
    Mailgateway Thread
    '''
    _name = 'mailgate.thread'
    _description = 'Mailgateway Thread'
    
    _columns = {
        'name':fields.char('Name', size=64),
        'message_ids':fields.one2many('mailgate.message', 'thread_id', 'Message'),
    }

mailgate_thread()

class mailgate_message(osv.osv):
    '''
    Mailgateway Message
    '''
    _name = 'mailgate.message'
    _description = 'Mailgateway Message'
    
    _columns = {
        'name':fields.char('Message', size=64, required=True),
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
        'attachment_ids': fields.many2many('ir.attachment', 'message_attachment_rel', 'message_id', 'attachment_id', 'Attachments'),
    }

mailgate_message()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
