import ast

from odoo import api, fields, models


class SurveySurvey(models.Model):
    _inherit = 'survey.survey'

    generate_lead = fields.Boolean('Lead Generating', compute='_compute_generate_lead', store="True")
    lead_count = fields.Integer('Leads', help='Number of leads created by this survey', compute='_compute_lead_count')
    team_id = fields.Many2one(
        'crm.team', string='Assign Leads to',
        index='btree_not_null', ondelete='set null')  # If a submission generates an opportunity, this sales team will be associated with it

    @api.depends('survey_type', 'question_ids')
    def _compute_generate_lead(self):
        for survey in self:
            survey.generate_lead = survey.survey_type in ['survey', 'live_session', 'custom'] and \
                                   any(question_id.generate_lead for question_id in survey.question_ids)

    def _compute_lead_count(self):
        lead_data = self.env['crm.lead'].sudo()._read_group(
            [('utm_reference', 'in', [f'{survey._name},{survey.id}' for survey in self])],
            ['utm_reference'], ['__count'],
        )
        mapped_data = dict(lead_data)
        for survey in self:
            survey.lead_count = mapped_data.get(f'{survey._name},{survey.id}', 0)

    def action_end_session(self):
        ''' Checks if leads need to be created for live sessions (either custom or live_session) '''
        super().action_end_session()

        user_inputs = self.user_input_ids.filtered(
            lambda user_input: user_input.create_date >= self.session_start_time)
        user_inputs._create_leads_from_generative_answers()

    def action_survey_see_leads(self):
        ''' Shows the leads created from the current survey '''
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('crm.crm_lead_all_leads')
        action['context'] = dict(
            ast.literal_eval(action.get('context', '{}').strip()),  # ".strip()" prevents a crash of literal_eval which doesn't interpret the "\n" after the dictionary is closed in the string
            create=False,
        )
        action['domain'] = [(
            'utm_reference',
            'in',
            [f'{survey._name},{survey.id}' for survey in self]
        )]
        return action
