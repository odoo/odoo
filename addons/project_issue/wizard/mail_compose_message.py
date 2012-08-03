# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 OpenERP SA (<http://www.openerp.com>)
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from osv import osv

class mail_compose_message(osv.osv_memory):
    _inherit = 'mail.compose.message'
    
    def get_value(self, cr, uid, model, resource_id, context=None):
        result = super(mail_compose_message, self).get_value(cr, uid,  model, resource_id, context=context)
        if not result.get('reply_to') and model == 'project.issue' and resource_id:
            issue = self.pool.get('project.issue').browse(cr, uid, resource_id, context=context)
            if issue.project_id.reply_to: 
                result['reply_to'] = issue.project_id.reply_to
        return result
    
    def get_message_data(self, cr, uid, message_id, context=None):
        result = super(mail_compose_message, self).get_message_data(cr, uid,  message_id, context=context)
        if not result.get('reply_to') and message_id:
            msg = self.pool.get('mail.message').browse(cr, uid, message_id, context)
            if msg.model == 'project.issue':
                issue = self.pool.get('project.issue').browse(cr, uid, msg.res_id, context)
                if issue.project_id and issue.project_id.reply_to:
                    result['reply_to'] = issue.project_id.reply_to
        return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
