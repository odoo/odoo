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
        self._raise_if_not_member_of('im_livechat.im_livechat_group_manager')
        start, end, __ = self._get_kpi_compute_parameters()
        domain = [
            ("channel_type", "=", "livechat"),
            ("livechat_rating", "!=", False),
            ("create_date", ">=", start),
            ("create_date", "<", end),
        ]
        count_by_rating = dict(
            self.env["discuss.channel"]._read_group(
                domain,
                ["livechat_rating"],
                ["__count"],
            )
        )
        total_count = sum(count_by_rating.values())
        if not total_count:
            self.kpi_livechat_rating_value = 0
            return
        rating_to_percentage = self.env["discuss.channel"]._rating_selection_to_percentage
        total_sum = sum(
            rating_to_percentage(rating) * count for rating, count in count_by_rating.items()
        )
        self.kpi_livechat_rating_value = total_sum / total_count

    def _compute_kpi_livechat_conversations_value(self):
        self._raise_if_not_member_of('im_livechat.im_livechat_group_manager')
        start, end, __ = self._get_kpi_compute_parameters()
        self.kpi_livechat_conversations_value = self.env['discuss.channel'].search_count([
            ('channel_type', '=', 'livechat'),
            ('create_date', '>=', start), ('create_date', '<', end),
        ])

    def _compute_kpi_livechat_response_value(self):
        self._raise_if_not_member_of('im_livechat.im_livechat_group_manager')
        start, end, __ = self._get_kpi_compute_parameters()
        response_time = self.env['im_livechat.report.channel'].sudo()._read_group([
            ('start_date', '>=', start),
            ('start_date', '<', end),
        ], [], ['time_to_answer:avg'])
        self.kpi_livechat_response_value = response_time[0][0]

    def _get_kpi_custom_settings(self, company, user):
        res = super()._get_kpi_custom_settings(company, user)
        res['kpi_action']['kpi_livechat_conversations'] = 'im_livechat.im_livechat_report_channel_action'
        res['kpi_action']['kpi_livechat_response'] = 'im_livechat.im_livechat_report_channel_time_to_answer_action'
        res['is_cross_company'].update(('kpi_livechat_rating', 'kpi_livechat_conversations', 'kpi_livechat_response'))
        res['kpi_sequence']['kpi_livechat_rating'] = 9500
        res['kpi_sequence']['kpi_livechat_conversations'] = 9505
        res['kpi_sequence']['kpi_livechat_response'] = 9510
        return res
