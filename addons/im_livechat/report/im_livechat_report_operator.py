# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class Im_LivechatReportOperator(models.Model):
    """ Livechat Support Report on the Operator """

    _name = 'im_livechat.report.operator'
    _description = "Livechat Support Operator Report"
    _order = 'livechat_channel_id, partner_id'
    _auto = False

    partner_id = fields.Many2one('res.partner', 'Operator', readonly=True)
    livechat_channel_id = fields.Many2one('im_livechat.channel', 'Channel', readonly=True)
    nbr_channel = fields.Integer('# of Sessions', readonly=True, aggregator="sum")
    channel_id = fields.Many2one('discuss.channel', 'Conversation', readonly=True)
    start_date = fields.Datetime('Start Date of session', readonly=True)
    time_to_answer = fields.Float('Time to answer', digits=(16, 2), readonly=True, aggregator="avg", help="Average time to give the first answer to the visitor")
    duration = fields.Float('Average duration', digits=(16, 2), readonly=True, aggregator="avg", help="Duration of the conversation (in seconds)")
    rating = fields.Float('Average rating', readonly=True, aggregator="avg", help="Average rating given by the visitor")

    def init(self):
        # Note : start_date_hour must be remove when the read_group will allow grouping on the hour of a datetime. Don't forget to change the view !
        tools.drop_view_if_exists(self.env.cr, 'im_livechat_report_operator')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW im_livechat_report_operator AS (
                SELECT
                    row_number() OVER () AS id,
                    C.livechat_operator_id AS partner_id,
                    C.livechat_channel_id AS livechat_channel_id,
                    COUNT(DISTINCT C.id) AS nbr_channel,
                    C.id AS channel_id,
                    C.create_date AS start_date,
                    C.rating_last_value as rating,
                    EXTRACT('epoch' FROM MAX(M.create_date) - MIN(M.create_date)) AS duration,
                    EXTRACT('epoch' FROM MIN(MO.create_date) - MIN(M.create_date)) AS time_to_answer
                FROM discuss_channel C
                    JOIN mail_message M ON M.res_id = C.id AND M.model = 'discuss.channel'
                    LEFT JOIN mail_message MO ON (MO.res_id = C.id AND MO.model = 'discuss.channel' AND MO.author_id = C.livechat_operator_id)
                WHERE C.livechat_channel_id IS NOT NULL
                GROUP BY C.id, C.livechat_operator_id
            )
        """)
