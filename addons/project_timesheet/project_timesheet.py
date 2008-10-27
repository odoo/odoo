# -*- encoding: utf-8 -*-
from osv import fields, osv
import time
import datetime
import pooler


class project_work(osv.osv):
    _inherit = "project.task.work"
    _description = "Task Work"
    def create(self, cr, uid, vals, *args, **kwargs):

        obj = self.pool.get('hr.analytic.timesheet')
        vals_line={}
        obj_task = self.pool.get('project.task').browse(cr, uid, vals['task_id'])

        vals_line['name']=obj_task.name + ': ' + vals['name']
        vals_line['user_id']=vals['user_id']
        vals_line['date']=vals['date'][:10]
        vals_line['unit_amount']=vals['hours']
        vals_line['account_id']=obj_task.project_id.category_id.id
        vals_line['amount']=00.0
        timeline_id=obj.create(cr, uid,vals_line,{})

        vals_line['amount']=(-1) * vals['hours']*obj.browse(cr,uid,timeline_id).product_id.standard_price
        obj.write(cr, uid,[timeline_id],vals_line,{})
        vals['hr_analytic_timesheet_id']=timeline_id
        return super(project_work,self).create(cr, uid, vals, *args, **kwargs)

    def write(self, cr, uid, ids,vals,context={}):
        vals_line={}

        task=self.pool.get('project.task.work').browse(cr,uid,ids)[0]
        line_id=task.hr_analytic_timesheet_id
        # in case,if a record is deleted from timesheet,but we change it from tasks!
        list_avail_ids=self.pool.get('hr.analytic.timesheet').search(cr,uid,[])
        if line_id in list_avail_ids:
            obj = self.pool.get('hr.analytic.timesheet')
            if 'name' in vals:
                vals_line['name']=task.name+': '+vals['name']
            if 'user_id' in vals:
                vals_line['user_id']=vals['user_id']
            if 'date' in vals:
                vals_line['date']=vals['date'][:10]
            if 'hours' in vals:
                vals_line['unit_amount']=vals['hours']
                vals_line['amount']=(-1) * vals['hours'] * obj.browse(cr,uid,line_id).product_id.standard_price
            obj.write(cr, uid,[line_id],vals_line,{})

        return super(project_work,self).write(cr, uid, ids,vals,context)

    def unlink(self, cr, uid, ids, *args, **kwargs):
        timesheet_id=self.pool.get('project.task.work').browse(cr,uid,ids)[0].hr_analytic_timesheet_id
        # delete entry from timesheet too while deleting entry to task.
        list_avail_ids=self.pool.get('hr.analytic.timesheet').search(cr,uid,[])
        if timesheet_id in list_avail_ids:
           obj = self.pool.get('hr.analytic.timesheet').unlink(cr,uid,[timesheet_id],*args)

        return super(project_work,self).unlink(cr, uid, ids,*args, **kwargs)

    _columns={
        'hr_analytic_timesheet_id':fields.integer('Related Timeline Id')
    }


project_work()

class project_project(osv.osv):
    _inherit = "project.project"
    def name_get(self, cr, user, ids, context=None):
        result = []
        for project in self.browse(cr, user, ids, context):
            if project.category_id and project.category_id.code:
                result.append((project.id, '['+(project.category_id.code or '')+'] '+project.name))
            else:
                result.append((project.id, '[?] '+project.name))
        return result
project_project()

