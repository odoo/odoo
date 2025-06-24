import ast

from odoo import api, fields, models


class SurveySurvey(models.Model):
    _inherit = 'survey.survey'

    lead_count = fields.Integer('Leads', help='Number of leads created by this survey', compute='_compute_lead_count')
    lead_ids = fields.One2many('crm.lead', 'survey_id', string='Leads created by the survey')

    @api.depends('lead_ids')
    def _compute_lead_count(self):
        leads = self.env['crm.lead']._read_group(
            [('survey_id', 'in', self.ids)], ['survey_id'], ['__count'])
        leads_count_by_survey = {survey.id: count for survey, count in leads}
        for survey in self:
            survey.lead_count = leads_count_by_survey.get(survey.id, 0)

    def action_survey_leads(self):
        ''' This method will show the leads created from the current survey '''
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('crm.crm_lead_all_leads')
        action['domain'] = [('survey_id', 'in', self.ids)]
        action['context'] = dict(
            ast.literal_eval(action.get('context', '{}')),
            create=False
        )
        return action

    def action_end_session(self):
        ''' Checks if leads need to be created for live sessions (either custom or live_session) '''
        super().action_end_session()

        user_inputs = self.user_input_ids.filtered(
            lambda user_input: user_input.create_date >= self.session_start_time)
        user_inputs._create_leads_if_generative_answers()
