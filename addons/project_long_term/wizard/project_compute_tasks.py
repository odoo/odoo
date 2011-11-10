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

from osv import osv, fields

class project_compute_tasks(osv.osv_memory):
    _name = 'project.compute.tasks'
    _description = 'Project Compute Tasks'
    _columns = {
        'project_id': fields.many2one('project.project', 'Project', required=True)
    }

    def compute_date(self, cr, uid, ids, context=None):
        """
        Schedule the tasks according to users and priority.
        """
        project_pool = self.pool.get('project.project')
        task_pool = self.pool.get('project.task')
        if context is None:
            context = {}
        context['compute_by'] = 'project'
        data = self.read(cr, uid, ids, [])[0]
        project_id = data['project_id'][0]
        project_pool.schedule_tasks(cr, uid, [project_id], context=context)
        return self._open_task_list(cr, uid, data, context=context)

    def _open_task_list(self, cr, uid, data, context=None):
        """
        Return the scheduled task list.
        """
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj._get_id(cr, uid, 'project_long_term', 'act_resouce_allocation')
        id = mod_obj.read(cr, uid, [result], ['res_id'])[0]['res_id']
        result = {}
        if not id:
            return result
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result['target'] = 'current'
        return result

project_compute_tasks()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
