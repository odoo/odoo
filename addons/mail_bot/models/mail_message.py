from odoo import models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _message_format(self, format_reply=True, msg_vals=None, for_current_user=False):
        message_values = super()._message_format(format_reply=format_reply, msg_vals=msg_vals, for_current_user=for_current_user)
        bot_com_id = self.env["ir.model.data"]._xmlid_to_res_id("mail_bot.odoobot_comment")
        for vals in message_values:
            message_sudo = self.browse(vals['id']).sudo().with_prefetch(self.ids)
            vals.update({
                'is_odoobot_discussion': message_sudo.subtype_id.id == bot_com_id
            })
        return message_values
