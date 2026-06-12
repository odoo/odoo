from odoo.http import route
from odoo.addons.mail.controllers.google_translate import GoogleTranslateController
from odoo.addons.im_livechat.tools.misc import force_guest_env


class GoogleTranslateCorsController(GoogleTranslateController):
    @route(
        "/im_livechat/cors/message/translate",
        methods=["POST"],
        type="jsonrpc",
        auth="public",
        cors="*",
    )
    def livechat_message_translate(self, guest_token, message_id, **kwargs):
        force_guest_env(guest_token)
        return self.translate(message_id, **kwargs)
