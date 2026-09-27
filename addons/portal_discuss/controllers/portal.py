# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal


class DiscussCustomerPortal(CustomerPortal):

    def _prepare_portal_counter_values(self, counter):
        if counter == 'discuss_count':
            domain = [
                ('partner_id', '=', request.env.user.partner_id.id),
                ('is_unread', '=', True),
            ]
            return 'discuss.channel.member', domain, 'read'
        return super()._prepare_portal_counter_values(counter)
