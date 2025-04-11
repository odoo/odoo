# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
from odoo.tools import SQL


class Im_LivechatReportChannel(models.Model):
    """ Livechat Support Report on the Channels """

    _name = 'im_livechat.report.channel'
    _description = "Livechat Support Channel Report"
    _order = 'start_date, livechat_channel_id, channel_id'
    _auto = False

    uuid = fields.Char('UUID', readonly=True)
    channel_id = fields.Many2one('discuss.channel', 'Conversation', readonly=True)
    channel_name = fields.Char('Channel Name', readonly=True)
    livechat_channel_id = fields.Many2one('im_livechat.channel', 'Channel', readonly=True)
    start_date = fields.Datetime('Start Date of session', readonly=True)
    start_hour = fields.Char('Start Hour of session', readonly=True)
    day_number = fields.Char('Day Number', readonly=True, help="1 is Monday, 7 is Sunday")
    time_to_answer = fields.Float('Time to answer (sec)', digits=(16, 2), readonly=True, aggregator="avg", help="Average time in seconds to give the first answer to the visitor")
    start_date_hour = fields.Char('Hour of start Date of session', readonly=True)
    duration = fields.Float('Average duration', digits=(16, 2), readonly=True, aggregator="avg", help="Duration of the conversation (in minutes)")
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
    is_unrated = fields.Integer('Session not rated', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Operator', readonly=True)
    handled_by_bot = fields.Integer("Handled by Bot", readonly=True, aggregator="sum")
    handled_by_agent = fields.Integer("Handled by Agent", readonly=True, aggregator="sum")

    def init(self):
        # Note : start_date_hour must be remove when the read_group will allow grouping on the hour of a datetime. Don't forget to change the view !
        tools.drop_view_if_exists(self.env.cr, 'im_livechat_report_channel')
        self.env.cr.execute(
            SQL("CREATE OR REPLACE VIEW im_livechat_report_channel AS (%s)",
            self._query()
        ))

    def _query(self) -> SQL:
        return SQL("%s %s %s %s %s", self._cte(), self._select(), self._from(), self._where(), self._group_by())

    def _cte(self) -> SQL:
        return SQL(
            """
            WITH message_vals AS (
                SELECT m.res_id as channel_id,
                       COUNT(DISTINCT m.id) AS message_count,
                       MIN(m.create_date) FILTER (
                           WHERE m.author_id = c.livechat_operator_id
                       ) AS first_agent_message_dt_legacy,
                       MAX(m.create_date) AS last_message_dt,
                       MIN(m.create_date) FILTER (
                           WHERE h.livechat_member_type = 'agent'
                       ) AS first_agent_message_dt,
                       MAX(m.create_date) FILTER (
                           WHERE h.livechat_member_type = 'bot'
                       ) AS last_bot_message_dt
                  FROM mail_message m
                  JOIN discuss_channel c
                    ON c.id = m.res_id
                   AND m.model = 'discuss.channel'
                   AND c.channel_type = 'livechat'
             LEFT JOIN im_livechat_channel_member_history h
                    ON h.channel_id = m.res_id
                   AND m.model = 'discuss.channel'
                   AND (h.guest_id = m.author_guest_id or h.partner_id = m.author_id)
              GROUP BY m.res_id
            ),
            channel_member_history AS (
                SELECT channel_id,
                       BOOL_OR(livechat_member_type = 'agent') as has_agent,
                       BOOL_OR(livechat_member_type = 'bot') as has_bot
                  FROM im_livechat_channel_member_history
              GROUP BY channel_id
            )
            """)

    def _select(self) -> SQL:
        return SQL(
            """
            SELECT
                C.id as id,
                C.uuid as uuid,
                C.id as channel_id,
                C.name as channel_name,
                COUNT(DISTINCT C.id) AS nbr_channel,
                C.livechat_channel_id as livechat_channel_id,
                C.create_date as start_date,
                to_char(date_trunc('hour', C.create_date), 'YYYY-MM-DD HH24:MI:SS') as start_date_hour,
                to_char(date_trunc('hour', C.create_date), 'HH24') as start_hour,
                EXTRACT(dow from  C.create_date) as day_number,
                EXTRACT('epoch' FROM MAX(message_vals.last_message_dt) - c.create_date)/60 AS duration,
                CASE
                    WHEN channel_member_history.has_agent AND channel_member_history.has_bot THEN
                        EXTRACT('epoch' FROM MIN(message_vals.first_agent_message_dt) - MAX(message_vals.last_bot_message_dt))
                    WHEN channel_member_history.has_agent THEN
                        EXTRACT('epoch' FROM MIN(message_vals.first_agent_message_dt) - c.create_date)
                    ELSE
                        EXTRACT('epoch' FROM MIN(message_vals.first_agent_message_dt_legacy) - c.create_date)
                END AS time_to_answer,
                count(distinct C.livechat_operator_id) as nbr_speaker,
                SUM(message_vals.message_count) as nbr_message,
                CASE
                    WHEN channel_member_history.has_agent AND MIN(message_vals.first_agent_message_dt) IS NULL THEN 1
                    WHEN channel_member_history.has_bot AND MIN(message_vals.last_bot_message_dt) IS NULL THEN 1
                    WHEN NOT channel_member_history.has_agent AND NOT channel_member_history.has_bot AND MIN(message_vals.first_agent_message_dt_legacy) IS NULL THEN 1
                    ELSE 0
                END AS is_without_answer,
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
                C.livechat_operator_id as partner_id,
                CASE WHEN channel_member_history.has_agent THEN 1 ELSE 0 END as handled_by_agent,
                CASE WHEN channel_member_history.has_bot and not channel_member_history.has_agent THEN 1 ELSE 0 END as handled_by_bot
            """,
        )

    def _from(self) -> SQL:
        return SQL(
            """
            FROM discuss_channel C
            JOIN message_vals ON message_vals.channel_id = c.id
       LEFT JOIN channel_member_history ON channel_member_history.channel_id = c.id
       LEFT JOIN rating_rating Rate ON (Rate.res_id = C.id and Rate.res_model = 'discuss.channel' and Rate.parent_res_model = 'im_livechat.channel')
            """,
        )

    def _where(self) -> SQL:
        return SQL("WHERE C.livechat_operator_id is not null")

    def _group_by(self) -> SQL:
        return SQL(
            """
            GROUP BY
                C.livechat_operator_id,
                C.id,
                C.name,
                C.livechat_channel_id,
                C.create_date,
                C.uuid,
                Rate.rating,
                channel_member_history.has_bot,
                channel_member_history.has_agent
            """,
        )
