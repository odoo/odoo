# -*- encoding: utf-8 -*-
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

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil import parser
import time

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DF


class hr_evaluation_plan(osv.Model):
    _name = "hr_evaluation.plan"
    _description = "Appraisal Plan"
    _columns = {
        'name': fields.char("Appraisal Plan", required=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'phase_ids': fields.one2many('hr_evaluation.plan.phase', 'plan_id', 'Appraisal Phases', copy=True),
        'month_first': fields.integer('First Appraisal in (months)', help="This number of months will be used to schedule the first evaluation date of the employee when selecting an evaluation plan. "),
        'month_next': fields.integer('Periodicity of Appraisal (months)', help="The number of month that depicts the delay between each evaluation of this plan (after the first one)."),
        'active': fields.boolean('Active')
    }
    _defaults = {
        'active': True,
        'month_first': 6,
        'month_next': 12,
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'account.account', context=c),
    }


class hr_evaluation_plan_phase(osv.Model):
    _name = "hr_evaluation.plan.phase"
    _description = "Appraisal Plan Phase"
    _order = "sequence"
    _columns = {
        'name': fields.char("Phase", size=64, required=True),
        'sequence': fields.integer("Sequence"),
        'company_id': fields.related('plan_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
        'plan_id': fields.many2one('hr_evaluation.plan', 'Appraisal Plan', ondelete='cascade'),
        'action': fields.selection([
            ('top-down', 'Top-Down Appraisal Requests'),
            ('bottom-up', 'Bottom-Up Appraisal Requests'),
            ('self', 'Self Appraisal Requests'),
            ('final', 'Final Interview')], 'Action', required=True),
        'survey_id': fields.many2one('survey.survey', 'Appraisal Form', required=True),
        'send_answer_manager': fields.boolean('All Answers',
            help="Send all answers to the manager"),
        'send_answer_employee': fields.boolean('All Answers',
            help="Send all answers to the employee"),
        'send_anonymous_manager': fields.boolean('Anonymous Summary',
            help="Send an anonymous summary to the manager"),
        'send_anonymous_employee': fields.boolean('Anonymous Summary',
            help="Send an anonymous summary to the employee"),
        'wait': fields.boolean('Wait Previous Phases',
            help="Check this box if you want to wait that all preceding phases " +
              "are finished before launching this phase."),
        'mail_feature': fields.boolean('Send mail for this phase', help="Check this box if you want to send mail to employees coming under this phase"),
        'mail_body': fields.text('Email'),
        'email_subject': fields.text('Subject')
    }
    _defaults = {
        'sequence': 1,
        'email_subject': _('''Regarding '''),
        'mail_body': lambda *a: _('''
Date: %(date)s

Dear %(employee_name)s,

I am doing an evaluation regarding %(eval_name)s.

Kindly submit your response.


Thanks,
--
%(user_signature)s

        '''),
    }


class hr_employee(osv.Model):
    _name = "hr.employee"
    _inherit="hr.employee"
    
    def _appraisal_count(self, cr, uid, ids, field_name, arg, context=None):
        Evaluation = self.pool['hr.evaluation.interview']
        return {
            employee_id: Evaluation.search_count(cr, uid, [('user_to_review_id', '=', employee_id)], context=context)
            for employee_id in ids
        }

    _columns = {
        'evaluation_plan_id': fields.many2one('hr_evaluation.plan', 'Appraisal Plan'),
        'evaluation_date': fields.date('Next Appraisal Date', help="The date of the next appraisal is computed by the appraisal plan's dates (first appraisal + periodicity)."),
        'appraisal_count': fields.function(_appraisal_count, type='integer', string='Appraisal Interviews'),
    }

    def run_employee_evaluation(self, cr, uid, automatic=False, use_new_cursor=False, context=None):  # cronjob
        now = parser.parse(datetime.now().strftime('%Y-%m-%d'))
        obj_evaluation = self.pool.get('hr_evaluation.evaluation')
        emp_ids = self.search(cr, uid, [('evaluation_plan_id', '<>', False), ('evaluation_date', '=', False)], context=context)
        for emp in self.browse(cr, uid, emp_ids, context=context):
            first_date = (now + relativedelta(months=emp.evaluation_plan_id.month_first)).strftime('%Y-%m-%d')
            self.write(cr, uid, [emp.id], {'evaluation_date': first_date}, context=context)

        emp_ids = self.search(cr, uid, [('evaluation_plan_id', '<>', False), ('evaluation_date', '<=', time.strftime("%Y-%m-%d"))], context=context)
        for emp in self.browse(cr, uid, emp_ids, context=context):
            next_date = (now + relativedelta(months=emp.evaluation_plan_id.month_next)).strftime('%Y-%m-%d')
            self.write(cr, uid, [emp.id], {'evaluation_date': next_date}, context=context)
            plan_id = obj_evaluation.create(cr, uid, {'employee_id': emp.id, 'plan_id': emp.evaluation_plan_id.id}, context=context)
            obj_evaluation.button_plan_in_progress(cr, uid, [plan_id], context=context)
        return True


class hr_evaluation(osv.Model):
    _name = "hr_evaluation.evaluation"
    _inherit = "mail.thread"
    _description = "Employee Appraisal"
    _columns = {
        'date': fields.date("Appraisal Deadline", required=True, select=True),
        'employee_id': fields.many2one('hr.employee', "Employee", required=True),
        'note_summary': fields.text('Appraisal Summary'),
        'note_action': fields.text('Action Plan', help="If the evaluation does not meet the expectations, you can propose an action plan"),
        'rating': fields.selection([
            ('0', 'Significantly below expectations'),
            ('1', 'Do not meet expectations'),
            ('2', 'Meet expectations'),
            ('3', 'Exceeds expectations'),
            ('4', 'Significantly exceeds expectations'),
        ], "Appreciation", help="This is the appreciation on which the evaluation is summarized."),
        'survey_request_ids': fields.one2many('hr.evaluation.interview', 'evaluation_id', 'Appraisal Forms'),
        'plan_id': fields.many2one('hr_evaluation.plan', 'Plan', required=True),
        'state': fields.selection([
            ('draft', 'New'),
            ('cancel', 'Cancelled'),
            ('wait', 'Plan In Progress'),
            ('progress', 'Waiting Appreciation'),
            ('done', 'Done'),
        ], 'Status', required=True, readonly=True, copy=False),
        'date_close': fields.date('Ending Date', select=True),
    }
    _defaults = {
        'date': lambda *a: (parser.parse(datetime.now().strftime('%Y-%m-%d')) + relativedelta(months=+1)).strftime('%Y-%m-%d'),
        'state': lambda *a: 'draft',
    }

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        for record in reads:
            name = record.plan_id.name
            employee = record.employee_id.name_related
            res.append((record['id'], name + ' / ' + employee))
        return res

    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        vals = {}
        vals['plan_id'] = False
        if employee_id:
            employee_obj = self.pool.get('hr.employee')
            for employee in employee_obj.browse(cr, uid, [employee_id], context=context):
                if employee and employee.evaluation_plan_id and employee.evaluation_plan_id.id:
                    vals.update({'plan_id': employee.evaluation_plan_id.id})
        return {'value': vals}

    def button_plan_in_progress(self, cr, uid, ids, context=None):
        hr_eval_inter_obj = self.pool.get('hr.evaluation.interview')
        if context is None:
            context = {}
        for evaluation in self.browse(cr, uid, ids, context=context):
            wait = False
            for phase in evaluation.plan_id.phase_ids:
                children = []
                if phase.action == "bottom-up":
                    children = evaluation.employee_id.child_ids
                elif phase.action in ("top-down", "final"):
                    if evaluation.employee_id.parent_id:
                        children = [evaluation.employee_id.parent_id]
                elif phase.action == "self":
                    children = [evaluation.employee_id]
                for child in children:

                    int_id = hr_eval_inter_obj.create(cr, uid, {
                        'evaluation_id': evaluation.id,
                        'phase_id': phase.id,
                        'deadline': (parser.parse(datetime.now().strftime('%Y-%m-%d')) + relativedelta(months=+1)).strftime('%Y-%m-%d'),
                        'user_id': child.user_id.id,
                    }, context=context)
                    if phase.wait:
                        wait = True
                    if not wait:
                        hr_eval_inter_obj.survey_req_waiting_answer(cr, uid, [int_id], context=context)

                    if (not wait) and phase.mail_feature:
                        body = phase.mail_body % {'employee_name': child.name, 'user_signature': child.user_id.signature,
                            'eval_name': phase.survey_id.title, 'date': time.strftime('%Y-%m-%d'), 'time': time}
                        sub = phase.email_subject
                        if child.work_email:
                            vals = {'state': 'outgoing',
                                    'subject': sub,
                                    'body_html': '<pre>%s</pre>' % body,
                                    'email_to': child.work_email,
                                    'email_from': evaluation.employee_id.work_email}
                            self.pool.get('mail.mail').create(cr, uid, vals, context=context)

        self.write(cr, uid, ids, {'state': 'wait'}, context=context)
        return True

    def button_final_validation(self, cr, uid, ids, context=None):
        request_obj = self.pool.get('hr.evaluation.interview')
        self.write(cr, uid, ids, {'state': 'progress'}, context=context)
        for evaluation in self.browse(cr, uid, ids, context=context):
            if evaluation.employee_id and evaluation.employee_id.parent_id and evaluation.employee_id.parent_id.user_id:
                self.message_subscribe_users(cr, uid, [evaluation.id], user_ids=[evaluation.employee_id.parent_id.user_id.id], context=context)
            if len(evaluation.survey_request_ids) != len(request_obj.search(cr, uid, [('evaluation_id', '=', evaluation.id), ('state', 'in', ['done', 'cancel'])], context=context)):
                raise osv.except_osv(_('Warning!'), _("You cannot change state, because some appraisal forms have not been completed."))
        return True

    def button_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'done', 'date_close': time.strftime('%Y-%m-%d')}, context=context)
        return True

    def button_cancel(self, cr, uid, ids, context=None):
        interview_obj = self.pool.get('hr.evaluation.interview')
        evaluation = self.browse(cr, uid, ids[0], context)
        interview_obj.survey_req_cancel(cr, uid, [r.id for r in evaluation.survey_request_ids])
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        return True

    def button_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'draft'}, context=context)
        return True

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('employee_id'):
            employee_id = self.pool.get('hr.employee').browse(cr, uid, vals.get('employee_id'), context=context)
            if employee_id.parent_id and employee_id.parent_id.user_id:
                vals['message_follower_ids'] = [(4, employee_id.parent_id.user_id.partner_id.id)]
        if 'date' in vals:
            new_vals = {'deadline': vals.get('date')}
            obj_hr_eval_iterview = self.pool.get('hr.evaluation.interview')
            for evaluation in self.browse(cr, uid, ids, context=context):
                for survey_req in evaluation.survey_request_ids:
                    obj_hr_eval_iterview.write(cr, uid, [survey_req.id], new_vals, context=context)
        return super(hr_evaluation, self).write(cr, uid, ids, vals, context=context)


