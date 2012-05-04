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
from crm import wizard

wizard.mail_compose_message.SUPPORTED_MODELS.append('hr.applicant')

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
        'department_id':fields.many2one('hr.department', 'Specific to a Department', help="Stages of the recruitment process may be different per department. If this stage is common to all departments, keep tempy this field."),
        'state': fields.selection(AVAILABLE_STATES, 'State', required=True, help="The related state for the stage. The state of you document will automatically change regarding the selected stage. Example, a stage is related to the state 'Close', when your document reach this stage, it will be automatically closed."),
        'requirements': fields.text('Requirements')
    }
    _defaults = {
        'sequence': 1,
        'state': 'draft',
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
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The name of the Degree of Recruitment must be unique!')
    ]
hr_recruitment_degree()

class hr_applicant(crm.crm_case, osv.osv):
    _name = "hr.applicant"
    _description = "Applicant"
    _order = "id desc"
    _inherit = ['ir.needaction_mixin', 'mail.thread']

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
 
    def _get_state(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for applicant in self.browse(cr, uid, ids, context=context):
            if applicant.stage_id:
                res[applicant.id] = applicant.stage_id.state
        return res

    def _get_stage(self, cr, uid, ids, context=None):
        applicant_obj = self.pool.get('hr.applicant')
        result = {}
        for stage in self.browse(cr, uid, ids, context=context):
            if stage.state:
                applicant_ids = applicant_obj.search(cr, uid, [('state', '=', stage.state)], context=context)
        for applicant in applicant_obj.browse(cr, uid, applicant_ids, context=context):
            result[applicant.id] = True
        return result.keys()

    def _save_state(self, cr, uid, applicant_id, field_name, field_value, arg, context=None):
        stage_ids = self.pool.get('hr.recruitment.stage').search(cr, uid, [('state', '=', field_value)], order='sequence', context=context)
        if stage_ids:
            return self.write(cr, uid, [applicant_id], {'stage_id': stage_ids[0]}, context=context)
        else:
            return cr.execute("""UPDATE hr_applicant SET state=%s WHERE id=%s""", (field_value, applicant_id))
    

    _columns = {
        'name': fields.char('Name', size=128, required=True),
        'message_ids': fields.one2many('mail.message', 'res_id', 'Messages', domain=[('model','=',_name)]),
        'active': fields.boolean('Active', help="If the active field is set to false, it will allow you to hide the case without removing it."),
        'description': fields.text('Description'),
        'email_from': fields.char('Email', size=128, help="These people will receive email."),
        'email_cc': fields.text('Watchers Emails', size=252, help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
        'probability': fields.float('Probability'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'create_date': fields.datetime('Creation Date', readonly=True, select=True),
        'write_date': fields.datetime('Update Date', readonly=True),
        'stage_id': fields.many2one ('hr.recruitment.stage', 'Stage'),
        'state': fields.function(_get_state, fnct_inv=_save_state, type='selection', selection=AVAILABLE_STATES, string="State", readonly=True,
            store = {
                     'hr.applicant': (lambda self, cr, uid, ids, c={}: ids, ['stage_id'], 10),
                     'hr.recruitment.stage': (_get_stage, ['state'], 10)
            }, help='The state is set to \'Draft\', when a case is created.\
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
        'survey': fields.related('job_id', 'survey_id', type='many2one', relation='survey', string='Survey'),
        'response': fields.integer("Response"),
        'reference': fields.char('Refered By', size=128),
        'source_id': fields.many2one('hr.recruitment.source', 'Source'),
        'day_open': fields.function(_compute_day, string='Days to Open', \
                                multi='day_open', type="float", store=True),
        'day_close': fields.function(_compute_day, string='Days to Close', \
                                multi='day_close', type="float", store=True),
        'color': fields.integer('Color Index'),
        'emp_id': fields.many2one('hr.employee', 'employee'),
        'user_email': fields.related('user_id', 'user_email', type='char', string='User Email', readonly=True),
    }

    _defaults = {
        'active': lambda *a: 1,
        'user_id':  lambda self, cr, uid, context: uid,
        'email_from': crm.crm_case. _get_default_email,
        'state': 'draft',
        'priority': lambda *a: '',
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.helpdesk', context=c),
        'color': 0,
    }

    def _read_group_stage_ids(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        access_rights_uid = access_rights_uid or uid
        stage_obj = self.pool.get('hr.recruitment.stage')
        order = stage_obj._order
        if read_group_order == 'stage_id desc':
            # lame hack to allow reverting search, should just work in the trivial case
            order = "%s desc" % order
        stage_ids = stage_obj._search(cr, uid, ['|',('id','in',ids),('department_id','=',False)], order=order,
                                      access_rights_uid=access_rights_uid, context=context)
        result = stage_obj.name_get(cr, access_rights_uid, stage_ids, context=context)
        # restore order of the search
        result.sort(lambda x,y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))
        return result

    _group_by_full = {
        'stage_id': _read_group_stage_ids
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

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """Automatically called when new email message arrives"""
        res_id = super(hr_applicant,self).message_new(cr, uid, msg, custom_values=custom_values, context=context)
        subject = msg.get('subject') or _("No Subject")
        body = msg.get('body_text')
        msg_from = msg.get('from')
        priority = msg.get('priority')
        vals = {
            'name': subject,
            'email_from': msg_from,
            'email_cc': msg.get('cc'),
            'description': body,
            'user_id': False,
        }
        if priority:
            vals['priority'] = priority
        vals.update(self.message_partner_by_email(cr, uid, msg.get('from', False)))
        self.write(cr, uid, [res_id], vals, context)
        return res_id

    def message_update(self, cr, uid, ids, msg, vals=None, default_act='pending', context=None):
        if isinstance(ids, (str, int, long)):
            ids = [ids]
        if vals is None:
            vals = {}
        msg_from = msg['from']
        vals.update({
            'description': msg['body_text']
        })
        if msg.get('priority', False):
            vals['priority'] = msg.get('priority')

        maps = {
            'cost':'planned_cost',
            'revenue': 'planned_revenue',
            'probability':'probability'
        }
        vls = { }
        for line in msg['body_text'].split('\n'):
            line = line.strip()
            res = tools.misc.command_re.match(line)
            if res and maps.get(res.group(1).lower(), False):
                key = maps.get(res.group(1).lower())
                vls[key] = res.group(2).lower()

        vals.update(vls)
        res = self.write(cr, uid, ids, vals, context=context)
        self.message_append_dict(cr, uid, ids, msg, context=context)
        return res

    def create(self, cr, uid, vals, context=None):
        obj_id = super(hr_applicant, self).create(cr, uid, vals, context=context)
        self.create_send_note(cr, uid, [obj_id], context=context)
        return obj_id

    def case_open(self, cr, uid, ids, context=None):
        """
            open Request of the applicant for the hr_recruitment
        """
        res = super(hr_applicant, self).case_open(cr, uid, ids, context)
        date = self.read(cr, uid, ids, ['date_open'])[0]
        if not date['date_open']:
            self.write(cr, uid, ids, {'date_open': time.strftime('%Y-%m-%d %H:%M:%S'),})
        return res

    def case_close(self, cr, uid, ids, context=None):
        res = super(hr_applicant, self).case_close(cr, uid, ids, context)
        return res

    def case_close_with_emp(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        hr_employee = self.pool.get('hr.employee')
        model_data = self.pool.get('ir.model.data')
        act_window = self.pool.get('ir.actions.act_window')
        emp_id = False
        for applicant in self.browse(cr, uid, ids, context=context):
            address_id = False
            if applicant.partner_id:
                address_id = applicant.partner_id.address_get(['contact'])['contact']
            if applicant.job_id:
                applicant.job_id.write({'no_of_recruitment': applicant.job_id.no_of_recruitment - 1})
                emp_id = hr_employee.create(cr,uid,{'name': applicant.partner_name or applicant.name,
                                                     'job_id': applicant.job_id.id,
                                                     'address_home_id': address_id,
                                                     'department_id': applicant.department_id.id
                                                     })
                self.write(cr, uid, [applicant.id], {'emp_id': emp_id}, context=context)
                self.case_close(cr, uid, [applicant.id], context)
            else:
                raise osv.except_osv(_('Warning!'),_('You must define Applied Job for this applicant.'))

        action_model, action_id = model_data.get_object_reference(cr, uid, 'hr', 'open_view_employee_list')
        dict_act_window = act_window.read(cr, uid, action_id, [])
        if emp_id:
            dict_act_window['res_id'] = emp_id
        dict_act_window['view_mode'] = 'form,tree'
        return dict_act_window

    def case_cancel(self, cr, uid, ids, context=None):
        """Overrides cancel for crm_case for setting probability
        """
        res = super(hr_applicant, self).case_cancel(cr, uid, ids, context)
        self.write(cr, uid, ids, {'probability' : 0.0})
        return res

    def case_pending(self, cr, uid, ids, context=None):
        """Marks case as pending"""
        res = super(hr_applicant, self).case_pending(cr, uid, ids, context)
        self.write(cr, uid, ids, {'probability' : 0.0})
        return res

    def case_reset(self, cr, uid, ids, context=None):
        """Resets case as draft
        """
        res = super(hr_applicant, self).case_reset(cr, uid, ids, context)
        self.write(cr, uid, ids, {'date_open': False, 'date_closed': False})
        return res

    def set_priority(self, cr, uid, ids, priority, *args):
        """Set applicant priority
        """
        return self.write(cr, uid, ids, {'priority' : priority})

    def set_high_priority(self, cr, uid, ids, *args):
        """Set applicant priority to high
        """
        return self.set_priority(cr, uid, ids, '1')

    def set_normal_priority(self, cr, uid, ids, *args):
        """Set applicant priority to normal
        """
        return self.set_priority(cr, uid, ids, '3')

    def write(self, cr, uid, ids, vals, context=None):
        if 'stage_id' in vals and vals['stage_id']:
            stage = self.pool.get('hr.recruitment.stage').browse(cr, uid, vals['stage_id'], context=context)
            self.message_append_note(cr, uid, ids, body=_("Stage changed to <b>%s</b>.") % stage.name, context=context)
        return super(hr_applicant,self).write(cr, uid, ids, vals, context=context)

    # -------------------------------------------------------
    # OpenChatter methods and notifications
    # -------------------------------------------------------
    
    def message_get_subscribers(self, cr, uid, ids, context=None):
        sub_ids = self.message_get_subscribers_ids(cr, uid, ids, context=context);
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.user_id:
                sub_ids.append(obj.user_id.id)
        return self.pool.get('res.users').read(cr, uid, sub_ids, context=context)

    def get_needaction_user_ids(self, cr, uid, ids, context=None):
        result = dict.fromkeys(ids, [])
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.state == 'draft' and obj.user_id:
                result[obj.id] = [obj.user_id.id]
        return result
    
    def case_get_note_msg_prefix(self, cr, uid, id, context=None):
		return 'Applicant'

    def case_open_send_note(self, cr, uid, ids, context=None):
        message = _("Applicant has been set <b>in progress</b>.")
        return self.message_append_note(cr, uid, ids, body=message, context=context)

    def case_close_send_note(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for applicant in self.browse(cr, uid, ids, context=context):
            if applicant.emp_id:
                message = _("Applicant has been <b>hired</b> and created as an employee.")
                self.message_append_note(cr, uid, [applicant.id], body=message, context=context)
            else:
                message = _("Applicant has been <b>hired</b>.")
                self.message_append_note(cr, uid, [applicant.id], body=message, context=context)
        return True

    def case_cancel_send_note(self, cr, uid, ids, context=None):
        msg = 'Applicant <b>refused</b>.'
        return self.message_append_note(cr, uid, ids, body=msg, context=context)

    def case_reset_send_note(self,  cr, uid, ids, context=None):
        message =_("Applicant has been set as <b>new</b>.")
        return self.message_append_note(cr, uid, ids, body=message, context=context)

    def create_send_note(self, cr, uid, ids, context=None):
        message = _("Applicant has been <b>created</b>.")
        return self.message_append_note(cr, uid, ids, body=message, context=context)

hr_applicant()

class hr_job(osv.osv):
    _inherit = "hr.job"
    _name = "hr.job"
    _columns = {
        'survey_id': fields.many2one('survey', 'Interview Form', help="Choose an interview form for this job position and you will be able to print/answer this interview from all applicants who apply for this job"),
    }
hr_job()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
