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

    def get_user_related_details(self, cr, uid, user_id):
        res = {}
        emp_obj = self.pool.get('hr.employee')
        emp_id = emp_obj.search(cr, uid, [('user_id', '=', user_id)])
        if not emp_id:
            user_name = self.pool.get('res.users').read(cr, uid, [user_id], ['name'])[0]['name']
            raise osv.except_osv(_('Bad Configuration !'),
                 _('No employee defined for user "%s". You must create one.')% (user_name,))
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
            if not a:
                raise osv.except_osv(_('Bad Configuration !'),
                        _('No product and product category property account defined on the related employee.\nFill in the timesheet tab of the employee form.'))
        res['product_id'] = emp.product_id.id
        res['journal_id'] = emp.journal_id.id
        res['general_account_id'] = a
        res['product_uom_id'] = emp.product_id.uom_id.id
        return res
        
    def create(self, cr, uid, vals, *args, **kwargs):
        obj = self.pool.get('hr.analytic.timesheet')
        vals_line = {}
        obj_task = self.pool.get('project.task').browse(cr, uid, vals['task_id'])
        result = self.get_user_related_details(cr, uid, vals.get('user_id', uid))
        vals_line['name'] = '%s: %s' % (tools.ustr(obj_task.name), tools.ustr(vals['name']) or '/')
        vals_line['user_id'] = vals['user_id']
        vals_line['product_id'] = result['product_id']
        vals_line['date'] = vals['date'][:10]
        vals_line['unit_amount'] = vals['hours']
        acc_id = obj_task.project_id.category_id.id
        vals_line['account_id'] = acc_id
        res = obj.on_change_account_id(cr, uid, False, acc_id)
        if res.get('value'):
            vals_line.update(res['value'])
        vals_line['general_account_id'] = result['general_account_id']
        vals_line['journal_id'] = result['journal_id']
        vals_line['amount'] = 00.0
        vals_line['product_uom_id'] = result['product_uom_id']
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
                vals_line['name'] = '%s: %s' % (tools.ustr(task.task_id.name), tools.ustr(vals['name']) or '/')
            if 'user_id' in vals:
                vals_line['user_id'] = vals['user_id']
                result = self.get_user_related_details(cr, uid, vals['user_id'])
                vals_line['product_id'] = result['product_id']
                vals_line['general_account_id'] = result['general_account_id']
                vals_line['journal_id'] = result['journal_id']
                vals_line['product_uom_id'] = result['product_uom_id']
            if 'date' in vals:
                vals_line['date'] = vals['date'][:10]
            if 'hours' in vals:
                vals_line['unit_amount'] = vals['hours']
                vals_line['amount'] = (-1) * vals['hours'] * obj.browse(cr, uid, line_id).product_id.standard_price
            obj.write(cr, uid, [line_id], vals_line, {})

        return super(project_work,self).write(cr, uid, ids, vals, context)

    def unlink(self, cr, uid, ids, *args, **kwargs):
        pool_analytic_timesheet = self.pool.get('hr.analytic.timesheet')
        for work_id in ids:
            timesheet_id = self.read(cr, uid, work_id, ['hr_analytic_timesheet_id'])['hr_analytic_timesheet_id']
#            delete entry from timesheet too while deleting entry to task.
            list_avail_ids = pool_analytic_timesheet.search(cr, uid, [])
            if timesheet_id in list_avail_ids:
                obj = pool_analytic_timesheet.unlink(cr, uid, [timesheet_id], *args, **kwargs)

        return super(project_work,self).unlink(cr, uid, ids, *args, **kwargs)

    _columns={
        'hr_analytic_timesheet_id':fields.integer('Related Timeline Id')
    }

project_work()

class task(osv.osv):
    _inherit = "project.task"
    _description = "Tasks"

    def unlink(self, cr, uid, ids, *args, **kwargs):
        for task_obj in self.browse(cr, uid, ids, *args, **kwargs):
            if task_obj.work_ids:
                work_ids = [x.id for x in task_obj.work_ids]
                self.pool.get('project.task.work').unlink(cr, uid, work_ids, *args, **kwargs)
        
        return super(task,self).unlink(cr, uid, ids, *args, **kwargs)
    
    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        if (vals.has_key('project_id') and vals['project_id']) or (vals.has_key('name') and vals['name']):
            vals_line = {}
            hr_anlytic_timesheet = self.pool.get('hr.analytic.timesheet')
            task_obj_l = self.browse(cr, uid, ids, context)
            if (vals.has_key('project_id') and vals['project_id']):
                project_obj = self.pool.get('project.project').browse(cr, uid, vals['project_id'])
                acc_id = project_obj.category_id.id

            for task_obj in task_obj_l:
                if len(task_obj.work_ids):
                    for task_work in task_obj.work_ids:
                        line_id = task_work.hr_analytic_timesheet_id
                        if (vals.has_key('project_id') and vals['project_id']):
                            vals_line['account_id'] = acc_id
                        if (vals.has_key('name') and vals['name']):
                            vals_line['name'] = '%s: %s' % (tools.ustr(vals['name']), tools.ustr(task_work.name) or '/')
                        hr_anlytic_timesheet.write(cr, uid, [line_id], vals_line, {})
        return super(task,self).write(cr, uid, ids, vals, context)

task()

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

