# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _get_thread_with_access(self, thread_id, *, mode="read", **kwargs):
        res = super()._get_thread_with_access(thread_id, mode=mode, **kwargs)
        if not self._name == "product.template" or self.env["website"].is_view_active(
            "website_sale.product_comment"
        ):
            return res
        return self.browse()
