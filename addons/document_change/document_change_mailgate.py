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
##############################################################################

import time
import re
import os

import mx.DateTime
import base64

from tools.translate import _

import tools
from osv import fields,osv,orm
from osv.orm import except_orm

class document_file(osv.osv):    
    _inherit = "ir.attachment"

    _columns = {
        'email_notification_ids':fields.one2many('document.email.notes','document_id','Phase', readonly=True),       
    }    

    def msg_new(self, cr, uid, msg):
        raise Exception(_('Sorry, Not Allowed to create document'))                
        return False
    
    def msg_update(self, cr, uid, id, msg, data={}, default_act='pending'):         
        mailgate_obj = self.pool.get('mail.gateway')
        msg_actions, body_data = mailgate_obj.msg_act_get(msg) 
        email_notify_data = {
            'name' : msg['Subject'],
            'description' : body_data,
            'email' : msg['From'],            
        }          
        data.update({            
            'email_notification_ids': [(0, 0, email_notify_data)],
        })        
        res = self.write(cr, uid, [id], data)
        return res

    def emails_get(self, cr, uid, ids, context={}):                
        res = []
        if isinstance(ids, (str, int, long)):
            select = [ids]
        else:
            select = ids
        for document in self.browse(cr, uid, select):
            user_email = (document.user_id and document.user_id.address_id and document.user_id.address_id.email) or False
            res += [(user_email, False, False, False)]
        if isinstance(ids, (str, int, long)):
            return len(res) and res[0] or False
        return res

    def msg_send(self, cr, uid, id, *args, **argv):
        return True 

document_file()


class document_email_notes(osv.osv):
    _name = "document.email.notes"
    _description = "EMail Conversation Detail"

    def _note_get(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for hist in self.browse(cursor, user, ids, context or {}):
            res[hist.id] = (hist.email or '/') + ' (' + str(hist.create_date) + ')\n'
            res[hist.id] += (hist.description or '')
        return res

    _columns = {
        'name': fields.char("Name", size=64, required=True, select=True),
        'description': fields.text('Description'),
        'note': fields.function(_note_get, method=True, string="Description", type="text"),
        'email': fields.char('Email', size=84),  
        'create_date': fields.datetime('Created Date'),  
        'action': fields.char('Action', size=64),
        'document_id': fields.many2one('ir.attachment','Document', required=True),    
    }
document_email_notes()
