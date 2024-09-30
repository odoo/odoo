# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.mail.tools.discuss import Store


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _get_allowed_message_post_params(self):
        return super()._get_allowed_message_post_params() | {"rating_value"}

    def _thread_to_store(self, store: Store, /, *, request_list=None, **kwargs):
        super()._thread_to_store(store, request_list=request_list, **kwargs)
        for thread in self:
            if hasattr(thread, "rating_count") and thread.rating_count:
                store.add(
                    thread, {"rating_stats": thread.sudo().rating_get_stats()}, as_thread=True
                )
