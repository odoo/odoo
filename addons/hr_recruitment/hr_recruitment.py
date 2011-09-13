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
from datetime import datetime, timedelta

from osv import fields, osv
from crm import crm
import tools
import collections
import binascii
import tools
from tools.translate import _

AVAILABLE_STATES = [
    ('draft', 'New'),
    ('open', 'In Progress'),
    ('cancel', 'Refused'),
    ('done', 'Hired'),
    ('pending', 'Pending')
]

AVAILABLE_PRIORITIES = [
    ('', ''),
    ('5', 'Not Good'),
    ('4', 'On Average'),
    ('3', 'Good'),
    ('2', 'Very Good'),
    ('1', 'Excellent')
]

class hr_recruitment_source(osv.osv):
    """ Sources of HR Recruitment """
    _name = "hr.recruitment.source"
    _description = "Source of Applicants"
    _columns = {
        'name': fields.char('Source Name', size=64, required=True, translate=True),
    }
hr_recruitment_source()


class hr_recruitment_stage(osv.osv):
    """ Stage of HR Recruitment """
    _name = "hr.recruitment.stage"
    _description = "Stage of Recruitment"
    _order = 'sequence'
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of stages."),
        'department_id':fields.many2one('hr.department', 'Department', help="Stages of the recruitment process may be different per department. If this stage is common to all departments, keep tempy this field."),
        'requirements': fields.text('Requirements')
    }
    _defaults = {
        'sequence': 1,
    }
hr_recruitment_stage()

class hr_recruitment_degree(osv.osv):
    """ Degree of HR Recruitment """
    _name = "hr.recruitment.degree"
    _description = "Degree of Recruitment"
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of degrees."),
    }
    _defaults = {
        'sequence': 1,
    }
hr_recruitment_degree()

