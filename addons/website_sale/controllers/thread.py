# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route

from odoo.addons.mail.controllers import thread


class ThreadController(thread.ThreadController):
    @route()
    def mail_message_post(self, thread_model, thread_id, post_data, context=None, **kwargs):
        website_id = post_data.pop("website_id", None)
        if website_id:
            context = context or {}
            context["website_id"] = int(website_id)
        super().mail_message_post(thread_model, thread_id, post_data, context, **kwargs)
