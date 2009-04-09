# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from osv import fields, osv
import time
import datetime
import pooler
import tools
from tools.translate import _


class project_work(osv.osv):
    _inherit = "project.task.work"
    _description = "Task Work"
    def create(self, cr, uid, vals, *args, **kwargs):

        obj = self.pool.get('hr.analytic.timesheet')
        vals_line = {}
        obj_task = self.pool.get('project.task').browse(cr, uid, vals['task_id'])

        emp_obj = self.pool.get('hr.employee')
        emp_id = emp_obj.search(cr, uid, [('user_id', '=', vals.get('user_id', uid))])

        if not emp_id:
            raise osv.except_osv(_('Bad Configuration !'),
                 _('No employee defined for this user. You must create one.'))
        emp = self.pool.get('hr.employee').browse(cr, uid, emp_id[0])
        if not emp.product_id:
            raise osv.except_osv(_('Bad Configuration !'),
                 _('No product defined on the related employee.\nFill in the timesheet tab of the employee form.'))

        if not emp.journal_id:
            raise osv.except_osv(_('Bad Configuration !'),
                 _('No journal defined on the related employee.\nFill in the timesheet tab of the employee form.'))

        a =  emp.product_id.product_tmpl_id.property_account_expense.id
        if not a:
            a = emp.product_id.categ_id.property_account_expense_categ.id

        vals_line['name'] = '%s: %s' % (tools.ustr(obj_task.name), tools.ustr(vals['name']) or '/')
        vals_line['user_id'] = vals['user_id']
        vals_line['date'] = vals['date'][:10]
        vals_line['unit_amount'] = vals['hours']
        vals_line['account_id'] = obj_task.project_id.category_id.id
        res = obj.on_change_account_id(cr, uid, False, obj_task.project_id.category_id.id)
        print 'Got', res
        if res.get('value'):
            vals_line.update(res['value'])
        vals_line['general_account_id'] = a
        vals_line['journal_id'] = emp.journal_id.id
        vals_line['amount'] = 00.0
        timeline_id = obj.create(cr, uid, vals_line, {})

        vals_line['amount'] = (-1) * vals['hours'] * obj.browse(cr, uid, timeline_id).product_id.standard_price
        obj.write(cr, uid,[timeline_id], vals_line, {})
        vals['hr_analytic_timesheet_id'] = timeline_id
        return super(project_work,self).create(cr, uid, vals, *args, **kwargs)

    def write(self, cr, uid, ids, vals, context=None):
        vals_line = {}

        task = self.pool.get('project.task.work').browse(cr, uid, ids)[0]
        line_id = task.hr_analytic_timesheet_id
        # in case,if a record is deleted from timesheet,but we change it from tasks!
        list_avail_ids = self.pool.get('hr.analytic.timesheet').search(cr, uid, [])
        if line_id in list_avail_ids:
            obj = self.pool.get('hr.analytic.timesheet')
            if 'name' in vals:
                vals_line['name'] = '%s: %s' % (tools.ustr(task.name), tools.ustr(vals['name']) or '/')
            if 'user_id' in vals:
                vals_line['user_id'] = vals['user_id']
            if 'date' in vals:
                vals_line['date'] = vals['date'][:10]
            if 'hours' in vals:
                vals_line['unit_amount'] = vals['hours']
                vals_line['amount'] = (-1) * vals['hours'] * obj.browse(cr, uid, line_id).product_id.standard_price
            obj.write(cr, uid, [line_id], vals_line, {})

        return super(project_work,self).write(cr, uid, ids, vals, context)

    def unlink(self, cr, uid, ids, *args, **kwargs):
        timesheet_id = self.pool.get('project.task.work').browse(cr, uid, ids)[0].hr_analytic_timesheet_id
#         delete entry from timesheet too while deleting entry to task.
        list_avail_ids = self.pool.get('hr.analytic.timesheet').search(cr, uid, [])
        if timesheet_id in list_avail_ids:
            obj = self.pool.get('hr.analytic.timesheet').unlink(cr, uid, [timesheet_id], *args, **kwargs)

        return super(project_work,self).unlink(cr, uid, ids, *args, **kwargs)

    _columns={
        'hr_analytic_timesheet_id':fields.integer('Related Timeline Id')
    }


project_work()

class project_project(osv.osv):
    _inherit = "project.project"
    def name_get(self, cr, user, ids, context=None):
        result = []
        for project in self.browse(cr, user, ids, context):
            name = "[%s] %s" % (project.category_id and project.category_id.code or '?', project.name)
            result.append((project.id, name))
        return result
project_project()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

