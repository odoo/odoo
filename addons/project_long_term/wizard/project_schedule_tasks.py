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

class project_schedule_task(osv.osv_memory):
    _name = "project.schedule.tasks"
    _description = 'project.schedule.tasks'
    _columns = {
        'msg': fields.char('Message', size=64)
    }
    _defaults = {
         'msg': 'Task Scheduling Completed Successfully'
    }

    def default_get(self, cr, uid, fields_list, context=None):
        res = super(project_schedule_task, self).default_get(cr, uid, fields_list, context)
        self.compute_date(cr, uid, context=context)
        return res
    
    def compute_date(self, cr, uid, context=None):
        """
        Schedule the tasks according to resource available and priority.
        """
        phase_pool = self.pool.get('project.phase')
        if context is None:
            context = {}
        if not 'active_id' in context:
            return {'type': 'ir.actions.act_window_close'}
        return phase_pool.schedule_tasks(cr, uid, [context['active_id']], context=context)
project_schedule_task()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
