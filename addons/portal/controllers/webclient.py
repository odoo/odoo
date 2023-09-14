# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context
from odoo.addons.portal.models.mail_thread import check_portal_access_token


class WebClient(WebclientController):

    @route("/mail/init_messaging", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    @check_portal_access_token
    def mail_init_messaging(self):
        return super().mail_init_messaging()
