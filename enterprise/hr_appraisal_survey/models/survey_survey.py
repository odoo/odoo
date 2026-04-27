# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from werkzeug.urls import url_encode

class SurveySurvey(models.Model):
    _inherit = 'survey.survey'

    survey_type = fields.Selection(selection_add=[('appraisal', 'Appraisal')], ondelete={'appraisal': 'set default'})
    appraisal_manager_user_ids = fields.Many2many(
        'res.users', relation='survey_survey_res_users_appraisal_rel', string='Appraisals Managers Users',
        compute='_compute_appraisal_manager_user_ids', store=True, readonly=True,
        help='Users allowed to view the survey used in an appraisal')

    @api.onchange('survey_type')
    def _onchange_survey_type(self):
        super()._onchange_survey_type()
        if self.survey_type == 'appraisal':
            self.write({
                'access_mode': 'token',
                'is_attempts_limited': True,
                'users_can_go_back': True,
            })

    @api.depends('survey_type')
    @api.depends_context('uid')
    def _compute_allowed_survey_types(self):
        super()._compute_allowed_survey_types()
        if self.env.user.has_group('hr_appraisal.group_hr_appraisal_user') or \
                self.env.user.has_group('survey.group_survey_user'):
            self.allowed_survey_types = (self.allowed_survey_types or []) + ['appraisal']

    @api.depends('survey_type', 'user_input_ids', 'user_input_ids.appraisal_id', 'user_input_ids.appraisal_id.manager_ids')
    def _compute_appraisal_manager_user_ids(self):
        appraisal_surveys = self.filtered(lambda s: s.survey_type == 'appraisal' and s.user_input_ids)
        (self - appraisal_surveys).appraisal_manager_user_ids = False
        for survey in appraisal_surveys:
            survey.appraisal_manager_user_ids = survey.user_input_ids.appraisal_id.manager_ids.user_id

    def action_open_all_survey_inputs(self):
        return {
            'type': 'ir.actions.act_url',
            'name': _("Survey Feedback"),
            'target': 'self',
            'url': '/appraisal/%s/results/' % (self.id)
        }

    def action_survey_user_input_completed(self):
        action = super().action_survey_user_input_completed()
        if self.survey_type == 'appraisal':
            action.update({
                'domain': [('survey_id.survey_type', '=', 'appraisal')]
            })
        return action

    def action_survey_user_input(self):
        action = super().action_survey_user_input()
        if self.survey_type == 'appraisal':
            action.update({
                'domain': [('survey_id.survey_type', '=', 'appraisal')]
            })
        return action

    def get_formview_id(self, access_uid=None):
        if self.survey_type == 'appraisal':
            access_user = self.env['res.users'].browse(access_uid) if access_uid else self.env.user
            if not access_user.has_group('survey.group_survey_user'):
                if view := self.env.ref('hr_appraisal_survey.survey_survey_view_form', raise_if_not_found=False):
                    return view.id
        return super().get_formview_id(access_uid=access_uid)


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    appraisal_id = fields.Many2one('hr.appraisal', index='btree_not_null')
    requested_by = fields.Many2one(related="create_uid.partner_id", string='Requested by')

    def action_open_survey_inputs(self):
        self.ensure_one()
        return {
            'name': _("Survey Feedback"),
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': '/survey/print/%s?%s' %
                   (self.survey_id.access_token, url_encode({"answer_token": self.access_token, "review": True}))
        }

    def action_open_all_survey_inputs(self):
        return {
            'type': 'ir.actions.act_url',
            'name': _("Survey Feedback"),
            'target': 'new',
            'url': '/survey/results/%s?%s' %
                   (self.survey_id[0].id, url_encode({"appraisal_id": self.appraisal_id.id}))
        }

    def action_ask_feedback(self):
        if len(self.appraisal_id) > 1:
            raise ValidationError("You can't selected feedback linked to multiples appraisals.")
        if len(self.survey_id) > 1:
            raise ValidationError("You can't selected multiple feedback template.")
        appraisal_id = self.appraisal_id
        set_emails = set(self.mapped('email'))
        if appraisal_id.employee_feedback_ids:
            employee_ids = appraisal_id.employee_feedback_ids.filtered(
                lambda e: e.work_email in set_emails or\
                    e.user_id.partner_id.email in set_emails).ids
        else:
            employee_ids = []
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'appraisal.ask.feedback',
            'target': 'new',
            'name': 'Ask Feedback',
            'context': {
                'default_appraisal_id': appraisal_id.id,
                'default_employee_ids': employee_ids,
                'default_survey_template_id': self.survey_id.id
            }
        }

    def _mark_done(self):
        self.appraisal_id._notify_answer_360_feedback()
        return super()._mark_done()

class SurveyQuestionAnswer(models.Model):
    _inherit = 'survey.question.answer'

    survey_id = fields.Many2one('survey.survey', related='question_id.survey_id')
