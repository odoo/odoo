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

from lxml import etree

import tools
from tools.translate import _
from osv import fields, osv

class project_task_delegate(osv.osv_memory):
    _name = 'project.task.delegate'
    _description = 'Task Delegate'

    _columns = {
        'name': fields.char('Delegated Title', size=64, required=True, help="New title of the task delegated to the user"),
        'prefix': fields.char('Your Task Title', size=64, required=True, help="Title for your validation task"),
        'user_id': fields.many2one('res.users', 'Assign To', required=True, help="User you want to delegate this task to"),
        'new_task_description': fields.text('New Task Description', help="Reinclude the description of the task in the task of the user"),
        'planned_hours': fields.float('Planned Hours',  help="Estimated time to close this task by the delegated user"),
        'planned_hours_me': fields.float('Hours to Validate', required=True, help="Estimated time for you to validate the work done by the user to whom you delegate this task"),
        'state': fields.selection([('pending','Pending'), ('done','Done'), ], 'Validation State', required=True, help="New state of your own task. Pending will be reopened automatically when the delegated task is closed")
    }

    def default_get(self, cr, uid, fields, context=None):
        """
        This function gets default values
        """
        res = super(project_task_delegate, self).default_get(cr, uid, fields, context=context)
        if context is None:
            context = {}
        record_id = context and context.get('active_id', False) or False
        task_pool = self.pool.get('project.task')
        task = task_pool.browse(cr, uid, record_id, context=context)
        task_name =tools.ustr(task.name)

        if 'name' in fields:
            if task_name.startswith(_('CHECK: ')):
                newname = tools.ustr(task_name).replace(_('CHECK: '), '')
            else:
                newname = tools.ustr(task_name or '')
            res.update({'name': newname})
        if 'planned_hours' in fields:
            res.update({'planned_hours': task.remaining_hours or 0.0})
        if 'prefix' in fields:
            if task_name.startswith(_('CHECK: ')):
                newname = tools.ustr(task_name).replace(_('CHECK: '), '')
            else:
                newname = tools.ustr(task_name or '')
            prefix = _('CHECK: %s') % newname
            res.update({'prefix': prefix})
        if 'new_task_description' in fields:
            res.update({'new_task_description': task.description})
        return res


    _defaults = {
       'planned_hours_me': 1.0,
       'state': 'pending',
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(project_task_delegate, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu=submenu)
        users_pool = self.pool.get('res.users')
        obj_tm = users_pool.browse(cr, uid, uid, context=context).company_id.project_time_mode_id
        tm = obj_tm and obj_tm.name or 'Hours'
        if tm in ['Hours','Hour']:
            return res

        eview = etree.fromstring(res['arch'])
        def _check_rec(eview):
            if eview.attrib.get('widget','') == 'float_time':
                eview.set('widget','float')
            for child in eview:
                _check_rec(child)
            return True

        _check_rec(eview)
        res['arch'] = etree.tostring(eview)
        for field in res['fields']:
            if 'Hours' in res['fields'][field]['string']:
                res['fields'][field]['string'] = res['fields'][field]['string'].replace('Hours',tm)
        return res

    def delegate(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        task_id = context.get('active_id', False)
        task_pool = self.pool.get('project.task')
        delegate_data = self.read(cr, uid, ids, context=context)[0]
        delegate_data['user_id'] = delegate_data['user_id'][0]
        delegate_data['name'] = tools.ustr(delegate_data['name'])
        task_pool.do_delegate(cr, uid, task_id, delegate_data, context=context)
        return {}

project_task_delegate()
