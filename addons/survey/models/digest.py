# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_nbr_of_answers = fields.Boolean('Participants')
    kpi_nbr_of_answers_value = fields.Integer(compute='_compute_kpi_nbr_of_answers_value')
    kpi_nbr_of_certified_participants = fields.Boolean('Certified Participants')
    kpi_nbr_of_certified_participants_value = fields.Integer(
        compute='_compute_kpi_nbr_of_certified_participants_value'
    )

    def _compute_kpi_nbr_of_answers_value(self):
        self._raise_if_not_member_of('survey.group_survey_manager')
        self._calculate_kpi(
            'survey.user_input',
            digest_kpi_field='kpi_nbr_of_answers_value',
            additional_domain=[('test_entry', '=', False)],
            is_cross_company=True,
        )

    def _compute_kpi_nbr_of_certified_participants_value(self):
        self._raise_if_not_member_of('survey.group_survey_manager')
        self._calculate_kpi(
            'survey.user_input',
            digest_kpi_field='kpi_nbr_of_certified_participants_value',
            date_field='end_datetime',
            additional_domain=[('test_entry', '=', False),
                               ('scoring_success', '=', True), ('survey_id.certification', '=', True)],
            is_cross_company=True)

    def _get_kpi_custom_settings(self, company, user):
        res = super()._get_kpi_custom_settings(company, user)
        menu_root_id = self.env.ref('survey.menu_surveys').id
        res['kpi_action']['kpi_nbr_of_answers'] = f'survey.action_survey_user_input?menu_id={menu_root_id}'
        res['kpi_action']['kpi_nbr_of_certified_participants'] = (
            f'survey.survey_user_input_action_certified?menu_id={menu_root_id}')
        res['is_cross_company'].update(('kpi_nbr_of_answers', 'kpi_nbr_of_certified_participants'))
        res['kpi_sequence']['kpi_nbr_of_answers'] = 11500
        res['kpi_sequence']['kpi_nbr_of_certified_participants'] = 11505
        return res