class hr_evaluation_interview(osv.Model):
    _name = 'hr.evaluation.interview'
    _inherit = 'mail.thread'
    _rec_name = 'user_to_review_id'
    _description = 'Appraisal Interview'
    _columns = {
        'request_id': fields.many2one('survey.user_input', 'Survey Request', ondelete='cascade', readonly=True),
        'evaluation_id': fields.many2one('hr_evaluation.evaluation', 'Appraisal Plan', required=True),
        'phase_id': fields.many2one('hr_evaluation.plan.phase', 'Appraisal Phase', required=True),
        'user_to_review_id': fields.related('evaluation_id', 'employee_id', type="many2one", relation="hr.employee", string="Employee to evaluate"),
        'user_id': fields.many2one('res.users', 'Interviewer'),
        'state': fields.selection([('draft', "Draft"),
                                   ('waiting_answer', "In progress"),
                                   ('done', "Done"),
                                   ('cancel', "Cancelled")],
                                  string="State", required=True, copy=False),
        'survey_id': fields.related('phase_id', 'survey_id', string="Appraisal Form", type="many2one", relation="survey.survey"),
        'deadline': fields.related('request_id', 'deadline', type="datetime", string="Deadline"),
    }
    _defaults = {
        'state': 'draft'
    }

    def create(self, cr, uid, vals, context=None):
        phase_obj = self.pool.get('hr_evaluation.plan.phase')
        survey_id = phase_obj.read(cr, uid, vals.get('phase_id'), fields=['survey_id'], context=context)['survey_id'][0]

        if vals.get('user_id'):
            user_obj = self.pool.get('res.users')
            partner_id = user_obj.read(cr, uid, vals.get('user_id'), fields=['partner_id'], context=context)['partner_id'][0]
        else:
            partner_id = None

        user_input_obj = self.pool.get('survey.user_input')

        if not vals.get('deadline'):
            vals['deadline'] = (datetime.now() + timedelta(days=28)).strftime(DF)

        ret = user_input_obj.create(cr, uid, {'survey_id': survey_id,
                                              'deadline': vals.get('deadline'),
                                              'type': 'link',
                                              'partner_id': partner_id}, context=context)
        vals['request_id'] = ret
        return super(hr_evaluation_interview, self).create(cr, uid, vals, context=context)

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        for record in reads:
            name = record.survey_id.title
            res.append((record['id'], name))
        return res

    def survey_req_waiting_answer(self, cr, uid, ids, context=None):
        request_obj = self.pool.get('survey.user_input')
        for interview in self.browse(cr, uid, ids, context=context):
            request_obj.action_survey_resent(cr, uid, [interview.id], context=context)
            self.write(cr, uid, interview.id, {'state': 'waiting_answer'}, context=context)
        return True

    def survey_req_done(self, cr, uid, ids, context=None):
        for id in self.browse(cr, uid, ids, context=context):
            flag = False
            wating_id = 0
            if not id.evaluation_id.id:
                raise osv.except_osv(_('Warning!'), _("You cannot start evaluation without Appraisal."))
            records = id.evaluation_id.survey_request_ids
            for child in records:
                if child.state == "draft":
                    wating_id = child.id
                    continue
                if child.state != "done":
                    flag = True
            if not flag and wating_id:
                self.survey_req_waiting_answer(cr, uid, [wating_id], context=context)
        self.write(cr, uid, ids, {'state': 'done'}, context=context)
        return True

    def survey_req_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        return True

    def action_print_survey(self, cr, uid, ids, context=None):
        """ If response is available then print this response otherwise print survey form (print template of the survey) """
        context = dict(context or {})
        interview = self.browse(cr, uid, ids, context=context)[0]
        survey_obj = self.pool.get('survey.survey')
        response_obj = self.pool.get('survey.user_input')
        response = response_obj.browse(cr, uid, interview.request_id.id, context=context)
        context.update({'survey_token': response.token})
        return survey_obj.action_print_survey(cr, uid, [interview.survey_id.id], context=context)

    def action_start_survey(self, cr, uid, ids, context=None):
        context = dict(context or {})
        interview = self.browse(cr, uid, ids, context=context)[0]
        survey_obj = self.pool.get('survey.survey')
        response_obj = self.pool.get('survey.user_input')
        # grab the token of the response and start surveying
        response = response_obj.browse(cr, uid, interview.request_id.id, context=context)
        context.update({'survey_token': response.token})
        return survey_obj.action_start_survey(cr, uid, [interview.survey_id.id], context=context)
