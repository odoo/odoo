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

from osv import fields, osv
import netsvc

class messages(osv.osv):
    """
    Message from one user to another within a project
    """
    _name = 'project.messages'
    logger = netsvc.Logger()

    _columns = {
        'create_date': fields.datetime('Creation Date', readonly=True),
        'from_id': fields.many2one('res.users', 'From', required=True, ondelete="CASCADE"),
        'to_id': fields.many2one('res.users', 'To', ondelete="CASCADE", help="Keep this empty to broadcast the message."),
        'project_id': fields.many2one('project.project', 'Project',
                                     required=True, ondelete="CASCADE"),
        'message': fields.text('Message', required=True),
    }
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        # return messages by current user, for current user or for all users
        # return all messages if current user is administrator  
        if uid != 1:
            args.extend(['|',('from_id', 'in', [uid,]),('to_id', 'in', [uid, False])])
        return super(messages, self).search(cr, uid, args, offset, limit,
                order, context=context, count=count)
        
    _defaults = {
        'from_id': lambda self, cr, uid, context: uid,
    }

messages()

class project_with_message(osv.osv):
    _inherit = 'project.project'
    
    _columns = {
        'message_ids':fields.one2many('project.messages', 'project_id', 'Messages'),
    }
project_with_message()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
