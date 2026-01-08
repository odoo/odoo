# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.addons.mass_mailing_sms.tests.common import MassSMSCommon
from odoo.addons.mass_mailing.tests.test_mailing_ab_testing import TestMailingABTestingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestMailingSMSABTesting(MassSMSCommon, TestMailingABTestingCommon):
    def setUp(self):
        super().setUp()
        self.ab_testing_mailing_sms_1 = self.env['mailing.mailing'].create({
            'subject': 'A/B Testing SMS V1',
            'contact_list_ids': self.mailing_list.ids,
            'ab_testing_enabled': True,
            'ab_testing_pc': 10,
            'ab_testing_schedule_datetime': datetime.now(),
            'mailing_type': 'sms'
        })
        self.ab_testing_mailing_sms_2 = self.ab_testing_mailing_sms_1.copy({
            'subject': 'A/B Testing SMS V2',
            'ab_testing_pc': 20,
        })

    def test_mailing_sms_ab_testing_compare(self):
        # compare version feature should returns all mailings of the same
        # campaign having a/b testing enabled and of mailing_type 'sms'.
        compare_version = self.ab_testing_mailing_sms_1.action_compare_versions()
        self.assertEqual(
            self.env['mailing.mailing'].search(compare_version.get('domain')),
            self.ab_testing_mailing_sms_1 + self.ab_testing_mailing_sms_2
        )
