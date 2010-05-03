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

import time
import netsvc
from osv import fields, osv, orm

from mx import DateTime
import re

class scrum_project(osv.osv):
    _inherit = 'project.project'
    _columns = {
        'product_owner_id': fields.many2one('res.users', 'Product Owner'),
        'sprint_size': fields.integer('Sprint Days'),
        'scrum': fields.integer('Is a Scrum Project'),
    }
    _defaults = {
        'product_owner_id': lambda self,cr,uid,context={}: uid,
        'sprint_size': lambda *a: 15,
        'scrum': lambda *a: 1
    }
scrum_project()

class scrum_sprint(osv.osv):
    _name = 'scrum.sprint'
    _description = 'Scrum Sprint'
    def _calc_progress(self, cr, uid, ids, name, args, context):
        res = {}
        for sprint in self.browse(cr, uid, ids):
            tot = 0.0
            prog = 0.0
            for bl in sprint.backlog_ids:
                tot += bl.planned_hours
                prog += bl.planned_hours * bl.progress / 100.0
            res.setdefault(sprint.id, 0.0)
            if tot>0:
                res[sprint.id] = round(prog/tot*100)
        return res
    def _calc_effective(self, cr, uid, ids, name, args, context):
        res = {}
        for sprint in self.browse(cr, uid, ids):
            res.setdefault(sprint.id, 0.0)
            for bl in sprint.backlog_ids:
                res[sprint.id] += bl.effective_hours
        return res
    def _calc_planned(self, cr, uid, ids, name, args, context):
        res = {}
        for sprint in self.browse(cr, uid, ids):
            res.setdefault(sprint.id, 0.0)
            for bl in sprint.backlog_ids:
                res[sprint.id] += bl.planned_hours
        return res
    def _calc_expected(self, cr, uid, ids, name, args, context):
        res = {}
        for sprint in self.browse(cr, uid, ids):
            res.setdefault(sprint.id, 0.0)
            for bl in sprint.backlog_ids:
                res[sprint.id] += bl.expected_hours
        return res
    def button_cancel(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'cancel'}, context=context)
        return True
    def button_draft(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'draft'}, context=context)
        return True
    def button_open(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'open'}, context=context)
        return True
    def button_close(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'done'}, context=context)
        return True
    def button_pending(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'pending'}, context=context)
        return True
    _columns = {
        'name' : fields.char('Sprint Name', required=True, size=64),
        'active' : fields.boolean('Active', help="If Active field is set to true, it will allow you to select sprint from task list view. "),
        'date_start': fields.date('Starting Date', required=True),
        'date_stop': fields.date('Ending Date', required=True),
        'project_id': fields.many2one('project.project', 'Project', required=True, domain=[('scrum','=',1)]),
        'product_owner_id': fields.many2one('res.users', 'Product Owner', required=True),
        'scrum_master_id': fields.many2one('res.users', 'Scrum Master', required=True),
        'meeting_ids': fields.one2many('scrum.meeting', 'sprint_id', 'Daily Scrum'),
        'review': fields.text('Sprint Review'),
        'retrospective': fields.text('Sprint Retrospective'),
        'backlog_ids': fields.one2many('scrum.product.backlog', 'sprint_id', 'Sprint Backlog'),
        'progress': fields.function(_calc_progress, method=True, string='Progress (0-100)'),
        'effective_hours': fields.function(_calc_effective, method=True, string='Effective hours'),
        'planned_hours': fields.function(_calc_planned, method=True, string='Planned Hours'),
        'expected_hours': fields.function(_calc_expected, method=True, string='Expected Hours'),
        'state': fields.selection([('draft','Draft'),('open','Open'),('pending','Pending'),('cancel','Cancelled'),('done','Done')], 'State', required=True),
    }
    _defaults = {
        'state': lambda *a: 'draft',
        'date_start' : lambda *a:time.strftime('%Y-%m-%d'),
        'active': lambda *a: 1,
    }
    def onchange_project_id(self, cr, uid, ids, project_id):
        v = {}
        if project_id:
            proj = self.pool.get('project.project').browse(cr, uid, [project_id])[0]
            v['product_owner_id']= proj.product_owner_id and proj.product_owner_id.id or False
            v['scrum_master_id']= proj.user_id and proj.user_id.id or False
            v['date_stop'] = (DateTime.now() + DateTime.RelativeDateTime(days=int(proj.sprint_size or 14))).strftime('%Y-%m-%d')
        return {'value':v}

scrum_sprint()