class hr_applicant(crm.crm_case, osv.osv):
    _name = "hr.applicant"
    _description = "Applicant"
    _order = "id desc"
    _inherit = ['mailgate.thread']

    def _compute_day(self, cr, uid, ids, fields, args, context=None):
        """
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Openday’s IDs
        @return: difference between current date and log date
        @param context: A standard dictionary for contextual values
        """
        res = {}
        for issue in self.browse(cr, uid, ids, context=context):
            for field in fields:
                res[issue.id] = {}
                duration = 0
                ans = False
                hours = 0

                if field in ['day_open']:
                    if issue.date_open:
                        date_create = datetime.strptime(issue.create_date, "%Y-%m-%d %H:%M:%S")
                        date_open = datetime.strptime(issue.date_open, "%Y-%m-%d %H:%M:%S")
                        ans = date_open - date_create
                        date_until = issue.date_open

                elif field in ['day_close']:
                    if issue.date_closed:
                        date_create = datetime.strptime(issue.create_date, "%Y-%m-%d %H:%M:%S")
                        date_close = datetime.strptime(issue.date_closed, "%Y-%m-%d %H:%M:%S")
                        date_until = issue.date_closed
                        ans = date_close - date_create
                if ans:
                    duration = float(ans.days)
                    res[issue.id][field] = abs(float(duration))
        return res

    _columns = {
        'name': fields.char('Name', size=128, required=True),
        'message_ids': fields.one2many('mailgate.message', 'res_id', 'Messages', domain=[('model','=',_name)]),
        'active': fields.boolean('Active', help="If the active field is set to false, it will allow you to hide the case without removing it."),
        'description': fields.text('Description'),
        'email_from': fields.char('Email', size=128, help="These people will receive email."),
        'email_cc': fields.text('Watchers Emails', size=252, help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
        'probability': fields.float('Probability'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'partner_address_id': fields.many2one('res.partner.address', 'Partner Contact', \
                                 domain="[('partner_id','=',partner_id)]"),
        'create_date': fields.datetime('Creation Date', readonly=True, select=True),
        'write_date': fields.datetime('Update Date', readonly=True),
        'stage_id': fields.many2one ('hr.recruitment.stage', 'Stage'),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True,
                                  help='The state is set to \'Draft\', when a case is created.\
                                  \nIf the case is in progress the state is set to \'Open\'.\
                                  \nWhen the case is over, the state is set to \'Done\'.\
                                  \nIf the case needs to be reviewed then the state is set to \'Pending\'.'),
        'company_id': fields.many2one('res.company', 'Company'),
        'user_id': fields.many2one('res.users', 'Responsible'),
        # Applicant Columns
        'date_closed': fields.datetime('Closed', readonly=True, select=True),
        'date_open': fields.datetime('Opened', readonly=True, select=True),
        'date': fields.datetime('Date'),
        'date_action': fields.date('Next Action Date'),
        'title_action': fields.char('Next Action', size=64),
        'priority': fields.selection(AVAILABLE_PRIORITIES, 'Appreciation'),
        'job_id': fields.many2one('hr.job', 'Applied Job'),
        'salary_proposed_extra': fields.char('Proposed Salary Extra', size=100, help="Salary Proposed by the Organisation, extra advantages"),
        'salary_expected_extra': fields.char('Expected Salary Extra', size=100, help="Salary Expected by Applicant, extra advantages"),
        'salary_proposed': fields.float('Proposed Salary', help="Salary Proposed by the Organisation"),
        'salary_expected': fields.float('Expected Salary', help="Salary Expected by Applicant"),
        'availability': fields.integer('Availability (Days)'),
        'partner_name': fields.char("Applicant's Name", size=64),
        'partner_phone': fields.char('Phone', size=32),
        'partner_mobile': fields.char('Mobile', size=32),
        'type_id': fields.many2one('hr.recruitment.degree', 'Degree'),
        'department_id': fields.many2one('hr.department', 'Department'),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),
        'survey': fields.related('job_id', 'survey_id', type='many2one', relation='survey', string='Survey'),
        'response': fields.integer("Response"),
        'reference': fields.char('Refered By', size=128),
        'source_id': fields.many2one('hr.recruitment.source', 'Source'),
        'day_open': fields.function(_compute_day, string='Days to Open', \
                                multi='day_open', type="float", store=True),
        'day_close': fields.function(_compute_day, string='Days to Close', \
                                multi='day_close', type="float", store=True),
    }

    def _get_stage(self, cr, uid, context=None):
        ids = self.pool.get('hr.recruitment.stage').search(cr, uid, [], context=context)
        return ids and ids[0] or False

    _defaults = {
        'active': lambda *a: 1,
        'user_id':  lambda self, cr, uid, context: uid,
        'email_from': crm.crm_case. _get_default_email,
        'state': lambda *a: 'draft',
        'priority': lambda *a: '',
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.helpdesk', context=c),
        'priority': lambda *a: crm.AVAILABLE_PRIORITIES[2][0],
    }

    def onchange_job(self,cr, uid, ids, job, context=None):
        result = {}

        if job:
            job_obj = self.pool.get('hr.job')
            result['department_id'] = job_obj.browse(cr, uid, job, context=context).department_id.id
            return {'value': result}
        return {'value': {'department_id': False}}

    def onchange_department_id(self, cr, uid, ids, department_id=False, context=None):
        if not department_id:
            return {'value': {'stage_id': False}}
        obj_recru_stage = self.pool.get('hr.recruitment.stage')
        stage_ids = obj_recru_stage.search(cr, uid, ['|',('department_id','=',department_id),('department_id','=',False)], context=context)
        stage_id = stage_ids and stage_ids[0] or False
        return {'value': {'stage_id': stage_id}}

    def stage_previous(self, cr, uid, ids, context=None):
        """This function computes previous stage for case from its current stage
             using available stage for that case type
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case IDs
        @param context: A standard dictionary for contextual values"""
        stage_obj = self.pool.get('hr.recruitment.stage')
        for case in self.browse(cr, uid, ids, context=context):
            department = (case.department_id.id or False)
            st = case.stage_id.id  or False
            stage_ids = stage_obj.search(cr, uid, ['|',('department_id','=',department),('department_id','=',False)], context=context)
            if st and stage_ids.index(st):
                self.write(cr, uid, [case.id], {'stage_id': stage_ids[stage_ids.index(st)-1]}, context=context)
            else:
                self.write(cr, uid, [case.id], {'stage_id': False}, context=context)
        return True

    def stage_next(self, cr, uid, ids, context=None):
        """This function computes next stage for case from its current stage
             using available stage for that case type
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case IDs
        @param context: A standard dictionary for contextual values"""
        stage_obj = self.pool.get('hr.recruitment.stage')
        for case in self.browse(cr, uid, ids, context=context):
            department = (case.department_id.id or False)
            st = case.stage_id.id  or False
            stage_ids = stage_obj.search(cr, uid, ['|',('department_id','=',department),('department_id','=',False)], context=context)
            val = False
            if st and len(stage_ids) != stage_ids.index(st)+1:
                val = stage_ids[stage_ids.index(st)+1]
            elif (not st) and stage_ids:
                val = stage_ids[0]
            else:
                val = False
            self.write(cr, uid, [case.id], {'stage_id': val}, context=context)
        return True

    def action_makeMeeting(self, cr, uid, ids, context=None):
        """
        This opens Meeting's calendar view to schedule meeting on current Opportunity
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Opportunity to Meeting IDs
        @param context: A standard dictionary for contextual values

        @return: Dictionary value for created Meeting view
        """
        data_obj = self.pool.get('ir.model.data')
        if context is None:
            context = {}
        value = {}
        for opp in self.browse(cr, uid, ids, context=context):
            # Get meeting views
            result = data_obj._get_id(cr, uid, 'crm', 'view_crm_case_meetings_filter')
            res = data_obj.read(cr, uid, result, ['res_id'], context=context)
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
                'default_email_from': opp.email_from,
                'default_state': 'open',
                'default_name': opp.name
            }
            value = {
                'name': ('Meetings'),
                'domain': "[('user_id','=',%s)]" % (uid),
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

    def action_print_survey(self, cr, uid, ids, context=None):
        """
        If response is available then print this response otherwise print survey form(print template of the survey).

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Survey IDs
        @param context: A standard dictionary for contextual values
        @return: Dictionary value for print survey form.
        """
        if context is None:
            context = {}
        record = self.browse(cr, uid, ids, context=context)
        record = record and record[0]
        context.update({'survey_id': record.survey.id, 'response_id': [record.response], 'response_no': 0, })
        value = self.pool.get("survey").action_print_survey(cr, uid, ids, context=context)
        return value

    def message_new(self, cr, uid, msg, context=None):
        """
        Automatically calls when new email message arrives

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks
        """
        mailgate_pool = self.pool.get('email.server.tools')
        attach_obj = self.pool.get('ir.attachment')

        subject = msg.get('subject') or _("No Subject")
        body = msg.get('body')
        msg_from = msg.get('from')
        priority = msg.get('priority')

        vals = {
            'name': subject,
            'email_from': msg_from,
            'email_cc': msg.get('cc'),
            'description': body,
            'user_id': False,
        }
        if msg.get('priority', False):
            vals['priority'] = priority

        res = mailgate_pool.get_partner(cr, uid, msg.get('from'))
        if res:
            vals.update(res)
        res = self.create(cr, uid, vals, context=context)

        attachents = msg.get('attachments', [])
        for attactment in attachents or []:
            data_attach = {
                'name': attactment,
                'datas':binascii.b2a_base64(str(attachents.get(attactment))),
                'datas_fname': attactment,
                'description': 'Mail attachment',
                'res_model': self._name,
                'res_id': res,
            }
            attach_obj.create(cr, uid, data_attach, context=context)

        return res

    def message_update(self, cr, uid, ids, vals={}, msg="", default_act='pending', context=None):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of update mail’s IDs
        """

        if isinstance(ids, (str, int, long)):
            ids = [ids]

        msg_from = msg['from']
        vals.update({
            'description': msg['body']
        })
        if msg.get('priority', False):
            vals['priority'] = msg.get('priority')

        maps = {
            'cost':'planned_cost',
            'revenue': 'planned_revenue',
            'probability':'probability'
        }
        vls = { }
        for line in msg['body'].split('\n'):
            line = line.strip()
            res = tools.misc.command_re.match(line)
            if res and maps.get(res.group(1).lower(), False):
                key = maps.get(res.group(1).lower())
                vls[key] = res.group(2).lower()

        vals.update(vls)
        res = self.write(cr, uid, ids, vals, context=context)
        return res

    def msg_send(self, cr, uid, id, *args, **argv):
        """ Send The Message
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of email’s IDs
            @param *args: Return Tuple Value
            @param **args: Return Dictionary of Keyword Value
        """
        return True

    def case_open(self, cr, uid, ids, *args):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case's Ids
        @param *args: Give Tuple Value
        """
        res = super(hr_applicant, self).case_open(cr, uid, ids, *args)
        date = self.read(cr, uid, ids, ['date_open'])[0]
        if not date['date_open']:
            self.write(cr, uid, ids, {'date_open': time.strftime('%Y-%m-%d %H:%M:%S'),})
        for (id, name) in self.name_get(cr, uid, ids):
            message = _("The job request '%s' has been set 'in progress'.") % name
            self.log(cr, uid, id, message)
        return res

    def case_close(self, cr, uid, ids, *args):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case's Ids
        @param *args: Give Tuple Value
        """
        employee_obj = self.pool.get('hr.employee')
        res = super(hr_applicant, self).case_close(cr, uid, ids, *args)
        for (id, name) in self.name_get(cr, uid, ids):
            message = _("Applicant '%s' is being hired.") % name
            self.log(cr, uid, id, message)
        return res

    def case_close_with_emp(self, cr, uid, ids, *args):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case's Ids
        @param *args: Give Tuple Value
        """
        employee_obj = self.pool.get('hr.employee')
        partner_obj = self.pool.get('res.partner')
        address_id = False
        applicant = self.browse(cr, uid, ids)[0]
        if applicant.partner_id:
            address_id = partner_obj.address_get(cr, uid, [applicant.partner_id.id], ['contact'])['contact']
        if applicant.job_id:
            self.pool.get('hr.job').write(cr, uid, [applicant.job_id.id], {'no_of_recruitment': applicant.job_id.no_of_recruitment - 1})
            emp_id = employee_obj.create(cr,uid,{'name': applicant.partner_name or applicant.name,
                                                 'job_id': applicant.job_id.id,
                                                 'address_home_id': address_id,
                                                 'department_id': applicant.department_id.id
                                                 })
        else:
            raise osv.except_osv(_('Warning!'),_('You must define Applied Job for Applicant !'))
        return self.case_close(cr, uid, ids, *args)

    def case_reset(self, cr, uid, ids, *args):
        """Resets case as draft
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case Ids
        @param *args: Tuple Value for additional Params
        """

        res = super(hr_applicant, self).case_reset(cr, uid, ids, *args)
        self.write(cr, uid, ids, {'date_open': False, 'date_closed': False})
        return res


hr_applicant()

class hr_job(osv.osv):
    _inherit = "hr.job"
    _name = "hr.job"
    _columns = {
        'survey_id': fields.many2one('survey', 'Survey', help="Select survey for the current job"),
    }
hr_job()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
