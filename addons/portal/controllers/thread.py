# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.addons.mail.controllers import thread
from odoo.addons.portal.utils import validate_thread_with_hash_pid, validate_thread_with_token


class ThreadController(thread.ThreadController):

    def _prepare_post_data(self, post_data, thread, **kwargs):
        post_data = super()._prepare_post_data(post_data, thread, **kwargs)
        if request.env.user._is_public():
            if validate_thread_with_hash_pid(thread, kwargs.get("hash"), kwargs.get("pid")):
                post_data["author_id"] = int(kwargs["pid"])
            elif (
                partner := thread._mail_get_partners()[thread.id][:1]
            ) and validate_thread_with_token(thread, kwargs.get("token")):
                post_data["author_id"] = partner.id
        return post_data
