# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mass_mailing.tests.common import TestMassSMSCommon
from odoo.tests.common import HttpCase
from odoo.tools import mute_logger


class TestSmsController(HttpCase, TestMassSMSCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.recipients = cls._create_mailing_sms_test_records(model='mail.test.sms', count=5)
        cls.mailing_sms.mailing_domain = [('id', 'in', cls.recipients.ids)]

    def _send_sms_immediately_and_assert_traces(self, moderated=False):
        self.mailing_sms.sms_force_send = True
        with self.mockSMSGateway(moderated=moderated):
            self.mailing_sms.action_send_sms()

        all_traces = self.assertSMSTraces(
            [{'partner': record.customer_id,
              'number': '+32' + record.phone_nbr[1:],
              'trace_status': 'process' if moderated else 'pending',
              } for i, record in enumerate(self.recipients)],
            self.mailing_sms, self.recipients,
        )
        return all_traces

    @mute_logger("odoo.addons.base.models.ir_http")
    def test_webhook_update_traces_pending_to_sent(self):
        all_traces = self._send_sms_immediately_and_assert_traces()
        first_two_traces = all_traces[:2]
        other_traces = all_traces[2:]
        statuses = [{'sms_status': 'delivered', 'uuids': first_two_traces.sms_tracker_ids.mapped('sms_uuid')}]
        self.assertEqual(self._make_webhook_jsonrpc_request(statuses), 'OK')
        self.assertEqual(set(first_two_traces.mapped('trace_status')), {'sent'})
        self.assertEqual(set(other_traces.mapped('trace_status')), {'pending'})

    @mute_logger("odoo.addons.base.models.ir_http")
    def test_webhook_update_traces_process_to_pending(self):
        self.assertEqual(self.mailing_sms.state, 'draft')
        all_traces = self._send_sms_immediately_and_assert_traces(moderated=True)
        self.assertEqual(self.mailing_sms.state, 'sending')
        statuses = [{'sms_status': 'sent', 'uuids': all_traces.sms_tracker_ids.mapped('sms_uuid')}]
        self.assertEqual(self._make_webhook_jsonrpc_request(statuses), 'OK')
        self.assertEqual(set(all_traces.mapped('trace_status')), {'pending'})
        self.assertEqual(self.mailing_sms.state, 'done')

    @mute_logger("odoo.addons.base.models.ir_http")
    def test_webhook_update_traces_sent_to_bounce_and_failed(self):
        all_traces = self._send_sms_immediately_and_assert_traces()
        trace_1, trace_2 = all_traces[:2]
        other_traces = all_traces[2:]
        statuses = [
            {'sms_status': 'invalid_destination', 'uuids': [trace_1.sms_tracker_ids.sms_uuid]},
            {'sms_status': 'sms_not_delivered', 'uuids': [trace_2.sms_tracker_ids.sms_uuid]},
            {'sms_status': 'delivered', 'uuids': other_traces.sms_tracker_ids.mapped('sms_uuid')}
        ]
        self.assertEqual(self._make_webhook_jsonrpc_request(statuses), 'OK')
        self.assertEqual(trace_1.trace_status, 'bounce')
        self.assertEqual(trace_2.trace_status, 'error')
        self.assertTrue(set(other_traces.mapped('trace_status')), {'sent'})
