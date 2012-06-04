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
from osv import fields, osv
from tools.translate import _
import re
import time
import tools
from datetime import datetime
from dateutil.relativedelta import relativedelta

class project_scrum_project(osv.osv):
    _inherit = 'project.project'
    _columns = {
        'product_owner_id': fields.many2one('res.users', 'Product Owner', help="The person who is responsible for the product"),
        'sprint_size': fields.integer('Sprint Days', help="Number of days allocated for sprint"),
        'scrum': fields.integer('Is a Scrum Project'),
    }
    _defaults = {
        'product_owner_id': lambda self, cr, uid, context={}: uid,
        'sprint_size': 15,
        'scrum': 1
    }
project_scrum_project()

class project_scrum_sprint(osv.osv):
    _name = 'project.scrum.sprint'
    _description = 'Project Scrum Sprint'
    _order = 'date_start desc'
    _inherit = ['mail.thread']
    def _compute(self, cr, uid, ids, fields, arg, context=None):
        res = {}.fromkeys(ids, 0.0)
        progress = {}
        if not ids:
            return res
        if context is None:
            context = {}
        for sprint in self.browse(cr, uid, ids, context=context):
            tot = 0.0
            prog = 0.0
            effective = 0.0
            progress = 0.0
            for bl in sprint.backlog_ids:
                tot += bl.expected_hours
                effective += bl.effective_hours
                prog += bl.expected_hours * bl.progress / 100.0
            if tot>0:
                progress = round(prog/tot*100)
            res[sprint.id] = {
                'progress' : progress,
                'expected_hours' : tot,
                'effective_hours': effective,
            }
        return res

    def button_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'cancel'}, context=context)
        self.cancel_send_note(cr, uid, ids, context=None)
        return True

    def button_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft'}, context=context)
        self.draft_send_note(cr, uid, ids, context=None)
        return True

    def button_open(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'open'}, context=context)
        self.open_send_note(cr, uid, ids, context=None)
        return True

    def button_close(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'done'}, context=context)
        self.close_send_note(cr, uid, ids, context=None)
        return True

    def button_pending(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'pending'}, context=context)
        self.pending_send_note(cr, uid, ids, context=None)
        return True

    _columns = {
        'name' : fields.char('Sprint Name', required=True, size=64),
        'date_start': fields.date('Starting Date', required=True),
        'date_stop': fields.date('Ending Date', required=True),
        'project_id': fields.many2one('project.project', 'Project', required=True, domain=[('scrum','=',1)], help="If you have [?] in the project name, it means there are no analytic account linked to this project."),
        'product_owner_id': fields.many2one('res.users', 'Product Owner', required=True,help="The person who is responsible for the product"),
        'scrum_master_id': fields.many2one('res.users', 'Scrum Master', required=True,help="The person who is maintains the processes for the product"),
        'meeting_ids': fields.one2many('project.scrum.meeting', 'sprint_id', 'Daily Scrum'),
        'review': fields.text('Sprint Review'),
        'retrospective': fields.text('Sprint Retrospective'),
        'backlog_ids': fields.one2many('project.scrum.product.backlog', 'sprint_id', 'Sprint Backlog'),
        'progress': fields.function(_compute, group_operator="avg", type='float', multi="progress", string='Progress (0-100)', help="Computed as: Time Spent / Total Time."),
        'effective_hours': fields.function(_compute, multi="effective_hours", string='Effective hours', help="Computed using the sum of the task work done."),
        'expected_hours': fields.function(_compute, multi="expected_hours", string='Planned Hours', help='Estimated time to do the task.'),
        'state': fields.selection([('draft','Draft'),('cancel','Cancelled'),('open','Open'),('pending','Pending'),('done','Done')], 'Status', required=True),
    }
    _defaults = {
        'state': 'draft',
        'date_start' : lambda *a: time.strftime('%Y-%m-%d'),
    }

    def copy(self, cr, uid, id, default=None, context=None):
        """Overrides orm copy method
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case’s IDs
        @param context: A standard dictionary for contextual values
        """
        if default is None:
            default = {}
        default.update({'backlog_ids': [], 'meeting_ids': []})
        return super(project_scrum_sprint, self).copy(cr, uid, id, default=default, context=context)

    def onchange_project_id(self, cr, uid, ids, project_id=False):
        v = {}
        if project_id:
            proj = self.pool.get('project.project').browse(cr, uid, [project_id])[0]
            v['product_owner_id']= proj.product_owner_id and proj.product_owner_id.id or False
            v['scrum_master_id']= proj.user_id and proj.user_id.id or False
            v['date_stop'] = (datetime.now() + relativedelta(days=int(proj.sprint_size or 14))).strftime('%Y-%m-%d')
        return {'value':v}

    # ----------------------------------------
    # OpenChatter methods and notifications
    # ----------------------------------------

    def create(self, cr, uid, vals, context=None):
        obj_id = super(project_scrum_sprint, self).create(cr, uid, vals, context)
        self.create_send_note(cr, uid, [obj_id], context=context)
        return obj_id

    def draft_send_note(self, cr, uid, ids, context=None):
        self.message_append_note(cr, uid, ids, body=_("Sprint has been set to <b>draft</b>."), context=context)

    def create_send_note(self, cr, uid, ids, context=None):
        self.message_append_note(cr, uid, ids, body=_("Sprint has been <b>created</b>."), context=context)

    def open_send_note(self, cr, uid, ids, context=None):
        self.message_append_note(cr, uid, ids, body=_("Sprint has been <b>opened</b>."), context=context)

    def pending_send_note(self, cr, uid, ids, context=None):
        self.message_append_note(cr, uid, ids, body=_("Sprint has been set to <b>pending</b>."), context=context)

    def cancel_send_note(self, cr, uid, ids, context=None):
        self.message_append_note(cr, uid, ids, body=_("Sprint has been <b>cancelled</b>."), context=context)

    def close_send_note(self, cr, uid, ids, context=None):
        self.message_append_note(cr, uid, ids, body=_("Sprint has been <b>closed</b>."), context=context)

