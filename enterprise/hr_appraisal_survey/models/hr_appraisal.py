# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _, api, SUPERUSER_ID
from odoo.tools import convert


class HrAppraisal(models.Model):
    _inherit = "hr.appraisal"

    employee_feedback_ids = fields.Many2many('hr.employee', string="Asked Feedback")
    survey_ids = fields.Many2many('survey.survey', help="Sent out surveys")
    completed_survey_count = fields.Integer(compute="_compute_completed_survey_count")
    total_survey_count = fields.Integer(compute="_compute_total_survey_count")

    @api.depends('survey_ids', 'survey_ids.user_input_ids.state')
    def _compute_completed_survey_count(self):
        grouped_data = self.env['survey.user_input']._read_group(
            domain=[('state', '=', 'done'), ('appraisal_id', 'in', self.ids)],
            groupby=['appraisal_id'],
            aggregates=['__count'])
        mapped_data = dict(grouped_data)

        for appraisal in self:
            appraisal.completed_survey_count = mapped_data.get(appraisal, 0)

    @api.depends('survey_ids')
    def _compute_total_survey_count(self):
        grouped_data = self.env['survey.user_input']._read_group(
            domain=[('appraisal_id', 'in', self.ids)],
            groupby=['appraisal_id'],
            aggregates=['__count'])
        mapped_data = dict(grouped_data)

        for appraisal in self:
            appraisal.total_survey_count = mapped_data.get(appraisal, 0)

    def action_ask_feedback(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'appraisal.ask.feedback',
            'target': 'new',
            'name': _('Ask Feedback'),
        }

    def action_open_survey_inputs(self):
        self.ensure_one()
        view_id = self.env.ref('hr_appraisal_survey.hr_appraisal_survey_user_input_view_tree', raise_if_not_found=False)
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'list',
            'res_model': 'survey.user_input',
            'target': 'current',
            'name': _('Feedback Surveys'),
            'views': [[view_id.id, 'list']],
            'domain': [('appraisal_id', '=', self.id)]
        }

    def action_open_all_survey_inputs(self):
        return {
            'type': 'ir.actions.act_url',
            'name': _("Survey Feedback"),
            'target': 'self',
            'url': '/appraisal/%s/results/' % (self.id)
        }

    def _notify_answer_360_feedback(self):
        for appraisal in self.with_user(SUPERUSER_ID):
            body = _('A new 360 Feedback report has been completed for the appraisal of %(employee_name)s.', employee_name=appraisal.employee_id.name)
            appraisal.message_post(body=body, subtype_xmlid='hr_appraisal_survey.mt_360_feedback')

    def _load_demo_data(self):
        super()._load_demo_data()
        convert.convert_file(self.env, 'hr_appraisal_survey', 'data/scenarios/scenario_appraisal_demo.xml', None, mode='init',
        kind='data')
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
