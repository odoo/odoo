from odoo.addons.event_sale.tests.common import TestEventSaleCommon

class TestEventRegistration(TestEventSaleCommon):

    def test_event_registration_without_sale_order_id(self):
        """
        Test the creation of an event registration without a sale order.
        """
        # Create a registration and generate a QR code for the existing event
        registration = self.env['event.registration'].create({
            'name': 'Test',
            'event_id': self.event_0.id,
            'state': 'draft'
        })
        registration_summary = registration._get_registration_summary()

        self.assertEqual(registration_summary['event_display_name'], 'TestEvent')
        self.assertEqual(registration_summary['name'], 'Test')
        self.assertEqual(registration_summary['ticket_name'], 'None')
        self.assertEqual(registration_summary['sale_status_value'], 'Free')
