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

import time
import netsvc
from osv import fields, osv, orm

from mx import DateTime
import re

class scrum_team(osv.osv):
    _name = 'scrum.team'
    _description = 'Scrum Team'
    _columns = {
        'name' : fields.char('Team Name', size=64),
        'users_id' : fields.many2many('res.users', 'scrum_team_users_rel', 'team_id','user_id', 'Users'),
    }
scrum_team()

class scrum_project(osv.osv):
    _name = 'scrum.project'
    _inherit = 'project.project'
    _table = 'project_project'
    _description = 'Scrum Project'
    _columns = {
        'product_owner_id': fields.many2one('res.users', 'Product Owner'),
        'tasks': fields.one2many('scrum.task', 'project_id', 'Scrum Tasks'),
        'sprint_size': fields.integer('Sprint Days'),
        'scrum': fields.integer('Is Scrum'),
        'parent_id': fields.many2one('scrum.project', 'Parent project'),
    }
    _defaults = {
        'product_owner_id': lambda self,cr,uid,context={}: uid,
        'warn_manager': lambda *a: 1,
        'sprint_size': lambda *a: 14,
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
    _columns = {
        'name' : fields.char('Sprint Name', required=True, size=64),
        'date_start': fields.date('Starting Date', required=True),
        'date_stop': fields.date('Ending Date', required=True),
        'project_id': fields.many2one('scrum.project', 'Project', required=True, domain=[('scrum','=',1)]),
        'product_owner_id': fields.many2one('res.users', 'Product Owner', required=True),
        'scrum_master_id': fields.many2one('res.users', 'Scrum Master', required=True),
        'meetings_id': fields.one2many('scrum.meeting', 'sprint_id', 'Daily Scrum'),
        'review': fields.text('Sprint Review'),
        'retrospective': fields.text('Sprint Retrospective'),
        'backlog_ids': fields.one2many('scrum.product.backlog', 'sprint_id', 'Sprint Backlog'),
        'progress': fields.function(_calc_progress, method=True, string='Progress (0-100)'),
        'effective_hours': fields.function(_calc_effective, method=True, string='Effective hours'),
        'planned_hours': fields.function(_calc_planned, method=True, string='Planned Hours'),
        'state': fields.selection([('draft','Draft'),('open','Open'),('done','Done')], 'Status', required=True),
    }
    _defaults = {
        'state': lambda *a: 'draft',
        'date_start' : lambda *a:time.strftime('%Y-%m-%d'),
    }
    def onchange_project_id(self, cr, uid, ids, project_id):
        v = {}
        if project_id:
            proj = self.pool.get('scrum.project').browse(cr, uid, [project_id])[0]
            v['product_owner_id']= proj.product_owner_id.id
            v['scrum_master_id']= proj.manager.id
            v['date_stop'] = (DateTime.now() + DateTime.RelativeDateTime(days=int(proj.sprint_size or 14))).strftime('%Y-%m-%d')
        return {'value':v}
        
scrum_sprint()

class scrum_product_backlog(osv.osv):
    _name = 'scrum.product.backlog'
    _description = 'Product Backlog'

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=80):
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
    _columns = {
        'name' : fields.char('Feature', size=64, required=True),
        'note' : fields.text('Note'),
        'active' : fields.boolean('Active'),
        'project_id': fields.many2one('scrum.project', 'Scrum Project', required=True, domain=[('scrum','=',1)]),
        'user_id': fields.many2one('res.users', 'User'),
        'sprint_id': fields.many2one('scrum.sprint', 'Sprint'),
        'sequence' : fields.integer('Sequence'),
        'priority' : fields.selection([('4','Very Low'), ('3','Low'), ('2','Medium'), ('1','Urgent'), ('0','Very urgent')], 'Priority'),
        'tasks_id': fields.one2many('scrum.task', 'product_backlog_id', 'Tasks Details'),
        'state': fields.selection([('draft','Draft'),('open','Open'),('done','Done')], 'Status', required=True),
        'progress': fields.function(_calc_progress, method=True, string='Progress (0-100)'),
        'effective_hours': fields.function(_calc_effective, method=True, string='Effective hours'),
        'planned_hours': fields.function(_calc_planned, method=True, string='Planned Hours')
    }
    _defaults = {
        'priority': lambda *a: '4',
        'state': lambda *a: 'draft',
        'active': lambda *a: 1
    }
    _order = "priority,sequence"
scrum_product_backlog()

class scrum_task(osv.osv):
    _name = 'scrum.task'
    _inherit = 'project.task'
    _table = 'project_task'
    _description = 'Scrum Task'
    _columns = {
        'product_backlog_id': fields.many2one('scrum.product.backlog', 'Product Backlog'),
        'scrum': fields.integer('Is Scrum'),
    }
    _defaults = {
        'scrum': lambda *a: 1,
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
    _columns = {
        'name' : fields.char('Meeting Name', size=64, required=True),
        'date': fields.date('Meeting Date', required=True),
        'sprint_id': fields.many2one('scrum.sprint', 'Sprint', required=True),
        'question_yesterday': fields.text('Tasks since yesterday'),
        'question_today': fields.text('Tasks for today'),
        'question_blocks': fields.text('Blocks encountered'),
        #
        # Should be more formal.
        #
        'question_backlog': fields.text('Backlog Accurate'),
    }
    #
    # Find the right sprint thanks to users and date
    #
    _defaults = {
        'date' : lambda *a:time.strftime('%Y-%m-%d'),
    }
scrum_meeting()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

