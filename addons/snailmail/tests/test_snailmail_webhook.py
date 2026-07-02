from odoo.tests import tagged
from odoo.addons.snailmail.tests.common import SnailmailWebhookCase


@tagged('post_install', '-at_install')
class TestSnailmailWebhook(SnailmailWebhookCase):
    """
    Test the snailmail webhook controller.
    Flow being tested:
        IAP server  →  POST /webhook/snailmail/1/<event_type>  →  Community DB
    """

    def test_webhook_delivered(self):
        """Delivered webhook marks letter as sent and notification as sent."""
        self.letter.state = 'process'
        self.letter.notification_ids.notification_status = 'process'

        payload = self._make_payload(status='delivered')
        response = self._post_webhook('delivered', payload)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'accepted', response.content)

        self.letter.invalidate_recordset()
        self.assertEqual(self.letter.state, 'sent')
        self.assertFalse(self.letter.error_code)

        notification = self.letter.notification_ids
        self.assertEqual(notification.notification_status, 'sent')
        self.assertFalse(notification.failure_type)
        self.assertFalse(notification.failure_reason)

    def test_webhook_undeliverable(self):
        """Undeliverable webhook marks letter as error and notification as bounce."""
        self.letter.state = 'process'
        self.letter.notification_ids.notification_status = 'process'
        payload = self._make_payload(
            status='undeliverable',
            reason='Recipient moved to a new address'
        )
        response = self._post_webhook('undeliverable', payload)

        self.assertEqual(response.status_code, 200)

        self.letter.invalidate_recordset()
        self.assertEqual(self.letter.state, 'error')
        self.assertEqual(self.letter.error_code, 'LETTER_UNDELIVERABLE')
        self.assertEqual(self.letter.info_msg.striptags(), 'Recipient moved to a new address')

        notification = self.letter.notification_ids
        self.assertEqual(notification.notification_status, 'bounce')
        self.assertEqual(notification.failure_type, 'sn_undeliverable')
        self.assertEqual(notification.failure_reason, 'Undeliverable letter')

    def test_webhook_error_management(self):
        """Test invalid webhook requests return 404."""
        cases = [
            {
                'description': 'invalid event type',
                'event_type': 'unknown_event',
                'payload': self._make_payload(status='delivered'),
            },
            {
                'description': 'invalid signature',
                'event_type': 'delivered',
                'payload': self._make_payload(status='delivered'),
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
                'payload': self._make_payload(letter_id='non-existent-uuid'),
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
                    case['payload'],
                    signature=case.get('signature'),
                )
                self.assertEqual(response.status_code, 404)