project_scrum_sprint()

class project_scrum_product_backlog(osv.osv):
    _name = 'project.scrum.product.backlog'
    _description = 'Product Backlog'

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args=[]
        if name:
            match = re.match('^S\(([0-9]+)\)$', name)
            if match:
                ids = self.search(cr, uid, [('sprint_id','=', int(match.group(1)))], limit=limit, context=context)
                return self.name_get(cr, uid, ids, context=context)
        return super(project_scrum_product_backlog, self).name_search(cr, uid, name, args, operator,context, limit=limit)

    def _compute(self, cr, uid, ids, fields, arg, context=None):
        res = {}.fromkeys(ids, 0.0)
        progress = {}
        if not ids:
            return res
        for backlog in self.browse(cr, uid, ids, context=context):
            tot = 0.0
            prog = 0.0
            effective = 0.0
            task_hours = 0.0
            progress = 0.0
            for task in backlog.tasks_id:
                task_hours += task.total_hours
                effective += task.effective_hours
                tot += task.planned_hours
                prog += task.planned_hours * task.progress / 100.0
            if tot>0:
                progress = round(prog/tot*100)
            res[backlog.id] = {
                'progress' : progress,
                'effective_hours': effective,
                'task_hours' : task_hours
            }
        return res

    def button_cancel(self, cr, uid, ids, context=None):
        obj_project_task = self.pool.get('project.task')
        self.write(cr, uid, ids, {'state':'cancel'}, context=context)
        for backlog in self.browse(cr, uid, ids, context=context):
            obj_project_task.write(cr, uid, [i.id for i in backlog.tasks_id], {'state': 'cancelled'})
        return True

    def button_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft'}, context=context)
        return True

    def button_open(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'open'}, context=context)
        return True

    def button_close(self, cr, uid, ids, context=None):
        obj_project_task = self.pool.get('project.task')
        self.write(cr, uid, ids, {'state':'done'}, context=context)
        for backlog in self.browse(cr, uid, ids, context=context):
            obj_project_task.write(cr, uid, [i.id for i in backlog.tasks_id], {'state': 'done'})
        return True

    def button_pending(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'pending'}, context=context)
        return True

    def button_postpone(self, cr, uid, ids, context=None):
        for product in self.browse(cr, uid, ids, context=context):
            tasks_id = []
            for task in product.tasks_id:
                if task.state != 'done':
                    tasks_id.append(task.id)

            clone_id = self.copy(cr, uid, product.id, {
                'name': 'PARTIAL:'+ product.name ,
                'sprint_id':False,
                'tasks_id':[(6, 0, tasks_id)],
                                })
        self.write(cr, uid, ids, {'state':'cancel'}, context=context)
        return True

    _columns = {
        'name' : fields.char('Feature', size=64, required=True),
        'note' : fields.text('Note'),
        'active' : fields.boolean('Active', help="If Active field is set to true, it will allow you to hide the product backlog without removing it."),
        'project_id': fields.many2one('project.project', 'Project', required=True, domain=[('scrum','=',1)]),
        'user_id': fields.many2one('res.users', 'Author'),
        'sprint_id': fields.many2one('project.scrum.sprint', 'Sprint'),
        'sequence' : fields.integer('Sequence', help="Gives the sequence order when displaying a list of product backlog."),
        'tasks_id': fields.one2many('project.task', 'product_backlog_id', 'Tasks Details'),
        'state': fields.selection([('draft','Draft'),('cancel','Cancelled'),('open','Open'),('pending','Pending'),('done','Done')], 'Status', required=True),
        'progress': fields.function(_compute, multi="progress", group_operator="avg", type='float', string='Progress', help="Computed as: Time Spent / Total Time."),
        'effective_hours': fields.function(_compute, multi="effective_hours", string='Spent Hours', help="Computed using the sum of the time spent on every related tasks", store=True),
        'expected_hours': fields.float('Planned Hours', help='Estimated total time to do the Backlog'),
        'create_date': fields.datetime("Creation Date", readonly=True),
        'task_hours': fields.function(_compute, multi="task_hours", string='Task Hours', help='Estimated time of the total hours of the tasks')
    }
    _defaults = {
        'state': 'draft',
        'active':  1,
        'user_id': lambda self, cr, uid, context: uid,
    }
    _order = "sequence"
