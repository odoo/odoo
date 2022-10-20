# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_nbr_of_answers = fields.Boolean('# Answers')
    kpi_nbr_of_answers_value = fields.Integer(compute='_compute_kpi_nbr_of_answers_value')
    kpi_nbr_of_certified_participants = fields.Boolean('# Certified Participants')
    kpi_nbr_of_certified_participants_value = fields.Integer(
        compute='_compute_kpi_nbr_of_certified_participants_value'
    )

    def _compute_kpi_nbr_of_answers_value(self):
        for record in self:
            start, end, _ = record._get_kpi_compute_parameters()
            record.kpi_nbr_of_answers_value = self.env['survey.user_input'].search_count([
                ('create_date', '>=', start),
                ('create_date', '<', end)
            ])

    def _compute_kpi_nbr_of_certified_participants_value(self):
        for record in self:
            start, end, _ = record._get_kpi_compute_parameters()
            record.kpi_nbr_of_certified_participants_value = self.env['survey.user_input'].search_count([
                ('end_datetime', '>=', start),
                ('end_datetime', '<', end),
                ('scoring_success', '=', True),
                ('survey_id.certification', '=', True),
            ])

    def _compute_kpis_actions(self, company, user):
        res = super(Digest, self)._compute_kpis_actions(company, user)
        res['kpi_nbr_of_answers'] = 'survey.action_survey_user_input'
        res['kpi_nbr_of_certified_participants'] = 'survey.action_show_certified_participants'
        return res
