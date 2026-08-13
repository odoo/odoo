# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mass_mailing_sms.tests.common import MassSMSCommon
from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.tests.common import users

from unittest.mock import patch

class TestMailingRetrySMS(MassSMSCommon, CronMixinCase):

    @classmethod
    def setUpClass(cls):
        super(TestMailingRetrySMS, cls).setUpClass()
        cls._create_mailing_list()

    @users('user_marketing')
    def test_sms_retry_immediate_trigger(self):
        mailing = self.env['mailing.mailing'].create({
            'name': 'TestMailing',
            'subject': 'Test',
            'mailing_type': 'sms',
            'body_plaintext': 'Coucou hibou',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
            'contact_list_ids': [(4, self.mailing_list_1.id)],
        })
        mailing.action_send_sms()

        # force the SMS sending to fail to test our retry mechanism
        def patched_sms_sms_send(sms_records, unlink_failed=False, unlink_sent=True, raise_exception=False):
            sms_records.write({'state': 'error', 'failure_type':'sms_credit'})

        with patch('odoo.addons.sms.models.sms_sms.SmsSms._send', patched_sms_sms_send):
            self.env.ref('sms.ir_cron_sms_scheduler_action').sudo().method_direct_trigger()

        with self.capture_triggers('mass_mailing.ir_cron_mass_mailing_queue') as captured_triggers:
            mailing.action_retry_failed()

        self.assertEqual(len(captured_triggers.records), 1, "Should have created an additional trigger immediately")
        captured_trigger = captured_triggers.records[0]
        self.assertEqual(captured_trigger.cron_id, self.env.ref('mass_mailing.ir_cron_mass_mailing_queue'))
