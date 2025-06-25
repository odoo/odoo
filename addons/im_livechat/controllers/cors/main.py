# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route
from odoo.addons.im_livechat.controllers.main import LivechatController
from odoo.addons.im_livechat.tools.misc import force_guest_env


class CorsLivechatController(LivechatController):
    @route("/im_livechat/cors/visitor_leave_session", type="json", auth="public", cors="*")
    def cors_visitor_leave_session(self, guest_token, channel_id):
        force_guest_env(guest_token)
        self.visitor_leave_session(channel_id)

    @route("/im_livechat/cors/feedback", type="json", auth="public", cors="*")
    def cors_feedback(self, guest_token, channel_id, rate, reason=None):
        force_guest_env(guest_token)
        self.feedback(channel_id, rate, reason)

    @route("/im_livechat/cors/history", type="json", auth="public", cors="*")
    def cors_history_pages(self, guest_token, pid, channel_id, page_history=None):
        force_guest_env(guest_token)
        return self.history_pages(pid, channel_id, page_history)

    @route("/im_livechat/cors/email_livechat_transcript", type="json", auth="public", cors="*")
    def cors_email_livechat_transcript(self, guest_token, channel_id, email):
        force_guest_env(guest_token)
        return self.email_livechat_transcript(channel_id, email)

    @route("/im_livechat/cors/get_session", methods=["POST"], type="json", auth="public", cors="*")
    def cors_get_session(
        self, channel_id, anonymous_name, previous_operator_id=None, chatbot_script_id=None, persisted=True, **kwargs
    ):
        force_guest_env(kwargs.get("guest_token", ""), raise_if_not_found=False)
        return self.get_session(
            channel_id, anonymous_name, previous_operator_id, chatbot_script_id, persisted, **kwargs
        )

    @route("/im_livechat/cors/init", type="json", auth="public", cors="*")
    def cors_livechat_init(self, channel_id, guest_token=""):
        force_guest_env(guest_token, raise_if_not_found=False)
        return self.livechat_init(channel_id)
