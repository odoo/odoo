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
import time
import tools
from crm import crm
from datetime import datetime, timedelta
from osv import fields,osv,orm
from osv.orm import except_orm
from tools.translate import _

class project_issue(osv.osv):
    _name = "project.issue"
    _description = "Project Issue"
    _order = "priority, id desc"
    _inherit = 'crm.case'

    def _compute_day(self, cr, uid, ids, fields, args, context={}):
        """
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Openday’s IDs
        @return: difference between current date and log date
        @param context: A standard dictionary for contextual values
        """
        log_obj = self.pool.get('crm.case.log')
        model_obj = self.pool.get('ir.model')
        cal_obj = self.pool.get('resource.calendar')

        model_ids = model_obj.search(cr, uid, [('model', '=', self._name)])
        model_id = False
        if len(model_ids):
            model_id = model_ids[0]

        res = {}
        for lead in self.browse(cr, uid, ids , context):
            for field in fields:
                res[lead.id] = {}
                duration = 0
                if field == 'day_open':
                    if lead.date_open:
                        date_create = datetime.strptime(lead.create_date, "%Y-%m-%d %H:%M:%S")
                        date_open = datetime.strptime(lead.date_open, "%Y-%m-%d %H:%M:%S")

                        ans = date_open - date_create
                        duration =  float(ans.days) + (float(ans.seconds) / 86400)

                elif field == 'day_close':
                    if lead.date_closed:
                        date_create = datetime.strptime(lead.create_date, "%Y-%m-%d %H:%M:%S")
                        date_close = datetime.strptime(lead.date_closed, "%Y-%m-%d %H:%M:%S")

                        ans = date_close - date_create
                        duration =  float(ans.days) + (float(ans.seconds) / 86400)
                res[lead.id][field] = abs(int(duration))
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
                                method=True, multi='day_open', type="integer", store=True),
        'day_close': fields.function(_compute_day, string='Days to Close', \
                                method=True, multi='day_close', type="integer", store=True),
       'assigned_to' : fields.many2one('res.users', 'Assigned to'),
        'timesheet_ids' : fields.one2many('hr.analytic.timesheet', 'issue_id', 'Timesheets'),
        'analytic_account_id' : fields.many2one('account.analytic.account', 'Analytic Account',
                                                domain="[('partner_id', '=', partner_id)]",
                                                required=True),
    }

    def _get_project(self, cr, uid, context):
       user = self.pool.get('res.users').browse(cr,uid,uid, context=context)
       if user.context_project_id:
           return user.context_project_id
       return False

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

class account_analytic_line(osv.osv):
    _inherit = 'account.analytic.line'
    _columns = {
        'create_date' : fields.datetime('Create Date', readonly=True),
    }

account_analytic_line()

class hr_analytic_issue(osv.osv):
    _inherit = 'hr.analytic.timesheet'

    _columns = {
        'issue_id' : fields.many2one('project.issue', 'Issue'),
    }

hr_analytic_issue()

