from openerp.osv import fields,osv
from openerp import tools


class im_livechat_report(osv.Model):
    """ Livechat Support Report """
    _name = "im_livechat.report"
    _auto = False
    _description = "Livechat Support Report"
    _columns = {
        'uuid': fields.char('UUID', size=50, readonly=True),
        'start_date': fields.datetime('Start Date of session', readonly=True, help="Start date of the conversation"),
        'start_date_hour': fields.char('Hour of start Date of session', readonly=True),
        'duration': fields.float('Average duration', digits=(16,2), readonly=True, group_operator="avg", help="Duration of the conversation (in seconds)"),
        'time_in_session': fields.float('Time in session', digits=(16,2), readonly=True, group_operator="avg", help="Average time the user spend in the conversation"),
        'time_to_answer': fields.float('Time to answer', digits=(16,2), readonly=True, group_operator="avg", help="Average time to give the first answer to the visitor"),
        'nbr_messages': fields.integer('Average message', readonly=True, group_operator="avg", help="Number of message in the conversation"),
        'nbr_user_messages': fields.integer('Average of messages/user', readonly=True, group_operator="avg", help="Average number of message per user"),
        'nbr_speakers': fields.integer('# of speakers', readonly=True, group_operator="avg", help="Number of different speakers"),
        'rating': fields.float('Rating', readonly=True, group_operator="avg", help="Average Rating"),
        'user_id': fields.many2one('res.users', 'User', readonly=True),
        'session_id': fields.many2one('im_chat.session', 'Session', readonly=True),
        'channel_id': fields.many2one('im_livechat.channel', 'Channel', readonly=True),
    }
    _order = 'start_date, uuid'

    def init(self, cr):
        # Note : start_date_hour must be remove when the read_group will allow grouping on the hour of a datetime. Don't forget to change the view !
        tools.drop_view_if_exists(cr, 'im_livechat_report')
        cr.execute("""
            CREATE OR REPLACE VIEW im_livechat_report AS (
                SELECT
                    min(M.id) as id,
                    S.uuid as uuid,
                    S.create_date as start_date,
                    to_char(date_trunc('hour', S.create_date), 'YYYY-MM-DD HH24:MI:SS') as start_date_hour,
                    EXTRACT('epoch' from ((SELECT (max(create_date)-min(create_date)) FROM im_chat_message WHERE to_id=S.id AND from_id = U.id))) as time_in_session,
                    EXTRACT('epoch' from ((SELECT min(create_date) FROM im_chat_message WHERE to_id=S.id AND from_id IS NOT NULL)-(SELECT min(create_date) FROM im_chat_message WHERE to_id=S.id AND from_id IS NULL))) as time_to_answer,
                    EXTRACT('epoch' from (max((SELECT (max(create_date)) FROM im_chat_message WHERE to_id=S.id))-S.create_date)) as duration,
                    (SELECT count(distinct COALESCE(from_id, 0)) FROM im_chat_message WHERE to_id=S.id) as nbr_speakers,
                    (SELECT count(id) FROM im_chat_message WHERE to_id=S.id) as nbr_messages,
                    count(M.id) as nbr_user_messages,
                    CAST(S.feedback_rating AS INT) as rating,
                    U.id as user_id,
                    S.channel_id as channel_id
                FROM im_chat_message M
                    LEFT JOIN im_chat_session S on (S.id = M.to_id)
                    LEFT JOIN res_users U on (U.id = M.from_id)
                WHERE S.channel_id IS NOT NULL
                GROUP BY U.id, M.to_id, S.id
            )
        """)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
