# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class DiscussMessageStarred(models.Model):
    _name = "discuss.message.starred"
    _description = "SQL view to handle starred message inbox"
    _auto = False
    _inherit = ['message.abstract']

    mail_message_id = fields.Many2one("mail.message")
    discuss_message_id = fields.Many2one("discuss.message")
    partner_id = fields.Many2one("res.partner")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        # Reference contract is the one with the latest start_date.
        self.env.cr.execute("""CREATE or REPLACE VIEW %s AS (
        SELECT id, id as mail_message_id, NULL as discuss_message_id, res_partner_id as partner_id, create_date FROM
        mail_message AS mm
        INNER JOIN mail_message_res_partner_starred_rel AS mmrpsr ON mmrpsr.mail_message_id = mm.id
        UNION
        SELECT id, NULL as mail_message_id, id as discuss_message_id, res_partner_id as partner_id, create_date FROM
        discuss_message AS dm
        INNER JOIN discuss_message_res_partner_starred_rel AS dmrpsr ON dmrpsr.discuss_message_id = dm.id
        ORDER BY create_date
        )""" % (self._table))

    def _format(self):
        formated_messages = []
        for message_starred in self:
            if message_starred.mail_message_id:
                formated_messages.append(message_starred.mail_message_id._message_format()[0])
            elif message_starred.discuss_message_id:
                formated_messages.append(message_starred.discuss_message_id._discuss_message_format()[0])
        return formated_messages
