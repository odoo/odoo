from werkzeug.exceptions import NotFound

from odoo.http import request

from odoo.addons.mail.controllers.discuss import public_page
from odoo.addons.mail.tools.discuss import Store, mail_route


class PublicPageController(public_page.PublicPageController):
    @mail_route("/my/conversations", methods=["GET"], type="http", auth="user")
    def discuss_portal(self):
        return self._response_discuss_public_template(Store())

    @mail_route("/my/conversations/<int:channel_id>", methods=["GET"], type="http", auth="user")
    def discuss_portal_channel(self, channel_id):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        return self._response_discuss_public_template(Store(), channel)
