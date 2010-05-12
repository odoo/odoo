 #-*- coding: utf-8 -*-
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

import base64
import os
import re
import time
import mx.DateTime
from datetime import datetime, timedelta

import tools
from crm import crm
from osv import fields,osv,orm
from osv.orm import except_orm
from tools.translate import _

class project_issue(osv.osv):
    _name = "project.issue"
    _description = "Project Issue"
    _order = "priority, id desc"
    _inherit = 'crm.case'

    def case_open(self, cr, uid, ids, *args):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case's Ids
        @param *args: Give Tuple Value
        """

        res = super(project_issue, self).case_open(cr, uid, ids, *args)
        self.write(cr, uid, ids, {'date_open': time.strftime('%Y-%m-%d %H:%M:%S')})
        return res

    def _compute_day(self, cr, uid, ids, fields, args, context={}):
        """
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Openday’s IDs
        @return: difference between current date and log date
        @param context: A standard dictionary for contextual values
        """
        cal_obj = self.pool.get('resource.calendar')
        res_obj = self.pool.get('resource.resource')

        res = {}
        for issue in self.browse(cr, uid, ids , context):
            for field in fields:
                res[issue.id] = {}
                duration = 0
                ans = False
                if field == 'day_open':
                    if issue.date_open:
                        date_create = datetime.strptime(issue.create_date, "%Y-%m-%d %H:%M:%S")
                        date_open = datetime.strptime(issue.date_open, "%Y-%m-%d %H:%M:%S")
                        ans = date_open - date_create
                        date_until = issue.date_open
                elif field == 'day_close':
                    if issue.date_closed:
                        date_create = datetime.strptime(issue.create_date, "%Y-%m-%d %H:%M:%S")
                        date_close = datetime.strptime(issue.date_closed, "%Y-%m-%d %H:%M:%S")
                        date_until = issue.date_closed
                        ans = date_close - date_create
                if ans:
                    resource_id = False
                    if issue.user_id:
                        resource_ids = res_obj.search(cr, uid, [('user_id','=',issue.user_id.id)])
                        resource_id = len(resource_ids) and resource_ids[0] or False

                    duration = float(ans.days)
                    if issue.section_id.resource_calendar_id:
                        duration =  float(ans.days) * 24
                        new_dates = cal_obj.interval_get(cr,
                            uid,
                            issue.section_id.resource_calendar_id and issue.section_id.resource_calendar_id.id or False,
                            mx.DateTime.strptime(issue.create_date, '%Y-%m-%d %H:%M:%S'),
                            duration,
                            resource=resource_id
                        )
                        no_days = []
                        date_until = mx.DateTime.strptime(date_until, '%Y-%m-%d %H:%M:%S')
                        for in_time, out_time in new_dates:
                            if in_time.date not in no_days:
                                no_days.append(in_time.date)
                            if out_time > date_until:
                                break
                        duration =  len(no_days)
                res[issue.id][field] = abs(float(duration))

        return res

    _columns = {
        'date_closed': fields.datetime('Closed', readonly=True),
        'date': fields.datetime('Date'),
        'canal_id': fields.many2one('res.partner.canal', 'Channel',help="The channels represent the different communication modes available with the customer." \
                                                                        " With each commercial opportunity, you can indicate the canall which is this opportunity source."),
        'categ_id': fields.many2one('crm.case.categ','Category', domain="[('object_id.model', '=', 'crm.project.bug')]"),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Severity'),
        'type_id': fields.many2one('crm.case.resource.type', 'Version', domain="[('object_id.model', '=', 'project.issue')]"),
        'partner_name': fields.char("Employee's Name", size=64),
        'partner_mobile': fields.char('Mobile', size=32),
        'partner_phone': fields.char('Phone', size=32),
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', domain="[('object_id.model', '=', 'project.issue')]"),
        'project_id':fields.many2one('project.project', 'Project'),
        'duration': fields.float('Duration'),
        'task_id': fields.many2one('project.task', 'Task', domain="[('project_id','=',project_id)]"),
        'date_open': fields.datetime('Opened', readonly=True),
        'day_open': fields.function(_compute_day, string='Days to Open', \
                                method=True, multi='day_open', type="float", store=True),
        'day_close': fields.function(_compute_day, string='Days to Close', \
                                method=True, multi='day_close', type="float", store=True),
        'assigned_to' : fields.many2one('res.users', 'Assigned to'),
    }

    def _get_project(self, cr, uid, context):
       user = self.pool.get('res.users').browse(cr,uid,uid, context=context)
       if user.context_project_id:
           return user.context_project_id.id
       return False

    def convert_issue_task(self, cr, uid, ids, context=None):
        case_obj = self.pool.get('project.issue')
        data_obj = self.pool.get('ir.model.data')
        task_obj = self.pool.get('project.task')

        if context is None:
            context = {}

#        for case in case_obj.browse(cr, uid, ids, context=context):
#            if case.state != 'open':
#                raise osv.except_osv(_('Warning !'),
#                    _('Issues or Feature Requests should be in \'Open\' state before converting into Task.'))

        result = data_obj._get_id(cr, uid, 'project', 'view_task_search_form')
        res = data_obj.read(cr, uid, result, ['res_id'])
        id2 = data_obj._get_id(cr, uid, 'project', 'view_task_form2')
        id3 = data_obj._get_id(cr, uid, 'project', 'view_task_tree2')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        if id3:
            id3 = data_obj.browse(cr, uid, id3, context=context).res_id

        for bug in case_obj.browse(cr, uid, ids, context=context):
            new_task_id = task_obj.create(cr, uid, {
                'name': bug.name,
                'partner_id': bug.partner_id.id,
                'description':bug.description,
                'date': bug.date,
                'project_id':bug.project_id.id,
                'priority':bug.priority,
                'user_id':bug.assigned_to.id,
                'planned_hours': 0.0,
            })

            new_task = task_obj.browse(cr, uid, new_task_id)

            vals = {
                'task_id': new_task_id,
                }
            case_obj.write(cr, uid, [bug.id], vals)

        return  {
            'name': _('Tasks'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'project.task',
            'res_id': int(new_task_id),
            'view_id': False,
            'views': [(id2,'form'),(id3,'tree'),(False,'calendar'),(False,'graph')],
            'type': 'ir.actions.act_window',
            'search_view_id': res['res_id'],
            'nodestroy': True
        }

    def _convert(self, cr, uid, ids, xml_id, context=None):
        data_obj = self.pool.get('ir.model.data')
        id2 = data_obj._get_id(cr, uid, 'project_issue', xml_id)
        categ_id = False
        if id2:
            categ_id = data_obj.browse(cr, uid, id2, context=context).res_id
        if categ_id:
            self.write(cr, uid, ids, {'categ_id': categ_id})
        return True

    def convert_to_feature(self, cr, uid, ids, context=None):
        return self._convert(cr, uid, ids, 'feature_request_categ', context=context)

    def convert_to_bug(self, cr, uid, ids, context=None):
        return self._convert(cr, uid, ids, 'bug_categ', context=context)

    def onchange_stage_id(self, cr, uid, ids, stage_id, context={}):
        if not stage_id:
            return {'value':{}}
        stage = self.pool.get('crm.case.stage').browse(cr, uid, stage_id, context)
        if not stage.on_change:
            return {'value':{}}
        return {'value':{}}

    _defaults = {
        'project_id':_get_project,
    }

project_issue()

