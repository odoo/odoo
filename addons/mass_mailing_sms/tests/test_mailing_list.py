# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mass_mailing_sms.tests.common import MassSMSCommon
from odoo.tests import Form, users


class TestMailingListSms(MassSMSCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailingListSms, cls).setUpClass()
        cls._create_mailing_list()

    @users('user_marketing')
    def test_mailing_list_action_send_sms(self):
        sms_ctx = self.mailing_list_1.action_send_mailing_sms().get('context', {})
        form = Form(self.env['mailing.mailing'].with_context(sms_ctx))
        form.sms_subject = 'Test SMS'
        form.body_plaintext = 'Test sms body'
        sms = form.save()
        # Check that mailing model and mailing list are set properly
        self.assertEqual(
                    sms.mailing_model_id, self.env['ir.model']._get('mailing.list'),
                    'Should have correct mailing model set')
        self.assertEqual(sms.contact_list_ids, self.mailing_list_1, 'Should have correct mailing list set')
        self.assertEqual(sms.mailing_type, 'sms', 'Should have correct mailing_type')
