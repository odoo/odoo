# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.sms.tests import common as sms_common
from odoo.addons.test_mail.tests import common as test_mail_common
from odoo.addons.test_mail_full.tests import common as test_mail_full_common


class TestSMSComposer(test_mail_full_common.BaseFunctionalTest, sms_common.MockSMS, test_mail_common.MockEmails, test_mail_common.TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestSMSComposer, cls).setUpClass()
        cls._test_body = 'VOID CONTENT'
        cls.partner_numbers = [
            phone_validation.phone_format(partner.mobile, partner.country_id.code, partner.country_id.phone_code, force_format='E164')
            for partner in (cls.partner_1 | cls.partner_2)
        ]

    def test_composer_no_model(self):
        composer = self.env['sms.composer'].with_context().create({
            'message': self._test_body,
            'recipients': '+32475998877, 0475997788'
        })

        with self.mockSMSGateway():
            composer.action_send_sms()
        # self.assertSMSSent(self.random_numbers, self._test_body)  # TDE FIXME: actually sanitizer is not called on numbers in current master (saas 12.3)
        self.assertSMSSent('+32475998877, 0475997788'.split(', '), self._test_body)

    def test_composer_no_mail_thread(self):
        composer = self.env['sms.composer'].with_context(active_model='test_performance.base').create({
            'message': self._test_body,
            'recipients': '+32475998877, 0475997788'
        })

        with self.mockSMSGateway():
            composer.action_send_sms()
        # self.assertSMSSent(self.random_numbers, self._test_body)  # TDE FIXME: actually sanitizer is not called on numbers in current master (saas 12.3)
        self.assertSMSSent('+32475998877, 0475997788'.split(', '), self._test_body)

    def test_composer_partners_active_domain(self):
        partners = self.partner_1 | self.partner_2
        composer = self.env['sms.composer'].with_context(
            active_model='res.partner',
            active_domain=[('id', 'in', partners.ids)]
        ).create({
            'message': self._test_body,
        })

        with self.mockSMSGateway():
            composer.action_send_sms()
        self.assertSMSSent(self.partner_numbers, self._test_body)

    def test_composer_partners_sanitize(self):
        partner_incorrect = self.env['res.partner'].create({
            'name': 'Jean-Claude Incorrect',
            'email': 'jean.claude@example.com',
            'mobile': 'coincoin',
            })
        partners = self.partner_1 | self.partner_2 | partner_incorrect
        # composer = self.env['sms.composer'].with_context(
        #     active_model='res.partner',
        #     active_domain=[('id', 'in', partners.ids)]
        # ).create({
        #     'message': self._test_body,
        # })

        # with self.mockSMSGateway():
        #     composer.action_send_sms()
        # self.assertSMSSent((self.partner_1 | self.partner_2).mapped('mobile'), test_body)  # TDE FIXME: actually sanitizer does not work in current master (saas 12.23))