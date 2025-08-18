# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.osv import expression

from odoo.addons.portal.controllers import mail


class PortalChatter(mail.PortalChatter):

    def _get_non_empty_message_domain(self):
        return expression.OR(
            [super()._get_non_empty_message_domain(), [("rating_value", "!=", False)]]
        )
