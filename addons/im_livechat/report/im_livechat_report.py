# -*- coding: utf-8 -*-
from openerp import api, fields, models, tools


class im_livechat_report(models.Model):
    """ Livechat Support Report """

    _name = "im_livechat.report"
    _description = "Livechat Support Report"
    _order = 'start_date, session_name'
    _auto = False

    session_name = fields.Char('Session Name', readonly=True)
    uuid = fields.Char('UUID', readonly=True)
    start_date = fields.Datetime('Start Date of session', readonly=True, help="Start date of the conversation")
    start_date_hour = fields.Char('Hour of start Date of session', readonly=True)
    duration = fields.Float('Average duration', digits=(16, 2), readonly=True, group_operator="avg", help="Duration of the conversation (in seconds)")
    time_in_session = fields.Float('Time in session', digits=(16, 2), readonly=True, group_operator="avg", help="Average time the user spend in the conversation")
    time_to_answer = fields.Float('Time to answer', digits=(16, 2), readonly=True, group_operator="avg", help="Average time to give the first answer to the visitor")
    nbr_messages = fields.Integer('Average message', readonly=True, group_operator="avg", help="Number of message in the conversation")
    nbr_user_messages = fields.Integer('Average of messages/user', readonly=True, group_operator="avg", help="Average number of message per user")
    nbr_speakers = fields.Integer('# of speakers', readonly=True, group_operator="avg", help="Number of different speakers")
    user_id = fields.Many2one('res.users', 'User', readonly=True)
    session_id = fields.Many2one('im_chat.session', 'Session', readonly=True)
    channel_id = fields.Many2one('im_livechat.channel', 'Channel', readonly=True)


    def init(self, cr):
        # Note : start_date_hour must be remove when the read_group will allow grouping on the hour of a datetime. Don't forget to change the view !
        tools.drop_view_if_exists(cr, 'im_livechat_report')
        cr.execute("""
            CREATE OR REPLACE VIEW im_livechat_report AS (
                SELECT
                    min(M.id) as id,
                    S.uuid as uuid,
                    CONCAT(C.name, ' / ', S.id) as session_name,
                    S.create_date as start_date,
                    to_char(date_trunc('hour', S.create_date), 'YYYY-MM-DD HH24:MI:SS') as start_date_hour,
                    EXTRACT('epoch' from ((SELECT (max(create_date)-min(create_date)) FROM im_chat_message WHERE to_id=S.id AND from_id = U.id))) as time_in_session,
                    EXTRACT('epoch' from ((SELECT min(create_date) FROM im_chat_message WHERE to_id=S.id AND from_id IS NOT NULL)-(SELECT min(create_date) FROM im_chat_message WHERE to_id=S.id AND from_id IS NULL))) as time_to_answer,
                    EXTRACT('epoch' from (max((SELECT (max(create_date)) FROM im_chat_message WHERE to_id=S.id))-S.create_date)) as duration,
                    (SELECT count(distinct COALESCE(from_id, 0)) FROM im_chat_message WHERE to_id=S.id) as nbr_speakers,
                    (SELECT count(id) FROM im_chat_message WHERE to_id=S.id) as nbr_messages,
                    count(M.id) as nbr_user_messages,
                    U.id as user_id,
                    S.channel_id as channel_id,
                    S.id as session_id
                FROM im_chat_message M
                    LEFT JOIN im_chat_session S on (S.id = M.to_id)
                    LEFT JOIN res_users U on (U.id = M.from_id)
                    LEFT JOIN im_livechat_channel C on (S.channel_id = C.id)
                WHERE S.channel_id IS NOT NULL
                GROUP BY U.id, M.to_id, S.id, C.name, S.uuid
            )
        """)
