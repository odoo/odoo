from freezegun import freeze_time

from odoo.addons.test_event_full.tests.common import TestEventFullCommon
from odoo.tests.common import tagged


@tagged('event_online', 'post_install', '-at_install')
class TestEventPortal(TestEventFullCommon):

    def test_portal_access(self):
        """ From portal, users should only see their own registrations and should be
        able to download their tickets.
        """
        sale_order = self.env['sale.order'].with_user(self.user_sales_salesman).create({
            'partner_id': self.partner_portal.id,
        })
        base_values = {
            'event_id': self.test_event.id,
            'event_ticket_id': self.test_event.event_ticket_ids[0].id,
        }
        registration_values = [
            # Registration booked by / assigned to portal user
            {'partner_id': self.partner_portal.id, 'name': 'Booked', **base_values},
            # Registration SO belongs to the portal user
            {'sale_order_id': sale_order.id, 'name': 'Assigned SO', **base_values},
            # Other random registrations with portal info (shouldn't appear on user portal)
            {'name': self.partner_portal.name, **base_values},
            {'email': self.partner_portal.email, **base_values},
            {'phone': self.partner_portal.phone, **base_values},
        ]
        self.env['event.registration'].create(registration_values)
        with freeze_time(self.reference_now, tick=True):
            self.start_tour('/my/events', 'event_portal', login='portal')
