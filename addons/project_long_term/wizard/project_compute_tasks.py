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

from openerp.osv import fields, osv


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
        if context is None:
            context = {}
        context['compute_by'] = 'project'

        for task in self.browse(cr, uid, ids, context=context):
            task.project_id.schedule_tasks()

        return self._open_task_list(cr, uid, context=context)

    def _open_task_list(self, cr, uid, context=None):
        """
        Return the scheduled task list.
        """
        if context is None:
            context = {}

        try:
            proxy = self.pool.get('ir.model.data')
            _, res_id = proxy.get_object_reference(cr, uid,
                                                   'project_long_term',
                                                   'act_resouce_allocation')
            proxy = self.pool.get('ir.actions.act_window')
            action = proxy.read(cr, uid, [res_id], context=context)[0]
            action['target'] = 'current'
            return action
        except ValueError:
            # this record does not exist into the model.data object
            # we return an empty dictionary
            return {}



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
