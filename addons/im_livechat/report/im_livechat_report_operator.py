# -*- coding: utf-8 -*-
from openerp import fields, models, tools


class ImLivechatReportOperator(models.Model):
    """ Livechat Support Report on the Operator """

    _name = "im_livechat.report.operator"
    _description = "Livechat Support Report"
    _order = 'livechat_channel_id, partner_id'
    _auto = False

    partner_id = fields.Many2one('res.partner', 'Operator', readonly=True)
    livechat_channel_id = fields.Many2one('im_livechat.channel', 'Channel', readonly=True)
    nbr_channel = fields.Integer('# of channel', readonly=True, group_operator="sum", help="Number of conversation")
    channel_id = fields.Many2one('mail.channel', 'Conversation', readonly=True)
    start_date = fields.Datetime('Start Date of session', readonly=True, help="Start date of the conversation")
    time_to_answer = fields.Float('Time to answer', digits=(16, 2), readonly=True, group_operator="avg", help="Average time to give the first answer to the visitor")
    duration = fields.Float('Average duration', digits=(16, 2), readonly=True, group_operator="avg", help="Duration of the conversation (in seconds)")

    def init(self, cr):
        # Note : start_date_hour must be remove when the read_group will allow grouping on the hour of a datetime. Don't forget to change the view !
        tools.drop_view_if_exists(cr, 'im_livechat_report_operator')
        cr.execute("""
            CREATE OR REPLACE VIEW im_livechat_report_operator AS (
                SELECT
                    row_number() OVER () AS id,
                    P.id as partner_id,
                    L.id as livechat_channel_id,
                    count(C.id) as nbr_channel,
                    C.id as channel_id,
                    C.create_date as start_date,
                    EXTRACT('epoch' FROM (max((SELECT (max(M.create_date)) FROM mail_message M JOIN mail_message_mail_channel_rel R ON (R.mail_message_id = M.id) WHERE R.mail_channel_id = C.id))-C.create_date)) as duration,
                    EXTRACT('epoch' from ((SELECT min(M.create_date) FROM mail_message M, mail_message_mail_channel_rel R WHERE M.author_id=P.id AND R.mail_channel_id = C.id AND R.mail_message_id = M.id)-(SELECT min(M.create_date) FROM mail_message M, mail_message_mail_channel_rel R WHERE M.author_id IS NULL AND R.mail_channel_id = C.id AND R.mail_message_id = M.id))) as time_to_answer
                FROM im_livechat_channel_im_user O
                    JOIN res_users U ON (O.user_id = U.id)
                    JOIN res_partner P ON (U.partner_id = P.id)
                    LEFT JOIN im_livechat_channel L ON (L.id = O.channel_id)
                    LEFT JOIN mail_channel C ON (C.livechat_channel_id = L.id)
                GROUP BY P.id, L.id, C.id, C.create_date
            )
        """)
