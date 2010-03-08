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
from osv import fields, osv
from mx import DateTime as dt
import tools
from tools.translate import _

class hr_evaluation_plan(osv.osv):
    _name = "hr_evaluation.plan"
    _description = "Evaluation Plan"
    _columns = {
        'name': fields.char("Evaluation Plan", size=64, required=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'phase_ids' : fields.one2many('hr_evaluation.plan.phase', 'plan_id', 'Evaluation Phases'),
        'month_first': fields.integer('First Evaluation After'),
        'month_next': fields.integer('Next Evaluation After'),
        'active': fields.boolean('Active')
    }
    _defaults = {
        'active' : lambda *a: True,
    }
hr_evaluation_plan()

class hr_evaluation_plan_phase(osv.osv):
    _name = "hr_evaluation.plan.phase"
    _description = "Evaluation Plan Phase"
    _order = "sequence"
    _columns = {
        'name': fields.char("Phase", size=64, required=True),
        'sequence': fields.integer("Sequence"),
        'company_id': fields.related('plan_id','company_id',type='many2one',relation='res.company',string='Company',store=True),
        'plan_id': fields.many2one('hr_evaluation.plan','Evaluation Plan', required=True, ondelete='cascade'),
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
            help="Check this box if you want to wait that all preceeding phases " +
              "are finished before launching this phase.")

    }
    _defaults = {
        'sequence' : lambda *a: 1,
    }
hr_evaluation_plan_phase()

class hr_employee(osv.osv):
    _inherit="hr.employee"
    _columns = {
        'evaluation_plan_id': fields.many2one('hr_evaluation.plan', 'Evaluation Plan'),
        'evaluation_date': fields.date('Next Evaluation', help="Date of the next evaluation"),
    }

    def onchange_evaluation_plan_id(self,cr,uid,ids,evaluation_plan_id,context={}):
        evaluation_date = self.browse(cr, uid, ids)[0].evaluation_date or ''
        evaluation_plan_obj=self.pool.get('hr_evaluation.plan')
        if evaluation_plan_id:
            for evaluation_plan in evaluation_plan_obj.browse(cr,uid,[evaluation_plan_id]):
                if not evaluation_date:
                   evaluation_date=(dt.ISO.ParseAny(dt.now().strftime('%Y-%m-%d'))+ dt.RelativeDateTime(months=+evaluation_plan.month_first)).strftime('%Y-%m-%d')
                else:
                   evaluation_date=(dt.ISO.ParseAny(evaluation_date)+ dt.RelativeDateTime(months=+evaluation_plan.month_next)).strftime('%Y-%m-%d')
        return {'value': {'evaluation_date':evaluation_date}}
hr_employee()

