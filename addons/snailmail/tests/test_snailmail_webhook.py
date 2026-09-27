from odoo.tests import tagged
from odoo.tools import mute_logger
from odoo.addons.snailmail.tests.common import SnailmailWebhookCase


@tagged('post_install', '-at_install')
class TestSnailmailWebhook(SnailmailWebhookCase):
    """
    Test the snailmail webhook controller.
    Flow being tested:
        IAP server  →  POST /webhook/snailmail/1/<event_type>  →  Community DB
    """

    def test_assert_letter_initial_values(self):
        """Verify letter and notification are in expected state after creation."""
        self.assertEqual(self.test_letter.state, 'pending')
        self.assertFalse(self.test_letter.error_code)
        self.assertFalse(self.test_letter.info_msg)

        self.assertTrue(self.test_letter.notification_ids)
        notification = self.test_letter.notification_ids
        self.assertEqual(len(notification), 1)
        self.assertEqual(notification.notification_type, 'snail')
        self.assertEqual(notification.notification_status, 'ready')
        self.assertFalse(notification.failure_type)
        self.assertFalse(notification.failure_reason)

    @mute_logger('odoo.addons.snailmail.controller.snailmail_webhook')
    def test_webhook_delivered(self):
        """Delivered webhook marks letter as sent and notification as sent."""
        self.test_letter.state = 'process'
        self.test_letter.notification_ids.notification_status = 'process'

        response = self._post_webhook('delivered')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'accepted', response.content)

        self.test_letter.invalidate_recordset()
        self.assertEqual(self.test_letter.state, 'sent')
        self.assertFalse(self.test_letter.error_code)

        notification = self.test_letter.notification_ids
        self.assertEqual(notification.notification_status, 'sent')
        self.assertFalse(notification.failure_type)
        self.assertFalse(notification.failure_reason)

    @mute_logger('odoo.addons.snailmail.controller.snailmail_webhook')
    def test_webhook_undeliverable(self):
        """Undeliverable webhook marks letter as error and notification as bounce."""
        self.test_letter.state = 'process'
        self.test_letter.notification_ids.notification_status = 'process'
        response = self._post_webhook('undeliverable', reason='Recipient moved to a new address')

        self.assertEqual(response.status_code, 200)

        self.test_letter.invalidate_recordset()
        self.assertEqual(self.test_letter.state, 'error')
        self.assertEqual(self.test_letter.error_code, 'LETTER_UNDELIVERABLE')
        self.assertEqual(self.test_letter.info_msg.striptags(), 'Recipient moved to a new address')

        notification = self.test_letter.notification_ids
        self.assertEqual(notification.notification_status, 'bounce')
        self.assertEqual(notification.failure_type, 'sn_undeliverable')
        self.assertEqual(notification.failure_reason, 'Undeliverable letter')

    @mute_logger('odoo.addons.snailmail.controller.snailmail_webhook')
    def test_webhook_error_management(self):
        """Test invalid webhook requests return 404."""
        cases = [
            {
                'description': 'invalid event type',
                'event_type': 'unknown_event',
            },
            {
                'description': 'invalid signature',
                'event_type': 'delivered',
                'signature': 'a' * 64,
            },
            {
                'description': 'missing letter_id',
                'event_type': 'delivered',
                'payload': {'status': 'delivered'},
            },
            {
                'description': 'missing status',
                'event_type': 'delivered',
                'payload': {'letter_id': self.pingen_letter_id},
            },
            {
                'description': 'letter not found',
                'event_type': 'delivered',
                'letter_id': 'non-existent-uuid',
            },
            {
                'description': 'empty payload',
                'event_type': 'delivered',
                'payload': {},
            },
        ]
        for case in cases:
            with self.subTest(description=case['description']):
                response = self._post_webhook(
                    case['event_type'],
                    letter_id=case.get('letter_id'),
                    signature=case.get('signature'),
                    payload=case.get('payload'),
                )
                self.assertEqual(response.status_code, 404)

    def test_partner_address_update_updates_letters(self):
        """Changing partner address updates pending/error letters but not sent ones."""
        def assertLetterAddress(street, zip_code, city):
            self.test_letter.invalidate_recordset()
            self.assertEqual(self.test_letter.street, street)
            self.assertEqual(self.test_letter.zip, zip_code)
            self.assertEqual(self.test_letter.city, city)

        self.partner.write({'street': 'New Street 99', 'zip': '9999', 'city': 'New City'})
        assertLetterAddress('New Street 99', '9999', 'New City')

        self.test_letter.state = 'error'
        self.partner.write({'street': 'Newest Street', 'zip': '8888', 'city': 'Newest City'})
        assertLetterAddress('Newest Street', '8888', 'Newest City')

        self.test_letter.state = 'sent'
        self.partner.write({'street': 'Should Not Update', 'zip': '0000', 'city': 'Ghost City'})
        assertLetterAddress('Newest Street', '8888', 'Newest City')
