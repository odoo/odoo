# -
#   I check that state of "Employee Evaluation" survey is Open.
# -
#   !assert {model: survey.survey, id: appraisal_form, severity: error, string: Survey should be in 'open' state}:
#     - state == 'open'
# -
#   I start the evaluation process by click on "Start Evaluation" button.
# -
#   !python {model: hr_evaluation.evaluation}: |
#      self.button_plan_in_progress(cr, uid, [ref('hr_evaluation_evaluation_0')])
# -
#   I check that state is "Plan in progress".
# -
#   !assert {model: hr_evaluation.evaluation, id: hr_evaluation_evaluation_0, severity: error, string: Evaluation should be 'Plan in progress' state}:
#     - state == 'wait'
# -
#   I find a mistake on evaluation form. So I cancel the evaluation and again start it.
# -
#   !python {model: hr_evaluation.evaluation}: |
#     evaluation = self.browse(cr, uid, ref('hr_evaluation_evaluation_0') , context)
#     self.button_cancel(cr, uid, [ref('hr_evaluation_evaluation_0')])
#     assert evaluation.state == 'cancel', 'Evaluation should be in cancel state'
#     self.button_draft(cr, uid, [ref('hr_evaluation_evaluation_0')])
#     evaluation = self.browse(cr, uid, ref('hr_evaluation_evaluation_0') , context)
#     assert evaluation.state == 'draft', 'Evaluation should be in draft state'
#     self.button_plan_in_progress(cr, uid, [ref('hr_evaluation_evaluation_0')])
# -
#   I check that state is "Plan in progress" and "Interview Request" record is created
# -
#   !python {model: hr_evaluation.evaluation}: |
#     interview_obj = self.pool.get('hr.evaluation.interview')
#     evaluation = self.browse(cr, uid, ref('hr_evaluation_evaluation_0') , context)
#     assert evaluation.state == 'wait', "Evaluation should be 'Plan in progress' state"
#     interview_ids = interview_obj.search(cr, uid, [('evaluation_id','=', ref('hr_evaluation_evaluation_0'))])
#     assert len(interview_ids), "Interview evaluation survey not created"
# -
#   Give answer of the first page in "Employee Evaluation" survey.
# -
#   !python {model: survey.question.wiz}: |
#     name_wiz_obj=self.pool.get('survey.name.wiz')
#     interview_obj = self.pool.get('hr.evaluation.interview')
#     interview_ids = interview_obj.search(cr, uid, [('evaluation_id','=', ref('hr_evaluation_evaluation_0'))])
#     assert len(interview_ids), "Interview evaluation survey not created"
#     ctx = {'active_model':'hr.evaluation.interview', 'active_id': interview_ids[0], 'active_ids': [interview_ids], 'survey_id': ref("survey_2")}
#     name_id = name_wiz_obj.create(cr, uid, {'survey_id': ref("survey_2")})
#     ctx ["sur_name_id"] = name_id
#     self.create(cr, uid, {str(ref("survey_question_2")) +"_" +str(ref("survey_answer_1")) + "_multi" :'tpa',
#                 str(ref("survey_question_2")) +"_" +str(ref("survey_answer_10")) + "_multi" :'application eng',
#                 str(ref("survey_question_2")) +"_" +str(ref("survey_answer_20")) + "_multi" :'3',
#                 str(ref("survey_question_2")) +"_" +str(ref("survey_answer_25")) + "_multi" :'2011-12-02 16:42:00',
#                 str(ref("survey_question_2")) +"_" +str(ref("survey_answer_43")) + "_multi" :'HR',
#                 }, context = ctx)
# -
#   I close this Evaluation survey by giving answer of questions.
# -
#   !python {model: hr_evaluation.evaluation}: |
#     interview_obj = self.pool.get('hr.evaluation.interview')
#     evaluation = self.browse(cr, uid, ref('hr_evaluation_evaluation_0'))
#     interview_obj.survey_req_done(cr, uid, [r.id for r in evaluation.survey_request_ids])
#     for survey in evaluation.survey_request_ids:
#       interview = interview_obj.browse(cr, uid, survey.id, context)
#       assert interview.state == "done", 'survey must be in done state'
# -
#   I print the evaluation.
# -
#   !python {model: hr_evaluation.evaluation}: |
#     evaluation = self.browse(cr, uid, ref('hr_evaluation_evaluation_0'))
#     self.pool.get('hr.evaluation.interview').action_print_survey(cr, uid, [r.id for r in evaluation.survey_request_ids])
# -
#   I click on "Final Validation" button to finalise evaluation.
# -
#   !python {model: hr_evaluation.evaluation}: |
#     self.button_final_validation(cr, uid, [ref("hr_evaluation_evaluation_0")])
# -
#   I check that state is "Waiting Appreciation".
# -
#   !assert {model: hr_evaluation.evaluation, id: hr_evaluation_evaluation_0}:
#       - state == 'progress'
# -
#   Give Rating "Meet expectations" by selecting overall Rating.
# -
#   !record {model: hr_evaluation.evaluation, id: hr_evaluation_evaluation_0}:
#     rating: '2'
# -
#   I close this Evaluation by click on "Done" button of this wizard.
# -
#   !python {model: hr_evaluation.evaluation}: |
#     self.button_done(cr, uid, [ref("hr_evaluation_evaluation_0")])
# -
#   I check that state of Evaluation is done.
# -
#   !assert {model: hr_evaluation.evaluation, id: hr_evaluation_evaluation_0, severity: error, string: Evaluation should be in done state}:
#       - state == 'done'
# -
#   Print Evaluations Statistics Report
# -
#   !python {model: hr.evaluation.report}: |
#     import os, time
#     from openerp import tools
#     ctx={}
#     data_dict={'state': 'done', 'rating': 2, 'employee_id': ref("hr.employee_fp")}
#     from openerp.tools import test_reports
#     test_reports.try_report_action(cr, uid, 'hr_evaluation_evaluation_0',wiz_data=data_dict, context=ctx, our_module='hr_evaluation')
