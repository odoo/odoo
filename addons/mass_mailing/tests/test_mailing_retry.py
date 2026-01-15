# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.tests.common import users

from unittest.mock import patch

class TestMailingRetry(MassMailCommon, CronMixinCase):

    @classmethod
    def setUpClass(cls):
        super(TestMailingRetry, cls).setUpClass()
        cls._create_mailing_list()

    @users('user_marketing')
    def test_mailing_retry_immediate_trigger(self):
        mailing = self.env['mailing.mailing'].create({
            'name': 'TestMailing',
            'subject': 'Test',
            'mailing_type': 'mail',
            'body_html': '<div>Hello</div>',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
            'contact_list_ids': [(4, self.mailing_list_1.id)],
        })
        mailing.action_launch()

        # force email sending to fail to test our retry mechanism
        def patched_mail_mail_send(mail_records, auto_commit=False, raise_exception=False, smtp_session=None,
                                   alias_domain_id=False, mail_server=False, post_send_callback=None):
            mail_records.write({'state': 'exception', 'failure_reason': 'forced_failure'})

        with (
            patch('odoo.addons.mail.models.mail_mail.MailMail._send', patched_mail_mail_send),
            self.enter_registry_test_mode(),
        ):
            self.env.ref('mass_mailing.ir_cron_mass_mailing_queue').sudo().method_direct_trigger()

        with self.capture_triggers('mass_mailing.ir_cron_mass_mailing_queue') as captured_triggers:
            mailing.action_retry_failed()

        self.assertEqual(len(captured_triggers.records), 1, "Should have created an additional trigger immediately")
        captured_trigger = captured_triggers.records[0]
        self.assertEqual(captured_trigger.cron_id, self.env.ref('mass_mailing.ir_cron_mass_mailing_queue'))
