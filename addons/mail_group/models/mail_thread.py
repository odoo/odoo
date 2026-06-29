from odoo import models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _message_route_check_is_a_reply(
        self, message_dict, replying_to_msg, email_to_list, email_to_localparts,
        rcpt_tos_list, rcpt_tos_valid_list,
    ):
        #    if destination = alias with different model -> consider it is a forward and not a reply
        #    if destination = alias with same model -> check contact settings as they still apply
        is_a_reply, reply_model, reply_thread_id = bool(replying_to_msg), replying_to_msg.model, replying_to_msg.res_id

        if is_a_reply and reply_model and reply_model == 'mail.group' and reply_thread_id and len(email_to_list) == 1:
            other_group_alias = self.env['mail.alias'].search([
                ('alias_model_id', '=', self.env['ir.model']._get_id('mail.group')),
                ('alias_force_thread_id', '!=', reply_thread_id),
                ('alias_force_thread_id', '!=', False),
                ('alias_full_name', 'in', email_to_list),
            ])
            if other_group_alias:
                return False, False, False, rcpt_tos_valid_list
        return super()._message_route_check_is_a_reply(
            message_dict, replying_to_msg, email_to_list, email_to_localparts,
            rcpt_tos_list, rcpt_tos_valid_list,
        )
