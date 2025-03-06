# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Domain
from odoo.addons.mail.controllers import thread


class ThreadController(thread.ThreadController):
    def _get_fetch_domain(self, thread, **kwargs):
        domain = super()._get_fetch_domain(thread, **kwargs)
        if kwargs.get("rating_value"):
            domain = Domain.AND(
                [domain, [("rating_value", "=", float(kwargs["rating_value"]))]]
            )
        return domain
