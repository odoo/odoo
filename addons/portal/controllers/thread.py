# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.addons.mail.controllers import thread
from odoo.addons.portal.utils import get_portal_partner


class ThreadController(thread.ThreadController):

    def _prepare_post_data(self, post_data, thread, **kwargs):
        post_data = super()._prepare_post_data(post_data, thread, **kwargs)
        if request.env.user._is_public():
            if partner := get_portal_partner(
                thread, kwargs.get("hash"), kwargs.get("pid"), kwargs.get("token")
            ):
                post_data["author_id"] = partner.id
        return post_data

    def _is_message_editable(self, message, **kwargs):
        if message._is_editable_in_portal(**kwargs):
            return True
        return super()._is_message_editable(message, **kwargs)
