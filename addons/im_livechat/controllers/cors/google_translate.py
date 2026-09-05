from odoo.http import route

from odoo.addons.mail.controllers.google_translate import GoogleTranslateController


class GoogleTranslateCorsController(GoogleTranslateController):
    @route(
        "/im_livechat/cors/message/translate",
        methods=["POST"],
        type="jsonrpc",
        auth="force_guest",
        cors="*",
    )
    def livechat_message_translate(self, guest_token, message_id, **kwargs):
        return self.translate(message_id, **kwargs)