project_scrum_product_backlog()

class project_scrum_task(osv.osv):
    _name = 'project.task'
    _inherit = 'project.task'

    def _get_task(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('project.scrum.product.backlog').browse(cr, uid, ids, context=context):
            for task in line.tasks_id:
                result[task.id] = True
        return result.keys()

    _columns = {
        'product_backlog_id': fields.many2one('project.scrum.product.backlog', 'Product Backlog',help="Related product backlog that contains this task. Used in SCRUM methodology"),
        'sprint_id': fields.related('product_backlog_id','sprint_id', type='many2one', relation='project.scrum.sprint', string='Sprint',
            store={
                'project.task': (lambda self, cr, uid, ids, c={}: ids, ['product_backlog_id'], 10),
                'project.scrum.product.backlog': (_get_task, ['sprint_id'], 10)
            }),
    }

project_scrum_task()

class project_scrum_meeting(osv.osv):
    _name = 'project.scrum.meeting'
    _description = 'Scrum Meeting'
    _order = 'date desc'
    _columns = {
        'name' : fields.char('Meeting Name', size=64),
        'date': fields.date('Meeting Date', required=True),
        'sprint_id': fields.many2one('project.scrum.sprint', 'Sprint', required=True),
        'project_id': fields.many2one('project.project', 'Project'),
        'question_yesterday': fields.text('Tasks since yesterday'),
        'question_today': fields.text('Tasks for today'),
        'question_blocks': fields.text('Blocks encountered'),
        'question_backlog': fields.text('Backlog Accurate'),
        'task_ids': fields.many2many('project.task', 'meeting_task_rel', 'metting_id', 'task_id', 'Tasks'),
        'user_id': fields.related('sprint_id', 'scrum_master_id', type='many2one', relation='res.users', string='Scrum Master', readonly=True),
    }
    #
    # TODO: Find the right sprint thanks to users and date
    #
    _defaults = {
        'date' : lambda *a: time.strftime('%Y-%m-%d'),
    }

project_scrum_meeting()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
