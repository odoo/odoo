# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_nbr_of_answers = fields.Boolean('Answers')
    kpi_nbr_of_answers_value = fields.Integer(compute='_compute_kpi_nbr_of_answers_value')
    kpi_nbr_of_certified_participants = fields.Boolean('Certified Participants')
    kpi_nbr_of_certified_participants_value = fields.Integer(
        compute='_compute_kpi_nbr_of_certified_participants_value'
    )

    def _compute_kpi_nbr_of_answers_value(self):
        self._ensure_user_has_one_of_the_group('survey.group_survey_manager')
        self._calculate_cross_company_kpi(
            'survey.user_input',
            digest_kpi_field='kpi_nbr_of_answers_value')

    def _compute_kpi_nbr_of_certified_participants_value(self):
        self._ensure_user_has_one_of_the_group('survey.group_survey_manager')
        self._calculate_cross_company_kpi(
            'survey.user_input',
            digest_kpi_field='kpi_nbr_of_certified_participants_value',
            date_field='end_datetime',
            additional_domain=[('scoring_success', '=', True), ('survey_id.certification', '=', True)])

    def _compute_kpis_actions(self, company, user):
        res = super()._compute_kpis_actions(company, user)
        menu_root_id = self.env.ref('survey.menu_surveys').id
        res['kpi_nbr_of_answers'] = f'survey.action_survey_user_input&menu_id={menu_root_id}'
        res['kpi_nbr_of_certified_participants'] = f'survey.action_survey_user_input_certified&menu_id={menu_root_id}'
        return res
