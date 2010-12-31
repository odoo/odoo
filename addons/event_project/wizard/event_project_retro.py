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
from datetime import date, datetime

class event_project(osv.osv_memory):
    """
    Event Project
    """
    _name = "event.project"
    _description = "Event Project"

    _columns = {
        'project_id': fields.many2one('project.project', 'Template of Project',
                    domain = [('active', '<>', False), ('state', '=', 'template')],
                    required =True,
                    help="This is Template Project. Project of event is a duplicate of this Template. After click on  'Create Retro-planning', New Project will be duplicated from this template project."),
        'date_start': fields.date('Date Start'),
        'date': fields.date('Date End'),
     }
    
    def _get_date_start(self, cr, uid, context=None):
        event_obj = self.pool.get('event.event')
        if context is None:
            context = {}
        event = event_obj.browse(cr, uid, context.get('active_id', False))
        res = datetime.strptime(event.date_begin, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
        return res
    
    def _get_date_end(self, cr, uid, context=None):
        event_obj = self.pool.get('event.event')
        if context is None:
            context = {}
        event = event_obj.browse(cr, uid, context.get('active_id', False), context=context)
        res = datetime.strptime(event.date_end, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
        return res
        
    _defaults = {
        'date_start': _get_date_start,
        'date': _get_date_end
    }
    
    def create_duplicate(self, cr, uid, ids, context=None):
        event_obj = self.pool.get('event.event')
        project_obj = self.pool.get('project.project')
        event = event_obj.browse(cr, uid, context.get('active_id', False), context=context)
        for current in self.browse(cr, uid, ids, context=context):
            duplicate_project_id = project_obj.copy(cr, uid, current.project_id.id, {
                    'active': True,
                    'date_start':current.date_start,
                    'date': current.date,
                    })
            event_obj.write(cr, uid, [event.id], {'project_id': duplicate_project_id })

        return {}

event_project()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: