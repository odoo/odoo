# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route
from odoo.addons.mail.controllers.link_preview import LinkPreviewController
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class LivechatLinkPreviewController(LinkPreviewController):
    @route("/mail/link_preview", cors="*")
    @add_guest_to_context
    def mail_link_preview(self, message_id, clear=None):
        return super().mail_link_preview(message_id, clear)

    @route("/mail/link_preview/delete", cors="*")
    @add_guest_to_context
    def mail_link_preview_delete(self, link_preview_id):
        return super().mail_link_preview_delete(link_preview_id)
