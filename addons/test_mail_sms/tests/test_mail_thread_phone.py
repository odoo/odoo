# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail_sms.tests.common import TestSMSCommon, TestSMSRecipients
from odoo.tests import tagged, users


@tagged('mail_thread')
class TestSMSActionsCommon(TestSMSCommon, TestSMSRecipients):
    """ Test mail.thread.phone mixin, its tools and API """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_phone_records, cls.test_phone_partners = cls._create_records_for_batch(
            'mail.test.sms.bl',
            5,
        )
        cls.test_phone_records += cls.env['mail.test.sms.bl'].create([
            {
                'phone_nbr': '+32475110505',
                'mobile_nbr': '+32475000505',
            }, {
                'phone_nbr': '0032475110606',
                'mobile_nbr': '0032475000606',
            }, {
                'phone_nbr': '0032475110707',
                'mobile_nbr': False,
            }, {
                'phone_nbr': False,
                'mobile_nbr': False,
            },
        ])

    def test_initial_data(self):
        """ Test initial data for this class, allowing to be sure of I/O of tests. """
        self.assertEqual(
            self.test_phone_records.mapped('mobile_nbr'),
            ['0475000000', '0475000101', '0475000202', '0475000303', '0475000404',
             '+32475000505', '0032475000606',
             False, False,
            ]
        )
        self.assertEqual(
            self.test_phone_records.mapped('phone_nbr'),
            [False] * 5 + ['+32475110505', '0032475110606', '0032475110707', False]
        )
