from odoo import api, fields, models


class SurveySurvey(models.Model):
    _inherit = "survey.survey"

    lead_count = fields.Integer("# Leads", compute='_compute_lead_count')

    @api.depends('lead_count')
    def _compute_lead_count(self):
        for survey in self:
            domain = [('survey_id', 'in', survey.ids)]
            leads = self.env['crm.lead'].search_count(domain)
            survey.lead_count = leads

    def action_survey_user_input_leads(self):
        """This method will show the leads created from the current survey"""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("crm.crm_lead_all_leads")
        action['domain'] = [('survey_id', 'in', self.ids)]
        action['context'] = dict(self._context, create=False)
        return action

    def action_end_session(self):
        """ Checks if a lead needs to be created for sessions in live """
        super().action_end_session()

        if self.survey_type in ['live_session', 'custom']:
            for survey in self:
                user_inputs = self.env['survey.user_input'].search([
                    ('survey_id', '=', survey.id),
                    ('is_session_answer', '=', True),
                    ('state', '=', 'done'),
                    ('create_date', '>=', survey.session_start_time),
                ])
                for user_input in user_inputs:
                    user_input._lead_qualification_check()
