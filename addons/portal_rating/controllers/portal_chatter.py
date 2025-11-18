from odoo.osv import expression

from odoo.addons.portal.controllers import portal_thread
from odoo.fields import Domain


class PortalChatter(portal_thread.PortalChatter):
    def _get_non_empty_message_domain(self):
        return super()._get_non_empty_message_domain() | Domain("rating_value", "!=", False)

    def _setup_portal_message_fetch_extra_domain(self, data):
        domains = [super()._setup_portal_message_fetch_extra_domain(data)]
        if data.get('rating_value', False) is not False:
            domains.append([('rating_value', '=', float(data['rating_value']))])
        return expression.AND(domains)