class hr_evaluation(osv.osv):
    _name = "hr_evaluation.evaluation"
    _description = "Employee Evaluation"
    _rec_name = 'employee_id'
    _columns = {
        'date': fields.date("Evaluation Deadline", required=True),
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
        ], "Overall Rating", help="This is the overall rating on that summarize the evaluation"),
        'survey_request_ids': fields.one2many('hr.evaluation.interview','evaluation_id','Appraisal Forms'),
        'plan_id': fields.many2one('hr_evaluation.plan', 'Plan', required=True),
        'state': fields.selection([
            ('draft','Draft'),
            ('wait','Plan In Progress'),
            ('progress','Final Validation'),
            ('done','Done'),
            ('cancel','Cancelled'),
        ], 'State', required=True,readonly=True),
        'date_close': fields.date('Ending Date'),
        'progress' : fields.float("Progress"),
    }
    _defaults = {
        'date' : lambda *a: (dt.ISO.ParseAny(dt.now().strftime('%Y-%m-%d')) + dt.RelativeDateTime(months =+ 1)).strftime('%Y-%m-%d'),
        'state' : lambda *a: 'draft',
    }

    def onchange_employee_id(self,cr,uid,ids,employee_id,context={}):
        employee_obj=self.pool.get('hr.employee')
        evaluation_plan_id=''
        if employee_id:
            for employee in employee_obj.browse(cr,uid,[employee_id]):
                if employee and employee.evaluation_plan_id and employee.evaluation_plan_id.id:
                    evaluation_plan_id=employee.evaluation_plan_id.id
                employee_ids=employee_obj.search(cr,uid,[('parent_id','=',employee.id)])
        return {'value': {'plan_id':evaluation_plan_id}}

    def button_plan_in_progress(self,cr, uid, ids, context):
        employee_obj = self.pool.get('hr.employee')
        hr_eval_inter_obj = self.pool.get('hr.evaluation.interview')
        survey_request_obj = self.pool.get('survey.request')
        curr_employee=self.browse(cr,uid, ids)[0].employee_id
        child_employees=employee_obj.browse(cr,uid, employee_obj.search(cr,uid,[('parent_id','=',curr_employee.id)]))
        manager_employee=curr_employee.parent_id
        for evaluation in self.browse(cr,uid,ids):
            if evaluation and evaluation.plan_id:
                apprai_id = []
                for phase in evaluation.plan_id.phase_ids:
                    if phase.action == "bottom-up":
                        for child in child_employees:
                            if child.user_id:
                                user = child.user_id.id
                            id = hr_eval_inter_obj.create(cr, uid, {'evaluation_id':evaluation.id ,'user_id' : user,'survey_id' : phase.survey_id.id, 'user_to_review_id' : child.id, 'date_deadline' :(dt.ISO.ParseAny(dt.now().strftime('%Y-%m-%d')) + dt.RelativeDateTime(months =+ 1)).strftime('%Y-%m-%d')})
                            if not phase.wait:
                                hr_eval_inter_obj.survey_req_waiting_answer(cr, uid, [id], context)
                            apprai_id.append(id)
                    elif phase.action == "top-down":
                        if manager_employee:
                            user = False
                            if manager_employee.user_id:
                                user = manager_employee.user_id.id
                            id = hr_eval_inter_obj.create(cr, uid, {'evaluation_id':evaluation.id,'user_id': user ,'survey_id' : phase.survey_id.id, 'user_to_review_id' :manager_employee.id, 'date_deadline' :(dt.ISO.ParseAny(dt.now().strftime('%Y-%m-%d')) + dt.RelativeDateTime(months =+ 1)).strftime('%Y-%m-%d')})
                            if not phase.wait:
                                hr_eval_inter_obj.survey_req_waiting_answer(cr, uid, [id], context)
                            apprai_id.append(id)
                    elif phase.action == "self":
                        if curr_employee:
                            user = False
                            if curr_employee.user_id:
                                user = curr_employee.user_id.id
                            id = hr_eval_inter_obj.create(cr, uid, {'evaluation_id':evaluation.id,'user_id' : user, 'survey_id' : phase.survey_id.id, 'user_to_review_id' :curr_employee.id, 'date_deadline' :(dt.ISO.ParseAny(dt.now().strftime('%Y-%m-%d')) + dt.RelativeDateTime(months =+ 1)).strftime('%Y-%m-%d')})
                            if not phase.wait:
                                hr_eval_inter_obj.survey_req_waiting_answer(cr, uid, [id], context)
                            apprai_id.append(id)
                    elif phase.action == "final":
                        if manager_employee:
                            user = False
                            if manager_employee.user_id:
                                user = manager_employee.user_id.id
                            id = hr_eval_inter_obj.create(cr, uid, {'evaluation_id':evaluation.id,'user_id' : user, 'survey_id' : phase.survey_id.id, 'user_to_review_id' :manager_employee.id, 'date_deadline' :(dt.ISO.ParseAny(dt.now().strftime('%Y-%m-%d')) + dt.RelativeDateTime(months =+ 1)).strftime('%Y-%m-%d')})
                            if not phase.wait:
                                hr_eval_inter_obj.survey_req_waiting_answer(cr, uid, [id], context)
                            apprai_id.append(id)
                self.write(cr, uid, evaluation.id, {'survey_request_ids':[[6, 0, apprai_id]]})
        self.write(cr,uid,ids,{'state':'wait'})
        return True

    def button_final_validation(self,cr, uid, ids, context):
        self.write(cr,uid,ids,{'state':'progress'})
        request_obj = self.pool.get('hr.evaluation.interview')
        for id in self.browse(cr, uid ,ids):
            if len(id.survey_request_ids) != len(request_obj.search(cr, uid, [('evaluation_id', '=', id.id),('state', '=', 'done')])):
                raise osv.except_osv(_('Warning !'),_("You cannot change state, because some appraisal in waiting answer or draft state"))
        return True

    def button_done(self,cr, uid, ids, context):
        self.write(cr,uid,ids,{'state':'done', 'date_close': time.strftime('%Y-%m-%d')})
        return True

    def button_cancel(self,cr, uid, ids, context):
        self.write(cr,uid,ids,{'state':'cancel'})
        return True

hr_evaluation()

class survey_request(osv.osv):
    _inherit="survey.request"
    _columns = {
        'is_evaluation':fields.boolean('Is Evaluation?'),
    }
survey_request()

class hr_evaluation_interview(osv.osv):
    _name='hr.evaluation.interview'
    _inherits={'survey.request':'request_id'}
    _description='Evaluation Interview'
    _columns = {

        'request_id': fields.many2one('survey.request','Request_id', ondelete='cascade'),
        'user_to_review_id': fields.many2one('hr.employee', 'Employee'),
        'evaluation_id' : fields.many2one('hr_evaluation.evaluation', 'Evaluation'),
        }
    _defaults = {
        'is_evaluation': lambda *a: True,
        }

    def survey_req_waiting_answer(self, cr, uid, ids, context):
        self.write(cr, uid, ids, { 'state' : 'waiting_answer'})
#        for id in self.browse(cr, uid, ids):
#            if id.user_id and id.user_id.address_id and id.user_id.address_id and id.user_id.address_id.email:
#                msg = " Hello %s, \n\n We are inviting you for %s survey. \n\n Thanks,"  %(id.user_id.name, id.survey_id.title)
#                tools.email_send(tools.config['email_from'], [id.user_id.address_id.email],\
#                                              'Invite to fill up Survey', msg)
        return True

    def survey_req_done(self, cr, uid, ids, context):
        self.write(cr, uid, ids, { 'state' : 'done'})
        hr_eval_obj = self.pool.get('hr_evaluation.evaluation')
        for id in self.browse(cr, uid, ids):
            flag = False
            wating_id = 0
            tot_done_req = 0
            records = self.pool.get("hr_evaluation.evaluation").browse(cr, uid, [id.evaluation_id.id])[0].survey_request_ids
            for child in records:
                if child.state == "draft" :
                    wating_id = child.id
                    continue
                if child.state != "done":
                    flag = True
                else :
                    tot_done_req += 1
            if not flag and wating_id:
                self.survey_req_waiting_answer(cr, uid, [wating_id], context)
            hr_eval_obj.write(cr, uid, [id.evaluation_id.id], {'progress' :tot_done_req * 100 / len(records)})

        return True
    def survey_req_draft(self, cr, uid, ids, arg):
        self.write(cr, uid, ids, { 'state' : 'draft'})
        return True

    def survey_req_cancel(self, cr, uid, ids, context):
        self.write(cr, uid, ids, { 'state' : 'cancel'})
        return True

hr_evaluation_interview()