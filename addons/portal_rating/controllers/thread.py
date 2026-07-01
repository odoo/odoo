# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Domain

from odoo.addons.portal.controllers.thread import PortalWebClientController


class PortalRatingThreadController(PortalWebClientController):
    @classmethod
    def _get_fetch_share_domain(cls, records, **params):
        domain = super()._get_fetch_share_domain(records, **params)
        if params.get("rating_value", False) is not False:
            domain &= Domain("rating_value", "=", float(params["rating_value"]))
        return domain
