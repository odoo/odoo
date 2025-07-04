# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Im_LivechatChannel(models.Model):
    _inherit = 'im_livechat.channel'

    def _get_livechat_discuss_channel_vals(
            self,
            anonymous_name,
            operator_params=None,
            user_id=None,
            country_id=None,
            lang=None,
            thread_id_to_keep=None,
        ):
        discuss_channel_vals = super()._get_livechat_discuss_channel_vals(
            anonymous_name, operator_params, user_id=user_id, country_id=country_id, lang=lang
        )
        if not discuss_channel_vals:
            return False

        self._delete_operator_requested_chat(discuss_channel_vals, thread_id_to_keep)
        return discuss_channel_vals

    def _delete_operator_requested_chat(self, discuss_channel_vals, thread_id_to_keep):
        visitor_sudo = self.env['website.visitor']._get_visitor_from_request()
        if visitor_sudo:
            discuss_channel_vals['livechat_visitor_id'] = visitor_sudo.id
            # As chat requested by the visitor, delete the chat requested by an operator if any to avoid conflicts between two flows
            chat_request_domain = [('livechat_visitor_id', '=', visitor_sudo.id), ('livechat_end_dt', '=', False)]
            if thread_id_to_keep:
                chat_request_domain.append(('id', '!=', thread_id_to_keep))
            chat_request_channel = self.env['discuss.channel'].sudo().search(chat_request_domain)
            for discuss_channel in chat_request_channel:
                operator = discuss_channel.livechat_operator_id
                operator_name = operator.user_livechat_username or operator.name
                discuss_channel._close_livechat_session(cancel=True, operator=operator_name)
                discuss_channel.is_pending_chat_request = False

    @api.model_create_multi
    def create(self, vals_list):
        channels = super().create(vals_list)
        if self.env.context.get("create_from_website"):
            for channel in channels:
                self.env.user._bus_send(
                    "simple_notification",
                    {
                        "type": "success",
                        "message": self.env._("Channel created: %(name)s", name=channel.name),
                    },
                )
        return channels
