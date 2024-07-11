# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.test_mail_sms.tests.test_sms_management import TestSMSActionsCommon
from odoo.tests.common import HttpCase, JsonRpcException
from odoo.tools import mute_logger


class TestSmsController(HttpCase, TestSMSActionsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sms_processing, cls.sms_sent = cls.env['sms.sms'].create([
            {
                'body': 'A test about pending state',
                'number': '10',
                'mail_message_id': cls.msg.id,
                'uuid': '8db55b6a9ec6443ca1d69af3ab500e27',
                'state': 'process',
            }, {
                'mail_message_id': cls.msg.id,
                'body': 'A test about sent state',
                'number': '20',
                'uuid': '8505e6f439d4472690c7955de9b210a4',
                'state': 'sent',
            },
        ])
        cls.notification_processing, cls.notification_pending = cls.env['mail.notification'].create([
            {
                'mail_message_id': cls.msg.id,
                'notification_type': 'sms',
                'notification_status': 'process',
                'sms_id_int': cls.sms_processing.id,
                'sms_tracker_ids': [Command.create({'sms_uuid': cls.sms_processing.uuid})],
            }, {
                'mail_message_id': cls.msg.id,
                'notification_type': 'sms',
                'notification_status': 'pending',
                'sms_id_int': cls.sms_sent.id,
                'sms_tracker_ids': [Command.create({'sms_uuid': cls.sms_sent.uuid})],
            },
        ])
        cls.sms_sent.unlink()  # as it would normally be.

    @mute_logger("odoo.addons.base.models.ir_http")
    def test_webhook_update_notification_from_processing_to_pending(self):
        self.assertTrue(self.sms_processing)
        statuses = [{'sms_status': 'sent', 'uuids': [self.sms_processing.uuid]}]
        self.assertEqual(self._make_webhook_jsonrpc_request(statuses), 'OK')
        self.assertTrue(self.sms_processing.to_delete)
        self.assertEqual(self.notification_processing.notification_status, 'pending')

    @mute_logger('odoo.addons.base.models.ir_http')
    def test_webhook_update_notification_from_pending_to_bounced(self):
        statuses = [{'sms_status': 'invalid_destination', 'uuids': [self.notification_pending.sms_tracker_ids.sms_uuid]}]
        self.assertEqual(self._make_webhook_jsonrpc_request(statuses), 'OK')
        self.assertEqual(self.notification_pending.notification_status, 'bounce')

    @mute_logger('odoo.addons.base.models.ir_http')
    def test_webhook_update_notification_from_pending_to_delivered(self):
        statuses = [{'sms_status': 'delivered', 'uuids': [self.notification_pending.sms_tracker_ids.sms_uuid]}]
        self.assertEqual(self._make_webhook_jsonrpc_request(statuses), 'OK')
        self.assertEqual(self.notification_pending.notification_status, 'sent')

    @mute_logger('odoo.addons.base.models.ir_http')
    def test_webhook_update_notification_from_pending_to_failed(self):
        statuses = [{'sms_status': 'not_delivered', 'uuids': [self.notification_pending.sms_tracker_ids.sms_uuid]}]
        self.assertEqual(self._make_webhook_jsonrpc_request(statuses), 'OK')
        self.assertEqual(self.notification_pending.notification_status, 'exception')
        self.assertEqual(self.notification_pending.failure_type, 'sms_not_delivered')

    @mute_logger('odoo.addons.base.models.ir_http')
    def test_webhook_update_notification_multiple_statuses(self):
        statuses = [
            {'sms_status': 'sent', 'uuids': [self.notification_processing.sms_tracker_ids.sms_uuid]},
            {'sms_status': 'delivered', 'uuids': [self.notification_pending.sms_tracker_ids.sms_uuid]}
        ]
        self.assertEqual(self._make_webhook_jsonrpc_request(statuses), 'OK')
        self.assertTrue(self.sms_processing.to_delete)
        self.assertEqual(self.notification_processing.notification_status, 'pending')
        self.assertEqual(self.notification_pending.notification_status, 'sent')

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.addons.sms.controllers.main', 'odoo.http')
    def test_webhook_update_raises_with_wrong_event_data(self):
        statuses = [{'sms_status': 'delivered', 'uuids': ['not a uuid']}]
        with self.assertRaises(JsonRpcException):
            self._make_webhook_jsonrpc_request(statuses)

    @mute_logger('odoo.addons.base.models.ir_http')
    def test_webhook_update_succeeds_with_non_existent_uuids(self):
        statuses = [{'sms_status': 'delivered', 'uuids': ['00000000000000000000000000000000']}]
        self.assertEqual(self._make_webhook_jsonrpc_request(statuses), 'OK')

    @mute_logger('odoo.addons.base.models.ir_http')
    def test_webhook_update_succeeds_with_unknown_status(self):
        statuses = [{'sms_status': 'something_new', 'uuids': [self.notification_pending.sms_tracker_ids.sms_uuid]}]
        self.assertEqual(self._make_webhook_jsonrpc_request(statuses), 'OK')
        self.assertEqual(self.notification_pending.notification_status, 'exception')
