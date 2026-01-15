# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.portal.utils import get_portal_partner


class PortalThreadController(ThreadController):

    def _prepare_message_data(self, post_data, *, thread, **kwargs):
        post_data = super()._prepare_message_data(post_data, thread=thread, **kwargs)
        if kwargs.get("from_create") and request.env.user._is_public():
            if partner := get_portal_partner(
                thread, kwargs.get("hash"), kwargs.get("pid"), kwargs.get("token")
            ):
                post_data["author_id"] = partner.id
        return post_data

    @classmethod
    def _can_edit_message(cls, message, hash=None, pid=None, token=None, **kwargs):
        if message.model and message.res_id and message.env.user._is_public():
            thread = request.env[message.model].browse(message.res_id)
            partner = get_portal_partner(thread, _hash=hash, pid=pid, token=token)
            if partner and message.author_id == partner:
                return True
        return super()._can_edit_message(message, hash=hash, pid=pid, token=token, **kwargs)
