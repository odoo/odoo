# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from odoo.addons.mail.controllers import thread


class ThreadController(thread.ThreadController):
    @route()
    def mail_message_post(self, thread_model, thread_id, post_data, context=None, **kwargs):
        if kwargs.get("canned_response_ids"):
            request.update_context(canned_response_ids=kwargs["canned_response_ids"])
        return super().mail_message_post(thread_model, thread_id, post_data, context, **kwargs)
