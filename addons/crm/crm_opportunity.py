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

from datetime import datetime
from osv import fields,osv,orm
from tools.translate import _
import crm
import time
import mx.DateTime

AVAILABLE_STATES = [
    ('draft','Draft'),
    ('open','Open'),
    ('cancel', 'Lost'),
    ('done', 'Converted'),
    ('pending','Pending')
]

class crm_opportunity(osv.osv):
    """ Opportunity Cases """

    _name = "crm.opportunity"
    _description = "Opportunity Cases"
    _order = "priority,date_action,id desc"
    _inherit = 'crm.case'

    def case_open(self, cr, uid, ids, *args):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case's Ids
        @param *args: Give Tuple Value
        """

        res = super(crm_opportunity, self).case_open(cr, uid, ids, *args)
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
        for opportunity in self.browse(cr, uid, ids , context):
            for field in fields:
                res[opportunity.id] = {}
                duration = 0
                ans = False
                if field == 'day_open':
                    if opportunity.date_open:
                        date_create = datetime.strptime(opportunity.create_date, "%Y-%m-%d %H:%M:%S")
                        date_open = datetime.strptime(opportunity.date_open, "%Y-%m-%d %H:%M:%S")
                        ans = date_open - date_create
                        date_until = opportunity.date_open
                elif field == 'day_close':
                    if opportunity.date_closed:
                        date_create = datetime.strptime(opportunity.create_date, "%Y-%m-%d %H:%M:%S")
                        date_close = datetime.strptime(opportunity.date_closed, "%Y-%m-%d %H:%M:%S")
                        date_until = opportunity.date_closed
                        ans = date_close - date_create
                if ans:
                    resource_id = False
                    if opportunity.user_id:
                        resource_ids = res_obj.search(cr, uid, [('user_id','=',opportunity.user_id.id)])
                        if resource_ids and len(resource_ids):
                            resource_id = resource_ids[0]

                    duration = float(ans.days)
                    if opportunity.section_id.resource_calendar_id:
                        duration =  float(ans.days) * 24
                        new_dates = cal_obj.interval_get(cr,
                            uid,
                            opportunity.section_id.resource_calendar_id and opportunity.section_id.resource_calendar_id.id or False,
                            mx.DateTime.strptime(opportunity.create_date, '%Y-%m-%d %H:%M:%S'),
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
                res[opportunity.id][field] = abs(int(duration))
        return res

    _columns = {
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', \
                     domain="[('section_id','=',section_id),\
                    ('object_id.model', '=', 'crm.opportunity')]"),
        'categ_id': fields.many2one('crm.case.categ', 'Category', \
                     domain="[('section_id','=',section_id), \
                    ('object_id.model', '=', 'crm.opportunity')]"),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
        'referred': fields.char('Referred By', size=64),
        'probability': fields.float('Probability (%)'),
        'planned_revenue': fields.float('Expected Revenue'),
        'ref': fields.reference('Reference', selection=crm._links_get, size=128),
        'ref2': fields.reference('Reference 2', selection=crm._links_get, size=128),
        'date_closed': fields.datetime('Closed', readonly=True),
        'user_id': fields.many2one('res.users', 'Salesman'),
        'phone': fields.char("Phone", size=64),
        'date_deadline': fields.date('Expected Closing'),
        'date_action': fields.date('Next Action'),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True,
                                  help='The state is set to \'Draft\', when a case is created.\
                                  \nIf the case is in progress the state is set to \'Open\'.\
                                  \nWhen the case is over, the state is set to \'Done\'.\
                                  \nIf the case needs to be reviewed then the state is set to \'Pending\'.'),

        'date_open': fields.datetime('Opened', readonly=True),
        'day_open': fields.function(_compute_day, string='Days to Open', \
                                method=True, multi='day_open', type="float", store=True),
        'day_close': fields.function(_compute_day, string='Days to Close', \
                                method=True, multi='day_close', type="float", store=True),
         }

    def onchange_stage_id(self, cr, uid, ids, stage_id, context={}):

        """ @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of stage’s IDs
            @stage_id: change state id on run time """

        if not stage_id:
            return {'value':{}}

        stage = self.pool.get('crm.case.stage').browse(cr, uid, stage_id, context)
        if not stage.on_change:
            return {'value':{}}
        return {'value':{'probability':stage.probability}}

    def stage_next(self, cr, uid, ids, context={}):

        """ @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of stage next’s IDs
            @param context: A standard dictionary for contextual values """

        res = super(crm_opportunity, self).stage_next(cr, uid, ids, context=context)
        for case in self.browse(cr, uid, ids, context):
            if case.stage_id and case.stage_id.on_change:
                self.write(cr, uid, [case.id], {'probability': case.stage_id.probability})
        return res

    def stage_previous(self, cr, uid, ids, context={}):

        """ @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of stage previous’s IDs
            @param context: A standard dictionary for contextual values """

        res = super(crm_opportunity, self).stage_previous(cr, uid, ids, context=context)
        for case in self.browse(cr, uid, ids, context):
            if case.stage_id and case.stage_id.on_change:
                self.write(cr, uid, [case.id], {'probability': case.stage_id.probability})
        return res

    _defaults = {
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.opportunity', context=c),
        'priority': lambda *a: crm.AVAILABLE_PRIORITIES[2][0],
        'state' : 'draft',
    }

    def action_makeMeeting(self, cr, uid, ids, context=None):
        """
        This opens Meeting's calendar view to schedule meeting on current Opportunity
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Opportunity to Meeting IDs
        @param context: A standard dictionary for contextual values

        @return : Dictionary value for created Meeting view
        """
        value = {}
        for opp in self.browse(cr, uid, ids):
            data_obj = self.pool.get('ir.model.data')

            # Get meeting views
            result = data_obj._get_id(cr, uid, 'crm', 'view_crm_case_meetings_filter')
            res = data_obj.read(cr, uid, result, ['res_id'])
            id1 = data_obj._get_id(cr, uid, 'crm', 'crm_case_calendar_view_meet')
            id2 = data_obj._get_id(cr, uid, 'crm', 'crm_case_form_view_meet')
            id3 = data_obj._get_id(cr, uid, 'crm', 'crm_case_tree_view_meet')
            if id1:
                id1 = data_obj.browse(cr, uid, id1, context=context).res_id
            if id2:
                id2 = data_obj.browse(cr, uid, id2, context=context).res_id
            if id3:
                id3 = data_obj.browse(cr, uid, id3, context=context).res_id

            context = {
                'default_opportunity_id': opp.id,
                'default_partner_id': opp.partner_id and opp.partner_id.id or False,
                'default_section_id': opp.section_id and opp.section_id.id or False,
                'default_email_from': opp.email_from,
                'default_state': 'open',
                'default_name': opp.name
            }
            value = {
                'name': _('Meetings'),
                'domain': "[('user_id','=',%s),('opportunity_id','=',%s)]" % (uid,opp.id),
                'context': context,
                'view_type': 'form',
                'view_mode': 'calendar,form,tree',
                'res_model': 'crm.meeting',
                'view_id': False,
                'views': [(id1, 'calendar'), (id2, 'form'), (id3, 'tree')],
                'type': 'ir.actions.act_window',
                'search_view_id': res['res_id'],
                'nodestroy': True
            }
        return value

crm_opportunity()

