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
from openerp.osv import fields, osv
from openerp.tools.translate import _

class project_task_reevaluate(osv.osv_memory):
    _name = 'project.task.reevaluate'

    def _get_remaining(self, cr, uid, context=None):
        if context is None:
            context = {}
        active_id = context.get('active_id', False)
        res = False
        if active_id:
            res = self.pool.get('project.task').browse(cr, uid, active_id, context=context).remaining_hours
        return res

    _columns = {
        'remaining_hours' : fields.float('Remaining Hours', digits=(16,2), help="Put here the remaining hours required to close the task."),
    }

    _defaults = {
        'remaining_hours': _get_remaining,
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(project_task_reevaluate, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu=submenu)
        users_pool = self.pool.get('res.users')
        time_mode = users_pool.browse(cr, uid, uid, context).company_id.project_time_mode_id
        time_mode_name = time_mode and time_mode.name or 'Hours'
        if time_mode_name in ['Hours','Hour']:
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
                res['fields'][field]['string'] = res['fields'][field]['string'].replace('Hours',time_mode_name)
        return res

    def compute_hours(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids, context=context)[0]
        task_id = context.get('active_id')
        if task_id:
            task_pool = self.pool.get('project.task')
            task_pool.write(cr, uid, task_id, {'remaining_hours': data.remaining_hours})
            if context.get('button_reactivate'):
                task_pool.do_reopen(cr, uid, [task_id], context=context)
        return {'type': 'ir.actions.act_window_close'}
project_task_reevaluate()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
