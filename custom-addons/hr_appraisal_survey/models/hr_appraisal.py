# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _, api


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
            'view_mode': 'tree',
            'res_model': 'survey.user_input',
            'target': 'current',
            'name': _('Feedback Surveys'),
            'views': [[view_id.id, 'tree']],
            'domain': [('appraisal_id', '=', self.id)]
        }

    def action_open_all_survey_inputs(self):
        return {
            'type': 'ir.actions.act_url',
            'name': _("Survey Feedback"),
            'target': 'self',
            'url': '/appraisal/%s/results/' % (self.id)
        }