class scrum_product_backlog(osv.osv):
    _name = 'scrum.product.backlog'
    _description = 'Product Backlog'

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args=[]
        if not context:
            context={}
        match = re.match('^S\(([0-9]+)\)$', name)
        if match:
            ids = self.search(cr, uid, [('sprint_id','=', int(match.group(1)))], limit=limit, context=context)
            return self.name_get(cr, uid, ids, context=context)
        return super(scrum_product_backlog, self).name_search(cr, uid, name, args, operator,context, limit=limit)

    def _calc_progress(self, cr, uid, ids, name, args, context):
        res = {}
        for bl in self.browse(cr, uid, ids):
            tot = 0.0
            prog = 0.0
            for task in bl.tasks_id:
                tot += task.planned_hours
                prog += task.planned_hours * task.progress / 100.0
            res.setdefault(bl.id, 0.0)
            if tot>0:
                res[bl.id] = round(prog/tot*100)
        return res
    def _calc_effective(self, cr, uid, ids, name, args, context):
        res = {}
        for bl in self.browse(cr, uid, ids):
            res.setdefault(bl.id, 0.0)
            for task in bl.tasks_id:
                res[bl.id] += task.effective_hours
        return res
    def _calc_planned(self, cr, uid, ids, name, args, context):
        res = {}
        for bl in self.browse(cr, uid, ids):
            res.setdefault(bl.id, 0.0)
            for task in bl.tasks_id:
                res[bl.id] += task.planned_hours
        return res

    def button_cancel(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'cancel'}, context=context)
        for backlog in self.browse(cr, uid, ids, context=context):
            self.pool.get('project.task').write(cr, uid, [i.id for i in backlog.tasks_id], {'state': 'cancelled'})
        return True
    def button_draft(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'draft'}, context=context)
        return True
    def button_open(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'open'}, context=context)
        return True
    def button_close(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'done'}, context=context)
        return True
    def button_pending(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'pending'}, context=context)
        return True

    _columns = {
        'name' : fields.char('Feature', size=64, required=True),
        'note' : fields.text('Note'),
        'active' : fields.boolean('Active', help="If Active field is set to true, it will allow you to hide the product backlog without removing it."),
        'project_id': fields.many2one('project.project', 'Project', required=True, domain=[('scrum','=',1)]),
        'user_id': fields.many2one('res.users', 'Responsible'),
        'sprint_id': fields.many2one('scrum.sprint', 'Sprint'),
        'sequence' : fields.integer('Sequence', help="Gives the sequence order when displaying a list of product backlog."),
        'tasks_id': fields.one2many('project.task', 'product_backlog_id', 'Tasks Details'),
        'state': fields.selection([('draft','Draft'),('open','Open'),('pending','Pending'),('done','Done'),('cancel','Cancelled')], 'State', required=True),
        'progress': fields.function(_calc_progress, method=True, string='Progress'),
        'effective_hours': fields.function(_calc_effective, method=True, string='Effective hours'),
        'planned_hours': fields.function(_calc_planned, method=True, string='Planned Hours'),
        'expected_hours': fields.float('Expected Hours'),
        'date':fields.datetime("Created Date"),
    }
    _defaults = {
        'state': lambda *a: 'draft',
        'active': lambda *a: 1,
        'user_id': lambda self,cr,uid,context: uid,
    }
    _order = "sequence"
scrum_product_backlog()

class scrum_task(osv.osv):
    _name = 'project.task'
    _inherit = 'project.task'
    def _get_task(self, cr, uid, ids, context={}):
        result = {}
        for line in self.pool.get('scrum.product.backlog').browse(cr, uid, ids, context=context):
            for task in line.tasks_id:
                result[task.id] = True
        return result.keys()
    _columns = {
        'product_backlog_id': fields.many2one('scrum.product.backlog', 'Product Backlog'),
        'sprint_id': fields.related('product_backlog_id','sprint_id', type='many2one', relation='scrum.sprint', string='Sprint',
            store={
                'project.task': (lambda self, cr, uid, ids, c={}: ids, ['product_backlog_id'], 10),
                'scrum.product.backlog': (_get_task, ['sprint_id'], 10)
            }),
    }
    def onchange_backlog_id(self, cr, uid, backlog_id):
        if not backlog_id:
            return {}
        project_id = self.pool.get('scrum.product.backlog').browse(cr, uid, backlog_id).project_id.id
        return {'value': {'project_id': project_id}}
scrum_task()

class scrum_meeting(osv.osv):
    _name = 'scrum.meeting'
    _description = 'Scrum Meeting'
    _order = 'date desc'
    _columns = {
        'name' : fields.char('Meeting Name', size=64, required=True),
        'date': fields.date('Meeting Date', required=True),
        'sprint_id': fields.many2one('scrum.sprint', 'Sprint', required=True),
        'project_id': fields.many2one('project.project', 'Project'),
        'question_yesterday': fields.text('Tasks since yesterday'),
        'question_today': fields.text('Tasks for today'),
        'question_blocks': fields.text('Blocks encountered'),
        'question_backlog': fields.text('Backlog Accurate'),
        'task_ids': fields.many2many('project.task', 'meeting_task_rel', 'metting_id', 'task_id', 'Tasks')
    }
    #
    # TODO: Find the right sprint thanks to users and date
    #
    _defaults = {
        'date' : lambda *a:time.strftime('%Y-%m-%d'),
    }
scrum_meeting()

