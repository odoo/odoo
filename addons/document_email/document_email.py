#!/usr/bin/env python
#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    fp@tinyerp.com 
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import os
import binascii

import netsvc

from osv import osv
from osv import fields
from tools.translate import _

logger = netsvc.Logger()

class email_to_document(osv.osv):

    _name = 'document.email'
    _description = "Emails to Documents Gateway"
    
    _columns = {
        'name':fields.char('Name', size=64, required=True, readonly=False),
        'user_id':fields.many2one('res.users', 'User', required=True),
        'directory_id':fields.many2one('document.directory', 'Directory', required=True),
        'accept_files':fields.char('File Extension', size=1024, required=True),
        'note': fields.text('Description'),
        'server_id': fields.many2one('email.server',"Mail Server", select=True),
    }
    
    _defaults = {
        'accept_files': lambda *a: "['.txt', '.ppt', '.doc', '.xls', '.pdf', '.jpg', '.png']",
        'user_id': lambda self, cr, uid, ctx: uid,
    }
    
    _sql_constraints = [
        ('name_uniq', 'unique (user_id, server_id)', 'You can not configure one serve for multiple directory !'),
    ]
    
    def message_new(self, cr, uid, msg, context):
        """
        Automatically calls when new email message arrives
        
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks
        """
        server_id = context.get('server_id', False)
        file_pool = self.pool.get('ir.attachment')
        if server_id:
            ids = self.search(cr, uid, [('server_id', '=', server_id)])
            dr = self.browse(cr, uid, ids[0])
            id = dr.directory_id.id
            
            partner = self.pool.get('email.server.tools').get_partner(cr, uid, msg.get('from'), context)
            ext = eval(dr.accept_files, {})
            attachents = msg.get('attachments', [])

            for attactment in attachents:
                file_ext = os.path.splitext(attactment)
                if file_ext[1] not in ext:
                    logger.notifyChannel('document', netsvc.LOG_WARNING, 'file type %s is not allows to process for directory %s' % (file_ext[1], dr.directory_id.name))
                    continue
                    
                data_attach = {
                    'name': attactment,
                    'datas':binascii.b2a_base64(str(attachents.get(attactment))),
                    'datas_fname': attactment,
                    'description': msg.get('body', 'Mail attachment'),
                    'parent_id': id,
                    'partner_id':partner.get('partner_id', False),
                    'res_model': 'document.directory',
                    'res_id': id,
                }
                file_pool.create(cr, uid, data_attach)

            return id
        return 0
    
    def message_update(self, cr, uid, ids, vals={}, msg="", default_act=None, context={}):
        """ 
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of update mail’s IDs 
        """
        logger.notifyChannel('document', netsvc.LOG_WARNING, 'method not implement to keep multipe version of file')
        return True
email_to_document()

class document_directory(osv.osv):
    _inherit = 'document.directory'
    
    _columns = {
        'email_ids':fields.one2many('document.email', 'directory_id', 'Document to Email', required=False),
    }
document_directory()
