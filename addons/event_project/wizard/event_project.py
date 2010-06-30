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

#
# Order Point Method:
#   - Order if the virtual stock of today is bellow the min of the defined order point
#

from osv import fields, osv
from tools.translate import _
import time
 
class event_project(osv.osv_memory):
    """
    Event Project
    """
    _name = "event.project"
    _description = "Event Project"

    _columns = {
             'project_id': fields.many2one('project.project', 'Project', domain = [('active', '<>', False), ('state', '=', 'template')], required =True)             
     }
    
    def create_duplicate(self, cr, uid, ids, context):
        event_obj=self.pool.get('event.event')
        project_obj = self.pool.get('project.project')
        
        for current in self.browse(cr, uid, ids): 
            duplicate_project_id= project_obj.copy(cr, uid, current.project_id.id, {'active': True})
            project_obj.write(cr, uid, [duplicate_project_id], {'name': "copy of " + project_obj.browse(cr, uid, duplicate_project_id, context).name , 'date_start':time.strftime('%Y-%m-%d'), 'date': event_obj.browse(cr, uid, context.get('active_ids', []))[0].date_begin[0:10] })
            event_obj.write(cr, uid, context.get('active_ids', []), {'project_id': duplicate_project_id })
            
        return {}
   
event_project()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
