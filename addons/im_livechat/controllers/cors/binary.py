# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.http import route
from odoo.addons.mail.controllers.discuss.binary import BinaryController
from odoo.addons.im_livechat.tools.misc import downgrade_to_public_user, force_guest_env


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

    @route(["/im_livechat/cors/web/image"], type='http', auth="public", cors="*")
    # pylint: disable=redefined-builtin,invalid-name
    def livechat_content_image(
        self, model, id, field, unique=False, guest_token=None, access_token=None
    ):
        if guest_token:
            force_guest_env(guest_token)
        else:
            downgrade_to_public_user()
        return self.content_image(
            model=model, id=id, field=field, unique=unique, access_token=access_token
        )
