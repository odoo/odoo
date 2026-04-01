# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class DigestDigest(models.Model):
    _inherit = 'digest.digest'

    kpi_livechat_rating = fields.Boolean('% of Happiness')
    kpi_livechat_rating_value = fields.Float(digits=(16, 2), compute='_compute_kpi_livechat_rating_value')
    kpi_livechat_conversations = fields.Boolean('Conversations handled')
    kpi_livechat_conversations_value = fields.Integer(compute='_compute_kpi_livechat_conversations_value')
    kpi_livechat_response = fields.Boolean('Time to answer (sec)')
    kpi_livechat_response_value = fields.Float(digits=(16, 2), compute='_compute_kpi_livechat_response_value')

    def _compute_kpi_livechat_rating_value(self):
        channels = self.env['discuss.channel'].search([('channel_type', '=', 'livechat')])
        start, end, __ = self._get_kpi_compute_parameters()
        domain = [
            ('create_date', '>=', start),
            ('create_date', '<', end),
        ]
        ratings = channels.rating_get_grades(domain)
        self.kpi_livechat_rating_value = (
            ratings['great'] * 100 / sum(ratings.values())
            if sum(ratings.values()) else 0
        )

    def _compute_kpi_livechat_conversations_value(self):
        start, end, __ = self._get_kpi_compute_parameters()
        self.kpi_livechat_conversations_value = self.env['discuss.channel'].search_count([
            ('channel_type', '=', 'livechat'),
            ('create_date', '>=', start), ('create_date', '<', end),
        ])

    def _compute_kpi_livechat_response_value(self):
        start, end, __ = self._get_kpi_compute_parameters()
        response_time = self.env['im_livechat.report.channel'].sudo()._read_group([
            ('start_date', '>=', start),
            ('start_date', '<', end),
        ], [], ['time_to_answer:avg'])
        self.kpi_livechat_response_value = response_time[0][0]

    def _compute_kpis_actions(self, company, user):
        res = super()._compute_kpis_actions(company, user)
        res['kpi_livechat_conversations'] = 'im_livechat.im_livechat_report_operator_action'
        res['kpi_livechat_response'] = 'im_livechat.im_livechat_report_channel_time_to_answer_action'
        return res
