# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Domain

from odoo.addons.portal.controllers.thread import PortalThreadController


class PortalRatingThreadController(PortalThreadController):
    def _get_non_empty_message_domain(self):
        return super()._get_non_empty_message_domain() | Domain("rating_value", "!=", False)

    def _get_fetch_domain(self, *args, only_portal=None, **kwargs):
        domain = super()._get_fetch_domain(*args, only_portal=only_portal, **kwargs)
        if only_portal and kwargs.get("rating_value", False) is not False:
            domain &= Domain("rating_value", "=", float(kwargs["rating_value"]))
        return domain
