# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class ImLivechatReportChannel(models.Model):
    """ Livechat Support Report on the Channels """

    _name = "im_livechat.report.channel"
    _description = "Livechat Support Channel Report"
    _order = 'start_date, technical_name'
    _auto = False

    uuid = fields.Char('UUID', readonly=True)
    channel_id = fields.Many2one('discuss.channel', 'Conversation', readonly=True)
    channel_name = fields.Char('Channel Name', readonly=True)
    technical_name = fields.Char('Code', readonly=True)
    livechat_channel_id = fields.Many2one('im_livechat.channel', 'Channel', readonly=True)
    start_date = fields.Datetime('Start Date of session', readonly=True)
    start_hour = fields.Char('Start Hour of session', readonly=True)
    day_number = fields.Char('Day Number', readonly=True, help="1 is Monday, 7 is Sunday")
    time_to_answer = fields.Float('Time to answer (sec)', digits=(16, 2), readonly=True, group_operator="avg", help="Average time in seconds to give the first answer to the visitor")
    start_date_hour = fields.Char('Hour of start Date of session', readonly=True)
    duration = fields.Float('Average duration', digits=(16, 2), readonly=True, group_operator="avg", help="Duration of the conversation (in seconds)")
    nbr_speaker = fields.Integer('# of speakers', readonly=True, group_operator="avg", help="Number of different speakers")
    nbr_message = fields.Integer('Average message', readonly=True, group_operator="avg", help="Number of message in the conversation")
    is_without_answer = fields.Integer('Session(s) without answer', readonly=True, group_operator="sum",
                                       help="""A session is without answer if the operator did not answer. 
                                       If the visitor is also the operator, the session will always be answered.""")
    days_of_activity = fields.Integer('Days of activity', group_operator="max", readonly=True, help="Number of days since the first session of the operator")
    is_anonymous = fields.Integer('Is visitor anonymous', readonly=True)
    country_id = fields.Many2one('res.country', 'Country of the visitor', readonly=True)
    is_happy = fields.Integer('Visitor is Happy', readonly=True)
    rating = fields.Integer('Rating', group_operator="avg", readonly=True)
    # TODO DBE : Use Selection field - Need : Pie chart must show labels, not keys.
    rating_text = fields.Char('Satisfaction Rate', readonly=True)
    is_unrated = fields.Integer('Session not rated', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Operator', readonly=True)

    def init(self):
        # Note : start_date_hour must be remove when the read_group will allow grouping on the hour of a datetime. Don't forget to change the view !
        tools.drop_view_if_exists(self.env.cr, 'im_livechat_report_channel')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW im_livechat_report_channel AS (
                SELECT
                    C.id as id,
                    C.uuid as uuid,
                    C.id as channel_id,
                    C.name as channel_name,
                    CONCAT(L.name, ' / ', C.id) as technical_name,
                    C.livechat_channel_id as livechat_channel_id,
                    C.create_date as start_date,
                    to_char(date_trunc('hour', C.create_date), 'YYYY-MM-DD HH24:MI:SS') as start_date_hour,
                    to_char(date_trunc('hour', C.create_date), 'HH24') as start_hour,
                    extract(dow from  C.create_date) as day_number, 
                    EXTRACT('epoch' FROM MAX(M.create_date) - MIN(M.create_date)) AS duration,
                    EXTRACT('epoch' FROM MIN(MO.create_date) - MIN(M.create_date)) AS time_to_answer,
                    count(distinct C.livechat_operator_id) as nbr_speaker,
                    count(distinct M.id) as nbr_message,
                    CASE 
                        WHEN EXISTS (select distinct M.author_id FROM mail_message M
                                        WHERE M.author_id=C.livechat_operator_id
                                        AND M.res_id = C.id
                                        AND M.model = 'discuss.channel'
                                        AND C.livechat_operator_id = M.author_id)
                        THEN 0
                        ELSE 1
                    END as is_without_answer,
                    (DATE_PART('day', date_trunc('day', now()) - date_trunc('day', C.create_date)) + 1) as days_of_activity,
                    CASE
                        WHEN C.anonymous_name IS NULL THEN 0
                        ELSE 1
                    END as is_anonymous,
                    C.country_id,
                    CASE 
                        WHEN rate.rating = 5 THEN 1
                        ELSE 0
                    END as is_happy,
                    Rate.rating as rating,
                    CASE
                        WHEN Rate.rating = 1 THEN 'Unhappy'
                        WHEN Rate.rating = 5 THEN 'Happy'
                        WHEN Rate.rating = 3 THEN 'Neutral'
                        ELSE null
                    END as rating_text,
                    CASE 
                        WHEN rate.rating > 0 THEN 0
                        ELSE 1
                    END as is_unrated,
                    C.livechat_operator_id as partner_id
                FROM discuss_channel C
                    JOIN mail_message M ON (M.res_id = C.id AND M.model = 'discuss.channel')
                    JOIN im_livechat_channel L ON (L.id = C.livechat_channel_id)
                    LEFT JOIN mail_message MO ON (MO.res_id = C.id AND MO.model = 'discuss.channel' AND MO.author_id = C.livechat_operator_id)
                    LEFT JOIN rating_rating Rate ON (Rate.res_id = C.id and Rate.res_model = 'discuss.channel' and Rate.parent_res_model = 'im_livechat.channel')
                    WHERE C.livechat_operator_id is not null
                GROUP BY C.livechat_operator_id, C.id, C.name, C.livechat_channel_id, L.name, C.create_date, C.uuid, Rate.rating
            )
        """)
