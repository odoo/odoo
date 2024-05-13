# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.mail.controllers.link_preview import LinkPreviewController
from odoo.addons.portal.models.mail_thread import check_portal_access


class PortalLinkPreviewController(LinkPreviewController):
    @http.route()
    @check_portal_access
    def mail_link_preview(self, message_id):
        return super().mail_link_preview(message_id)
