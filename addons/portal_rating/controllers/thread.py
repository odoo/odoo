# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.controllers import thread


class ThreadController(thread.ThreadController):

    def _get_allowed_message_post_params(self):
        post_params = super()._get_allowed_message_post_params()
        post_params.add("rating_value")
        return post_params
