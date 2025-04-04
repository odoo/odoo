# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.http import route
from odoo.addons.mail.controllers.discuss.binary import BinaryController
from odoo.addons.im_livechat.tools.misc import force_guest_env


class LivechatBinaryController(BinaryController):
    @route(
        "/im_livechat/cors/channel/<int:channel_id>/attachment/<int:attachment_id>",
        methods=["GET"],
        type="http",
        auth="public",
        cors="*",
    )
    def livechat_channel_attachment(self, guest_token, channel_id, attachment_id, download=None, **kwargs):
        force_guest_env(guest_token)
        return self.discuss_channel_attachment(channel_id, attachment_id, download, **kwargs)

    @route(
        [
            "/im_livechat/cors/channel/<int:channel_id>/image/<int:attachment_id>",
            "/im_livechat/cors/channel/<int:channel_id>/image/<int:attachment_id>/<int:width>x<int:height>",
        ],
        methods=["GET"],
        type="http",
        auth="public",
        cors="*"
    )
    def livechat_fetch_image(self, guest_token, channel_id, attachment_id, width=0, height=0, **kwargs):
        force_guest_env(guest_token)
        return self.fetch_image(channel_id, attachment_id, width, height, **kwargs)
