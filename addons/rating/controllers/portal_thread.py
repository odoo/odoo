# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.portal.controllers import portal_thread
from odoo.fields import Domain


class PortalChatter(portal_thread.PortalChatter):

    def _get_non_empty_message_domain(self):
        return super()._get_non_empty_message_domain() | Domain("rating_value", "!=", False)
