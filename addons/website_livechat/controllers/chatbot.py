# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from odoo import http, Command, fields
from odoo.http import request
from odoo.addons.mail.tools.discuss import Store


class WebsiteLivechatChatbotScriptController(http.Controller):
    @http.route('/chatbot/<model("chatbot.script"):chatbot_script>/test',
        type="http", auth="user", website=True)
    def chatbot_test_script(self, chatbot_script):
        """ Custom route allowing to test a chatbot script.
        As we don't have a im_livechat.channel linked to it, we pre-emptively create a discuss.channel
        that will hold the conversation between the bot and the user testing the script. """
        store = Store()
        channels = request.env["discuss.channel"].search([
            ["is_member", "=", True],
            ["livechat_end_dt", "=", False],
            ["chatbot_current_step_id.chatbot_script_id", "=", chatbot_script.id],
        ])
        for channel in channels:
            channel._close_livechat_session()
        store.add(channels, {"close_chat_window": True})

        discuss_channel_values = {
            "channel_member_ids": [
                Command.create(
                    {
                        "partner_id": chatbot_script.operator_partner_id.id,
                        # making sure the unpin_dt is always later than the last_interest_dt
                        # so that the channel is unpinned
                        "unpin_dt": fields.Datetime.now(),
                        "last_interest_dt": fields.Datetime.now() - timedelta(seconds=30),
                        "livechat_member_type": "bot",
                    },
                ),
                Command.create(
                    {
                        "partner_id": request.env.user.partner_id.id,
                        "livechat_member_type": "visitor",
                    },
                ),
            ],
            'livechat_operator_id': chatbot_script.operator_partner_id.id,
            'chatbot_current_step_id': chatbot_script._get_welcome_steps()[-1].id,
            'channel_type': 'livechat',
            'name': chatbot_script.title,
        }
        discuss_channel = request.env['discuss.channel'].create(discuss_channel_values)
        chatbot_script._post_welcome_steps(discuss_channel)
        store.add(discuss_channel, {"open_chat_window": True})
        request.env["res.users"]._init_store_data(store)
        store.add(chatbot_script)
        return request.render("im_livechat.chatbot_test_script_page", {
            'server_url': chatbot_script.get_base_url(),
            'chatbot_script': chatbot_script,
            'chatbot_test_store': store.get_result(),
        })
