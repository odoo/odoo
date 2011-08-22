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

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil import parser
from osv import fields, osv
from tools.translate import _

class hr_evaluation_plan(osv.osv):
    _name = "hr_evaluation.plan"
    _description = "Evaluation Plan"
    _columns = {
        'name': fields.char("Evaluation Plan", size=64, required=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'phase_ids': fields.one2many('hr_evaluation.plan.phase', 'plan_id', 'Evaluation Phases'),
        'month_first': fields.integer('First Evaluation in (months)', help="This number of months will be used to schedule the first evaluation date of the employee when selecting an evaluation plan. "),
        'month_next': fields.integer('Periodicity of Evaluations (months)', help="The number of month that depicts the delay between each evaluation of this plan (after the first one)."),
        'active': fields.boolean('Active')
    }
    _defaults = {
        'active': True,
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'account.account', context=c),
    }
hr_evaluation_plan()

class hr_evaluation_plan_phase(osv.osv):
    _name = "hr_evaluation.plan.phase"
    _description = "Evaluation Plan Phase"
    _order = "sequence"
    _columns = {
        'name': fields.char("Phase", size=64, required=True),
        'sequence': fields.integer("Sequence"),
        'company_id': fields.related('plan_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
        'plan_id': fields.many2one('hr_evaluation.plan','Evaluation Plan', ondelete='cascade'),
        'action': fields.selection([
            ('top-down','Top-Down Appraisal Requests'),
            ('bottom-up','Bottom-Up Appraisal Requests'),
            ('self','Self Appraisal Requests'),
            ('final','Final Interview')], 'Action', required=True),
        'survey_id': fields.many2one('survey','Appraisal Form',required=True),
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
        'mail_feature': fields.boolean('Send mail for this phase', help="Check this box if you want to send mail to employees"+
                                       " coming under this phase"),
        'mail_body': fields.text('Email'),
        'email_subject':fields.text('char')
    }
    _defaults = {
        'sequence': 1,
        'email_subject': _('''Regarding '''),
        'mail_body': lambda *a:_('''
Date: %(date)s

Dear %(employee_name)s,

I am doing an evaluation regarding %(eval_name)s.

Kindly submit your response.


Thanks,
--
%(user_signature)s

        '''),
    }
hr_evaluation_plan_phase()

class hr_employee(osv.osv):
    _name = "hr.employee"
    _inherit="hr.employee"
    _columns = {
        'evaluation_plan_id': fields.many2one('hr_evaluation.plan', 'Evaluation Plan'),
        'evaluation_date': fields.date('Next Evaluation Date', help="The date of the next evaluation is computed by the evaluation plan's dates (first evaluation + periodicity)."),
    }

    def run_employee_evaluation(self, cr, uid, automatic=False, use_new_cursor=False, context=None):
        obj_evaluation = self.pool.get('hr_evaluation.evaluation')
        for id in self.browse(cr, uid, self.search(cr, uid, [], context=context), context=context):
            if id.evaluation_plan_id and id.evaluation_date:
                if (parser.parse(id.evaluation_date) + relativedelta(months = int(id.evaluation_plan_id.month_next))).strftime('%Y-%m-%d') <= time.strftime("%Y-%m-%d"):
                    self.write(cr, uid, id.id, {'evaluation_date': (parser.parse(id.evaluation_date) + relativedelta(months =+ int(id.evaluation_plan_id.month_next))).strftime('%Y-%m-%d')}, context=context)
                    obj_evaluation.create(cr, uid, {'employee_id': id.id, 'plan_id': id.evaluation_plan_id}, context=context)
        return True

    def onchange_evaluation_plan_id(self, cr, uid, ids, evaluation_plan_id, evaluation_date, context=None):
        if evaluation_plan_id:
            evaluation_plan_obj=self.pool.get('hr_evaluation.plan')
            obj_evaluation = self.pool.get('hr_evaluation.evaluation')
            flag = False
            evaluation_plan =  evaluation_plan_obj.browse(cr, uid, [evaluation_plan_id], context=context)[0]
            if not evaluation_date:
               evaluation_date=(parser.parse(datetime.now().strftime('%Y-%m-%d'))+ relativedelta(months=+evaluation_plan.month_first)).strftime('%Y-%m-%d')
               flag = True
            else:
                if (parser.parse(evaluation_date) + relativedelta(months = int(evaluation_plan.month_next))).strftime('%Y-%m-%d') <= time.strftime("%Y-%m-%d"):
                    evaluation_date=(parser.parse(evaluation_date)+ relativedelta(months=+evaluation_plan.month_next)).strftime('%Y-%m-%d')
                    flag = True
            if ids and flag:
                obj_evaluation.create(cr, uid, {'employee_id': ids[0], 'plan_id': evaluation_plan_id}, context=context)
        return {'value': {'evaluation_date': evaluation_date}}

    def create(self, cr, uid, vals, context=None):
        id = super(hr_employee, self).create(cr, uid, vals, context=context)
        if vals.get('evaluation_plan_id', False):
            self.pool.get('hr_evaluation.evaluation').create(cr, uid, {'employee_id': id, 'plan_id': vals['evaluation_plan_id']}, context=context)
        return id

hr_employee()

class hr_evaluation(osv.osv):
    _name = "hr_evaluation.evaluation"
    _description = "Employee Evaluation"
    _rec_name = 'employee_id'
    _columns = {
        'date': fields.date("Evaluation Deadline", required=True, select=True),
        'employee_id': fields.many2one('hr.employee', "Employee", required=True),
        'note_summary': fields.text('Evaluation Summary'),
        'note_action': fields.text('Action Plan',
            help="If the evaluation does not meet the expectations, you can propose"+
              "an action plan"),
        'rating': fields.selection([
            ('0','Significantly bellow expectations'),
            ('1','Did not meet expectations'),
            ('2','Meet expectations'),
            ('3','Exceeds expectations'),
            ('4','Significantly exceeds expectations'),
        ], "Appreciation", help="This is the appreciation on that summarize the evaluation"),
        'survey_request_ids': fields.one2many('hr.evaluation.interview','evaluation_id','Appraisal Forms'),
        'plan_id': fields.many2one('hr_evaluation.plan', 'Plan', required=True),
        'state': fields.selection([
            ('draft','Draft'),
            ('wait','Plan In Progress'),
            ('progress','Waiting Appreciation'),
            ('done','Done'),
            ('cancel','Cancelled'),
        ], 'State', required=True, readonly=True),
        'date_close': fields.date('Ending Date', select=True),
        'progress': fields.float("Progress"),
    }
    _defaults = {
        'date': lambda *a: (parser.parse(datetime.now().strftime('%Y-%m-%d')) + relativedelta(months =+ 1)).strftime('%Y-%m-%d'),
        'state': lambda *a: 'draft',
    }

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        for record in reads:
            name = record.plan_id.name
            res.append((record['id'], name))
        return res

    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        evaluation_plan_id=False
        if employee_id:
            employee_obj=self.pool.get('hr.employee')
            for employee in employee_obj.browse(cr, uid, [employee_id], context=context):
                if employee and employee.evaluation_plan_id and employee.evaluation_plan_id.id:
                    evaluation_plan_id=employee.evaluation_plan_id.id
        return {'value': {'plan_id':evaluation_plan_id}}

    def button_plan_in_progress(self, cr, uid, ids, context=None):
        mail_message = self.pool.get('mail.message')
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
#                    if not child.user_id:
#                        continue

                    int_id = hr_eval_inter_obj.create(cr, uid, {
                        'evaluation_id': evaluation.id,
                        'survey_id': phase.survey_id.id,
                        'date_deadline': (parser.parse(datetime.now().strftime('%Y-%m-%d')) + relativedelta(months =+ 1)).strftime('%Y-%m-%d'),
                        'user_id': child.user_id.id,
                        'user_to_review_id': evaluation.employee_id.id
                    }, context=context)
                    if phase.wait:
                        wait = True
                    if not wait:
                        hr_eval_inter_obj.survey_req_waiting_answer(cr, uid, [int_id], context=context)

                    if (not wait) and phase.mail_feature:
                        body = phase.mail_body % {'employee_name': child.name, 'user_signature': child.user_id.signature,
                            'eval_name': phase.survey_id.title, 'date': time.strftime('%Y-%m-%d'), 'time': time }
                        sub = phase.email_subject
                        dest = [child.work_email]
                        if dest:
                           mail_message.schedule_with_attach(cr, uid, evaluation.employee_id.work_email, dest, sub, body, context=context)

        self.write(cr, uid, ids, {'state':'wait'}, context=context)
        return True

    def button_final_validation(self, cr, uid, ids, context=None):
        request_obj = self.pool.get('hr.evaluation.interview')
        self.write(cr, uid, ids, {'state':'progress'}, context=context)
        for id in self.browse(cr, uid, ids, context=context):
            if len(id.survey_request_ids) != len(request_obj.search(cr, uid, [('evaluation_id', '=', id.id),('state', '=', 'done')], context=context)):
                raise osv.except_osv(_('Warning !'),_("You cannot change state, because some appraisal in waiting answer or draft state"))
        return True

    def button_done(self,cr, uid, ids, context=None):
        self.write(cr, uid, ids,{'progress': 1 * 100}, context=context)
        self.write(cr, uid, ids,{'state':'done', 'date_close': time.strftime('%Y-%m-%d')}, context=context)
        return True

    def button_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids,{'state':'cancel'}, context=context)
        return True

    def button_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids,{'state': 'draft'}, context=context)
        return True

    def write(self, cr, uid, ids, vals, context=None):
        if 'date' in vals:
            new_vals = {'date_deadline': vals.get('date')}
            obj_hr_eval_iterview = self.pool.get('hr.evaluation.interview')
            for evalutation in self.browse(cr, uid, ids, context=context):
                for survey_req in evalutation.survey_request_ids:
                    obj_hr_eval_iterview.write(cr, uid, [survey_req.id], new_vals, context=context)
        return super(hr_evaluation, self).write(cr, uid, ids, vals, context=context)

