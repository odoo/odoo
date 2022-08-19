# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_livechat_rating = fields.Boolean('% of Happiness')
    kpi_livechat_rating_value = fields.Float(digits=(16, 2), compute='_compute_kpi_livechat_rating_value')
    kpi_livechat_conversations = fields.Boolean('Conversations handled')
    kpi_livechat_conversations_value = fields.Integer(compute='_compute_kpi_livechat_conversations_value')
    kpi_livechat_response = fields.Boolean('Time to answer(sec)', help="Time to answer the user in second.")
    kpi_livechat_response_value = fields.Float(digits=(16, 2), compute='_compute_kpi_livechat_response_value')

    def _compute_kpi_livechat_rating_value(self):
        channels = self.env['mail.channel'].search([('livechat_operator_id', '=', self.env.user.partner_id.id)])
        for record in self:
            start, end, company = record._get_kpi_compute_parameters()
            domain = [
                ('create_date', '>=', start), ('create_date', '<', end),
                ('rated_partner_id', '=', self.env.user.partner_id.id)
            ]
            ratings = channels.rating_get_grades(domain)
            record.kpi_livechat_rating_value = ratings['great'] * 100 / sum(ratings.values()) if sum(ratings.values()) else 0

    def _compute_kpi_livechat_conversations_value(self):
        for record in self:
            start, end, company = record._get_kpi_compute_parameters()
            record.kpi_livechat_conversations_value = self.env['mail.channel'].search_count([
                ('channel_type', '=', 'livechat'),
                ('livechat_operator_id', '=', self.env.user.partner_id.id),
                ('create_date', '>=', start), ('create_date', '<', end)
            ])

    def _compute_kpi_livechat_response_value(self):
        for record in self:
            start, end, company = record._get_kpi_compute_parameters()
            response_time = self.env['im_livechat.report.operator'].sudo().read_group([
                ('start_date', '>=', start), ('start_date', '<', end),
                ('partner_id', '=', self.env.user.partner_id.id)], ['partner_id', 'time_to_answer'], ['partner_id'])
            record.kpi_livechat_response_value = sum(
                response['time_to_answer']
                for response in response_time
                if response['time_to_answer'] > 0
            )

    def _compute_kpis_actions(self, company, user):
        res = super(Digest, self)._compute_kpis_actions(company, user)
        res['kpi_livechat_rating'] = 'im_livechat.rating_rating_action_livechat_report'
        res['kpi_livechat_conversations'] = 'im_livechat.im_livechat_report_operator_action'
        res['kpi_livechat_response'] = 'im_livechat.im_livechat_report_channel_time_to_answer_action'
        return res
