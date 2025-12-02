# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
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
    start_date_minutes = fields.Char("Start Date of session, truncated to minutes", readonly=True)
    day_number = fields.Selection(
        selection=[
            ("0", "Sunday"),
            ("1", "Monday"),
            ("2", "Tuesday"),
            ("3", "Wednesday"),
            ("4", "Thursday"),
            ("5", "Friday"),
            ("6", "Saturday"),
        ],
        string="Day of the Week",
        readonly=True,
    )
    time_to_answer = fields.Float("Response Time", digits=(16, 6), readonly=True, aggregator="avg", help="Average time in hours to give the first answer to the visitor")
    start_date_hour = fields.Char('Hour of start Date of session', readonly=True)
    duration = fields.Float("Duration (min)", digits=(16, 2), readonly=True, aggregator="avg", help="Duration of the conversation (in minutes)")
    nbr_message = fields.Integer("Messages per Session", readonly=True, aggregator="avg", help="Number of message in the conversation")
    country_id = fields.Many2one('res.country', 'Country of the visitor', readonly=True)
    lang_id = fields.Many2one("res.lang", related="channel_id.livechat_lang_id", string="Language", readonly=True)
    rating = fields.Integer('Rating', aggregator="avg", readonly=True)
    # TODO DBE : Use Selection field - Need : Pie chart must show labels, not keys.
    rating_text = fields.Char('Satisfaction Rate', readonly=True)
    partner_id = fields.Many2one("res.partner", "Agent", readonly=True)
    handled_by_bot = fields.Integer("Handled by Bot", readonly=True, aggregator="sum")
    handled_by_agent = fields.Integer("Handled by Agent", readonly=True, aggregator="sum")
    visitor_partner_id = fields.Many2one("res.partner", string="Customer", readonly=True)
    call_duration_hour = fields.Float("Call Duration", digits=(16, 2), readonly=True, aggregator="avg")
    has_call = fields.Float("Whether the session had a call", readonly=True)
    number_of_calls = fields.Float("# of Sessions with calls", readonly=True, related="has_call", aggregator="sum")
    percentage_of_calls = fields.Float("Session with Calls (%)", readonly=True, related="has_call", aggregator="avg")
    session_outcome = fields.Selection(
        selection=[
            ("no_answer", "Never Answered"),
            ("no_agent", "No one Available"),
            ("no_failure", "Success"),
            ("escalated", "Escalated"),
        ],
        string="Session Outcome",
        readonly=True,
    )
    chatbot_script_id = fields.Many2one("chatbot.script", "Chatbot", readonly=True)
    chatbot_answers_path = fields.Char("Chatbot Answers", readonly=True)
    chatbot_answers_path_str = fields.Char("Chatbot Answers (String)", readonly=True)
    session_expertises = fields.Char("Expertises used in this session (String)", readonly=True)
    session_expertise_ids = fields.Many2many(
        "im_livechat.expertise",
        readonly=True,
        related="channel_id.livechat_expertise_ids",
        string="Expertises used in this session",
    )
    conversation_tag_ids = fields.Many2many(
        "im_livechat.conversation.tag",
        readonly=True,
        related="channel_id.livechat_conversation_tag_ids",
        string="Tags used in this conversation",
    )
    agent_requesting_help_history = fields.Many2one(
        "im_livechat.channel.member.history",
        related="channel_id.livechat_agent_requesting_help_history",
        readonly=True,
    )
    agent_providing_help_history = fields.Many2one(
        "im_livechat.channel.member.history",
        related="channel_id.livechat_agent_providing_help_history",
        readonly=True,
    )

    @property
    def _unknown_chatbot_answer_name(self):
        return self.env._("Unknown")

    @property
    def _table_query(self):
        return SQL("%s %s %s", self._select(), self._from(), self._where())

    def _select(self) -> SQL:
        return SQL(
            """
            SELECT
                C.id as id,
                C.uuid as uuid,
                C.id as channel_id,
                C.name as channel_name,
                C.livechat_channel_id as livechat_channel_id,
                C.create_date as start_date,
                channel_member_history.visitor_partner_id AS visitor_partner_id,
                to_char(date_trunc('hour', C.create_date), 'YYYY-MM-DD HH24:MI:SS') as start_date_hour,
                to_char(date_trunc('hour', C.create_date), 'HH24') as start_hour,
                to_char(date_trunc('minute', C.create_date), 'YYYY-MM-DD HH:MI:SS') AS start_date_minutes,
                EXTRACT(dow from C.create_date)::text AS day_number,
                EXTRACT('epoch' FROM COALESCE(C.livechat_end_dt, NOW() AT TIME ZONE 'utc') - C.create_date)/60 AS duration,
                CASE
                    WHEN channel_member_history.has_agent AND channel_member_history.has_bot THEN
                        EXTRACT('epoch' FROM message_vals.first_agent_message_dt - message_vals.last_bot_message_dt)
                    WHEN channel_member_history.has_agent THEN
                        EXTRACT('epoch' FROM message_vals.first_agent_message_dt - c.create_date)
                    ELSE
                        EXTRACT('epoch' FROM message_vals.first_agent_message_dt_legacy - c.create_date)
                END/3600 AS time_to_answer,
                message_vals.message_count as nbr_message,
                CASE
                    WHEN C.livechat_is_escalated THEN 'escalated'
                    ELSE C.livechat_failure
                END AS session_outcome,
                C.country_id,
                NULLIF(C.rating_last_value, 0) AS rating,
                CASE
                    WHEN C.rating_last_value = 1 THEN 'Unhappy'
                    WHEN C.rating_last_value = 5 THEN 'Happy'
                    WHEN C.rating_last_value = 3 THEN 'Neutral'
                    ELSE null
                END as rating_text,
                C.livechat_operator_id as partner_id,
                CASE WHEN channel_member_history.has_agent THEN 1 ELSE 0 END as handled_by_agent,
                CASE WHEN channel_member_history.has_bot and not channel_member_history.has_agent THEN 1 ELSE 0 END as handled_by_bot,
                CASE WHEN channel_member_history.chatbot_script_id IS NOT NULL AND NOT channel_member_history.has_agent THEN channel_member_history.chatbot_script_id ELSE NULL END AS chatbot_script_id,
                CASE WHEN call_history_data.call_duration_hour IS NOT NULL THEN 1 ELSE 0 END AS has_call,
                call_history_data.call_duration_hour,
                chatbot_answer_history.chatbot_answers_path,
                chatbot_answer_history.chatbot_answers_path_str,
                expertise_history.expertises session_expertises
            """,
        )

    def _from(self) -> SQL:
        return SQL(
            """
            FROM discuss_channel C
       LEFT JOIN LATERAL (
                SELECT BOOL_OR(livechat_member_type = 'agent') AS has_agent,
                       BOOL_OR(livechat_member_type = 'bot') AS has_bot,
                       MIN(CASE WHEN livechat_member_type = 'visitor' THEN partner_id END) AS visitor_partner_id,
                       MIN(chatbot_script_id) AS chatbot_script_id
                  FROM im_livechat_channel_member_history
                 WHERE channel_id = C.id
        ) AS channel_member_history ON TRUE
       LEFT JOIN LATERAL
            (
                SELECT SUM(
                           CASE
                               WHEN discuss_call_history.end_dt IS NOT NULL
                               THEN EXTRACT(EPOCH FROM discuss_call_history.end_dt - discuss_call_history.start_dt) / 3600
                           END
                       ) AS call_duration_hour
                  FROM discuss_call_history
                 WHERE discuss_call_history.channel_id = C.id
            ) AS call_history_data ON TRUE
        LEFT JOIN LATERAL
            (
                SELECT STRING_AGG(chatbot_message.user_raw_script_answer_id::TEXT, ' - ' ORDER BY chatbot_message.id) AS chatbot_answers_path,
                       STRING_AGG(
                           COALESCE(
                               chatbot_script_answer.name->>%s,
                               chatbot_script_answer.name->>'en_US',
                               fallback.value,
                               %s
                           ),
                           ' - ' ORDER BY chatbot_message.id
                        ) AS chatbot_answers_path_str
                  FROM chatbot_message
             LEFT JOIN chatbot_script_answer
                    ON chatbot_message.user_raw_script_answer_id = chatbot_script_answer.id
             LEFT JOIN LATERAL
                  (
                      SELECT value
                      FROM jsonb_each_text(chatbot_script_answer.name)
                      LIMIT 1
                  ) AS fallback ON TRUE
                WHERE chatbot_message.user_raw_script_answer_id IS NOT NULL
                  AND chatbot_message.discuss_channel_id = C.id
            ) AS chatbot_answer_history ON TRUE
        LEFT JOIN LATERAL
            (
                SELECT STRING_AGG(
                            COALESCE(
                                im_livechat_expertise.name->>%s,
                                im_livechat_expertise.name->>'en_US',
                                fallback.value
                            ),
                            ' - ' ORDER BY im_livechat_expertise.id
                       ) AS expertises
                  FROM im_livechat_channel_member_history_im_livechat_expertise_rel REL
                  JOIN im_livechat_expertise
                    ON im_livechat_expertise.id = REL.im_livechat_expertise_id
                  JOIN im_livechat_channel_member_history
                    ON im_livechat_channel_member_history.id = REL.im_livechat_channel_member_history_id
                  JOIN LATERAL
                    (
                        SELECT value
                          FROM jsonb_each_text(im_livechat_expertise.name)
                         LIMIT 1
                    ) AS fallback ON TRUE
                 WHERE im_livechat_channel_member_history.channel_id = C.id
            ) AS expertise_history ON TRUE
        LEFT JOIN LATERAL
            (
                SELECT COUNT(DISTINCT M.id) AS message_count,
                       MIN(CASE WHEN H.livechat_member_type = 'agent' THEN M.create_date END) AS first_agent_message_dt,
                       MAX(CASE WHEN H.livechat_member_type = 'bot' THEN M.create_date END) AS last_bot_message_dt,
                       MIN(CASE WHEN M.author_id = C.livechat_operator_id THEN M.create_date END) AS first_agent_message_dt_legacy
                  FROM mail_message M
             LEFT JOIN im_livechat_channel_member_history H on H.channel_id = M.res_id AND (M.author_id = H.partner_id OR M.author_guest_id = H.guest_id)
                 WHERE M.res_id = C.id and M.model = 'discuss.channel'
            ) AS message_vals ON TRUE
            """,
            self.env.lang,
            self._unknown_chatbot_answer_name,
            self.env.lang,
        )

    def _where(self) -> SQL:
        return SQL("WHERE C.channel_type = 'livechat'")

    @api.model
    def formatted_read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None, order=None):
        # Update chatbot_answers_path label: ids are used for grouping but names
        # should be displayed.
        result = super().formatted_read_group(
            domain, groupby, aggregates, having=having, offset=offset, limit=limit, order=order
        )
        answer_ids = {
            int(answer_id.strip())
            for entry in result
            if entry.get("chatbot_answers_path")
            for answer_id in entry["chatbot_answers_path"].split("-")
        }
        answer_name_by_id = {
            answer.id: answer.name
            for answer in self.env["chatbot.script.answer"].search_fetch(
                [("id", "in", answer_ids)],
                ["name"],
            )
        }
        for entry in result:
            if not (path := entry.get("chatbot_answers_path")):
                continue
            id_list = [int(answer_id.strip()) for answer_id in path.split("-")]
            entry["chatbot_answers_path"] = " - ".join(
                answer_name_by_id.get(answer_id, self._unknown_chatbot_answer_name)
                for answer_id in id_list
            )
        return result

    @api.model
    def action_open_discuss_channel_view(self, domain=()):
        discuss_channels = self.search_fetch(domain, ["channel_id"]).channel_id
        action = self.env["ir.actions.act_window"]._for_xml_id("im_livechat.discuss_channel_action")
        if len(discuss_channels) == 1:
            action["res_id"] = discuss_channels.id
            action["view_mode"] = "form"
            action["views"] = [view for view in action["views"] if view[1] == "form"]
            return action
        action["context"] = {}
        action["domain"] = [("id", "in", discuss_channels.ids)]
        action["mobile_view_mode"] = "list"
        action["view_mode"] = "list"
        action["views"] = [view for view in action["views"] if view[1] in ("list", "form")]
        return action
