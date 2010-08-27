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

from osv import fields, osv
from tools.translate import _
from tools import email_send as email

class project_task_review(osv.osv_memory):
    """
    Review Task
    """
    _name = "project.task.review"
    _description = "Project Task  Review"
    _columns = {
        'user_id': fields.many2one('res.users', 'Review by'),
        'description': fields.text('Description'),
    }
    def review(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids[0], [])
        notes = data['description'] or ''
        task_id=context.get('active_id',False)
        task_obj = self.pool.get('project.task')
        if data['user_id']:
            user_name = self.pool.get('res.users').browse(cr, uid, data['user_id']).name or ''
        description = _("Review By ") + user_name + _(" At ") + time.strftime('%Y-%m-%d %H:%M:%S')
        description += "\n" + "=======================" + "\n"  + notes 
        if task_id:    
            task = task_obj.browse(cr, uid,task_id)            
            description = task.description and task.description  + "\n\n" + description
            task_obj.write(cr, uid, [task_id], {'description': description})
        return {}
  
project_task_review()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
