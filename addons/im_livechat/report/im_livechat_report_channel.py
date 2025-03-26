# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
from odoo.tools import SQL


class Im_LivechatReportChannel(models.Model):
    """ Livechat Support Report on the Channels """

    _name = 'im_livechat.report.channel'
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
    time_to_answer = fields.Float('Time to answer (sec)', digits=(16, 2), readonly=True, aggregator="avg", help="Average time in seconds to give the first answer to the visitor")
    start_date_hour = fields.Char('Hour of start Date of session', readonly=True)
    duration = fields.Float('Session Duration (minutes)', digits=(16, 2), readonly=True, aggregator="avg", help="Duration of the conversation (in minutes)")
    nbr_speaker = fields.Integer('# of speakers', readonly=True, aggregator="avg", help="Number of different speakers")
    nbr_channel = fields.Integer("# of Sessions", readonly=True, aggregator="sum")
    nbr_message = fields.Integer('Average message', readonly=True, aggregator="avg", help="Number of message in the conversation")
    is_without_answer = fields.Integer('Session(s) without answer', readonly=True, aggregator="sum",
                                       help="""A session is without answer if the operator did not answer. 
                                       If the visitor is also the operator, the session will always be answered.""")
    days_of_activity = fields.Integer('Days of activity', aggregator="max", readonly=True, help="Number of days since the first session of the operator")
    is_anonymous = fields.Integer('Is visitor anonymous', readonly=True)
    country_id = fields.Many2one('res.country', 'Country of the visitor', readonly=True)
    is_happy = fields.Integer('Visitor is Happy', readonly=True)
    rating = fields.Integer('Rating', aggregator="avg", readonly=True)
    # TODO DBE : Use Selection field - Need : Pie chart must show labels, not keys.
    rating_text = fields.Char('Satisfaction Rate', readonly=True)
    day_name = fields.Char('Day Name', help="Day of the Week", readonly=True)
    is_unrated = fields.Integer('Session not rated', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Operator', readonly=True)
    chatbot_partner_id = fields.Many2one('res.partner', string="Bot Operator", readonly=True)
    visitor_partner_id = fields.Many2one('res.partner', string="Visitor Partner", readonly=True)
    res_user_settings_id = fields.Many2one('res.users.settings', help="Settings related to the User")
    operator_expertise_id = fields.Many2many(related="res_user_settings_id.livechat_expertise_ids")
    chatbot_answer = fields.Char('Chatbot Answer path', readonly=True)
    partner_name = fields.Char(related="partner_id.name")

    def init(self):
        # Note : start_date_hour must be remove when the read_group will allow grouping on the hour of a datetime. Don't forget to change the view !
        tools.drop_view_if_exists(self.env.cr, 'im_livechat_report_channel')
        self.env.cr.execute(
            SQL("CREATE OR REPLACE VIEW im_livechat_report_channel AS (%s)",
            self._query()
        ))

    def _query(self) -> SQL:
        return SQL("%s %s %s", self._select(), self._from(), self._group_by())

    def _select(self) -> SQL:
        return SQL(
            """
            SELECT
                C.id as id,
                C.uuid as uuid,
                C.id as channel_id,
                C.name as channel_name,
                COUNT(DISTINCT C.id) AS nbr_channel,
                USS.res_user_settings_id AS res_user_settings_id,
                CONCAT(L.name, ' / ', C.id) as technical_name,
                C.livechat_channel_id as livechat_channel_id,
                C.create_date as start_date,
                to_char(date_trunc('hour', C.create_date), 'YYYY-MM-DD HH24:MI:SS') as start_date_hour,
                to_char(date_trunc('hour', C.create_date), 'HH24') as start_hour,
                extract(dow from  C.create_date) as day_number,
                CR.script_operator_partner_id AS chatbot_partner_id,
                V.visitor_partner_id,
                answers_path.chatbot_answer AS chatbot_answer,
                CASE
                    WHEN extract(dow from C.create_date) = 1 THEN 'Monday'
                    WHEN extract(dow from C.create_date) = 2 THEN 'Tuesday'
                    WHEN extract(dow from C.create_date) = 3 THEN 'Wednesday'
                    WHEN extract(dow from C.create_date) = 4 THEN 'Thursday'
                    WHEN extract(dow from C.create_date) = 5 THEN 'Friday'
                    WHEN extract(dow from C.create_date) = 6 THEN 'Saturday'
                    WHEN extract(dow from C.create_date) = 0 THEN 'Sunday'
                END as day_name,
                EXTRACT('epoch' FROM MAX(M.create_date) - MIN(M.create_date))/60 AS duration,
                EXTRACT('epoch' FROM MIN(MO.create_date) - MIN(M.create_date)) AS time_to_answer,
                count(distinct C.livechat_operator_id) as nbr_speaker,
                count(distinct M.id) as nbr_message,
                count(distinct DCM.partner_id) as member_count,
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
            """,
        )

    def _from(self) -> SQL:
        return SQL(
            """
            FROM discuss_channel C
                JOIN mail_message M ON (M.res_id = C.id AND M.model = 'discuss.channel')
                JOIN im_livechat_channel L ON (L.id = C.livechat_channel_id)
                LEFT JOIN mail_message MO ON (MO.res_id = C.id AND MO.model = 'discuss.channel' AND MO.author_id = C.livechat_operator_id)
                LEFT JOIN rating_rating Rate ON (Rate.res_id = C.id and Rate.res_model = 'discuss.channel' and Rate.parent_res_model = 'im_livechat.channel')
                LEFT JOIN discuss_channel_member DCM ON DCM.channel_id = C.id
                LEFT JOIN res_users U ON U.partner_id = C.livechat_operator_id
                LEFT JOIN LATERAL (
                    SELECT STRING_AGG(SA.name->>'en_US', ' > ' ORDER BY M.create_date) AS chatbot_answer
                      FROM chatbot_message CM
                      JOIN chatbot_script_answer SA ON SA.id = CM.user_script_answer_id
                      JOIN mail_message M ON M.id = CM.mail_message_id
                     WHERE CM.discuss_channel_id = C.id
                ) AS answers_path ON TRUE
                LEFT JOIN LATERAL (
                    SELECT US.id AS res_user_settings_id
                      FROM res_users_settings US
                     WHERE US.user_id = U.id
                     ORDER BY US.id ASC
                     LIMIT 1
                ) USS ON TRUE
                LEFT JOIN (
                    SELECT rule.channel_id, script.operator_partner_id AS script_operator_partner_id
                      FROM im_livechat_channel_rule rule
                      JOIN chatbot_script script ON script.id = rule.chatbot_script_id
                     WHERE rule.chatbot_script_id IS NOT NULL
                ) CR ON CR.channel_id = C.livechat_channel_id
                LEFT JOIN LATERAL (
                    SELECT DCM.partner_id AS visitor_partner_id
                      FROM discuss_channel_member DCM
                     WHERE DCM.channel_id = C.id
                       AND DCM.partner_id IS NOT NULL
                       AND DCM.partner_id != C.livechat_operator_id
                     ORDER BY DCM.id ASC
                     LIMIT 1
                ) V ON TRUE
            """,
        )

    def _group_by(self) -> SQL:
        return SQL(
            """
            GROUP BY
                C.id,
                C.uuid,
                C.create_date,
                C.livechat_operator_id,
                C.livechat_channel_id,
                C.name,
                CR.script_operator_partner_id,
                answers_path.chatbot_answer,
                L.name,
                Rate.rating,
                USS.res_user_settings_id,
                V.visitor_partner_id
            """,
        )