hr_evaluation()

class survey_request(osv.osv):
    _inherit = "survey.request"
    _columns = {
        'is_evaluation': fields.boolean('Is Evaluation?'),
    }
    _defaults = {
        'state': 'waiting_answer',
    }

survey_request()

class hr_evaluation_interview(osv.osv):
    _name = 'hr.evaluation.interview'
    _inherits = {'survey.request': 'request_id'}
    _rec_name = 'request_id'
    _description = 'Evaluation Interview'
    _columns = {
        'request_id': fields.many2one('survey.request','Request_id', ondelete='cascade', required=True),
        'user_to_review_id': fields.many2one('hr.employee', 'Employee to Interview'),
        'evaluation_id': fields.many2one('hr_evaluation.evaluation', 'Evaluation Form'),
    }
    _defaults = {
        'is_evaluation': True,
    }

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        for record in reads:
            name = record.request_id.survey_id.title
            res.append((record['id'], name))
        return res

    def survey_req_waiting_answer(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, { 'state': 'waiting_answer'}, context=context)
        return True

    def survey_req_done(self, cr, uid, ids, context=None):
        hr_eval_obj = self.pool.get('hr_evaluation.evaluation')
        for id in self.browse(cr, uid, ids, context=context):
            flag = False
            wating_id = 0
            tot_done_req = 1
            if not id.evaluation_id.id:
                raise osv.except_osv(_('Warning !'),_("You cannot start evaluation without Evaluation."))
            records = hr_eval_obj.browse(cr, uid, [id.evaluation_id.id], context=context)[0].survey_request_ids
            for child in records:
                if child.state == "draft":
                    wating_id = child.id
                    continue
                if child.state != "done":
                    flag = True
                else:
                    tot_done_req += 1
            if not flag and wating_id:
                self.survey_req_waiting_answer(cr, uid, [wating_id], context=context)
            hr_eval_obj.write(cr, uid, [id.evaluation_id.id], {'progress': tot_done_req * 100 / len(records)}, context=context)
        self.write(cr, uid, ids, { 'state': 'done'}, context=context)
        return True

    def survey_req_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, { 'state': 'draft'}, context=context)
        return True

    def survey_req_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, { 'state': 'cancel'}, context=context)
        return True

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
        context.update({'survey_id': record.survey_id.id, 'response_id': [record.response.id], 'response_no':0,})
        value = self.pool.get("survey").action_print_survey(cr, uid, ids, context=context)
        return value

hr_evaluation_interview()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:1
