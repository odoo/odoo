from odoo.fields import Domain
from odoo.addons.portal.controllers import portal_thread


class PortalChatter(portal_thread.PortalChatter):

    def _setup_portal_message_fetch_extra_domain(self, data):
        domain = super()._setup_portal_message_fetch_extra_domain(data)
        if data.get('rating_value', False) is not False:
            domain &= Domain('rating_value', '=', float(data['rating_value']))
        return domain
