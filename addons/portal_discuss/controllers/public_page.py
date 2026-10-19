from werkzeug.exceptions import NotFound

from odoo.http import request

from odoo.addons.mail.controllers.discuss import public_page
from odoo.addons.mail.tools.discuss import Store, mail_route


class PublicPageController(public_page.PublicPageController):
    @mail_route("/my/conversations", methods=["GET"], type="http", auth="user")
    def discuss_portal(self):
        store = Store().add_global_values(
            companyName=request.env.company.name,
            inPublicPage=True,
        )
        return request.render(
            "mail.discuss_public_channel_template",
            {
                "session_info": request.env["ir.http"].session_info(),
                "store_data": store.as_dict(),
            },
        )

    @mail_route("/my/conversations/<int:channel_id>", methods=["GET"], type="http", auth="user")
    def discuss_portal_channel(self, channel_id):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        return self._response_discuss_public_template(Store(), channel)
