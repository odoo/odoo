
from werkzeug.exceptions import NotFound

from odoo.http import request

from odoo.addons.mail.controllers.discuss import public_page
from odoo.addons.mail.tools.discuss import mail_route


class PublicPageController(public_page.PublicPageController):
    @mail_route("/my/conversations", methods=["GET"], type="http", auth="user", website=True)
    def discuss_portal(self):
        return self._response_discuss_portal_embed("/discuss")

    @mail_route(
        "/my/conversations/<int:channel_id>", methods=["GET"], type="http", auth="user", website=True
    )
    def discuss_portal_channel(self, channel_id):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        return self._response_discuss_portal_embed(f"/discuss/channel/{channel_id}")

    def _response_discuss_channel_invitation(self, store, channel, guest_email=None):
        response = super()._response_discuss_channel_invitation(store, channel, guest_email)
        if request.env.user._is_portal():
            return request.redirect(f"/my/conversations/{channel.id}")
        return response

    def _response_discuss_portal_embed(self, path):
        """Render the discuss public page embedded in the portal layout."""
        query = request.httprequest.query_string.decode()
        return request.render(
            "portal_discuss.discuss_public_channel_template_portal",
            {"embed_url": f"{path}?{query}" if query else path},
        )
