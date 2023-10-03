# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route
from odoo.addons.im_livechat.controllers.main import LivechatController
from odoo.addons.im_livechat.tools.misc import downgrade_to_public_user, force_guest_env


class CorsLivechatController(LivechatController):
    @route("/im_livechat/cors/visitor_leave_session", type="json", auth="public", cors="*")
    def cors_visitor_leave_session(self, guest_token, uuid):
        force_guest_env(guest_token)
        self.visitor_leave_session(uuid)

    @route("/im_livechat/cors/get_session", methods=["POST"], type="json", auth="public", cors="*")
    def cors_get_session(
        self, channel_id, anonymous_name, previous_operator_id=None, chatbot_script_id=None, persisted=True, **kwargs
    ):
        downgrade_to_public_user()
        return self.get_session(
            channel_id, anonymous_name, previous_operator_id, chatbot_script_id, persisted, **kwargs
        )
