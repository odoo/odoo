# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route
from odoo.addons.mail.controllers import thread


class ThreadController(thread.ThreadController):

    @route(website=True)
    def mail_message_post(self, thread_model, thread_id, post_data, context=None, **kwargs):
        return super().mail_message_post(thread_model, thread_id, post_data, context, **kwargs)
