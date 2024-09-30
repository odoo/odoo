# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.osv import expression
from odoo.addons.mail.controllers import thread


class ThreadController(thread.ThreadController):
    def _get_fetch_domain(self, thread_model, thread_id, **kwargs):
        domain = super()._get_fetch_domain(thread_model, thread_id, **kwargs)
        if kwargs.get("portal") and kwargs.get("rating_value"):
            domain = expression.AND(
                [domain, [("rating_value", "=", float(kwargs["rating_value"]))]]
            )
        return domain
