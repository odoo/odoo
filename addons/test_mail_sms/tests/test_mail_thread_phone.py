# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sms.tests.common import SMSCommon
from odoo.addons.test_mail_sms.tests.common import TestSMSRecipients
from odoo.tests import tagged, users


@tagged('mail_thread')
class TestSMSActionsCommon(SMSCommon, TestSMSRecipients):
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

    @users('employee')
    def test_search_phone_mobile_search_boolean(self):
        test_phone_records = self.test_phone_records.with_env(self.env)

        # test Falsy -> is set / is not set
        for test_values in [False, '', ' ']:
            # test is not set -> both fields should be not set
            results = self.env['mail.test.sms.bl'].search([('phone_mobile_search', '=', test_values)])
            self.assertEqual(results, test_phone_records[-1],
                             'Search on phone_mobile_search: = False: record with two void values')
            # test is set -> at least one field should be set
            results = self.env['mail.test.sms.bl'].search([('phone_mobile_search', '!=', test_values)])
            self.assertEqual(results, test_phone_records[:-1],
                             'Search on phone_mobile_search: != False: record at least one value set')

        # test Truthy -> is set / is not set
        results = self.env['mail.test.sms.bl'].search([('phone_mobile_search', '=', True)])
        self.assertEqual(results, test_phone_records[:-1],
                         'Search on phone_mobile_search: = True: record at least one value set')
        results = self.env['mail.test.sms.bl'].search([('phone_mobile_search', '!=', True)])
        self.assertEqual(results, test_phone_records[-1],
                         'Search on phone_mobile_search: != True: record with two void values')

    @users('employee')
    def test_search_phone_mobile_search_equal(self):
        """ Test searching by phone/mobile with direct search """
        test_phone_records = self.test_phone_records.with_env(self.env)

        # test "=" search
        results = self.env['mail.test.sms.bl'].search([('phone_mobile_search', '=', '0475')])
        self.assertFalse(results, 'Search on phone_mobile_search: = should return only matching results')
        results = self.env['mail.test.sms.bl'].search([('phone_mobile_search', '=', '0475000000')])
        self.assertEqual(results, test_phone_records[0])
        results = self.env['mail.test.sms.bl'].search([('phone_mobile_search', '=', '0032475110606')])
        self.assertEqual(results, test_phone_records[6])
        results = self.env['mail.test.sms.bl'].search([('phone_mobile_search', '=', '+32475110606')])
        self.assertEqual(results, test_phone_records[6])

    @users('employee')
    def test_search_phone_mobile_search_ilike(self):
        """ Test searching by phone/mobile on various ilike combinations """
        test_phone_records = self.test_phone_records.with_env(self.env)

        # test ilike search
        results = self.env['mail.test.sms.bl'].search([('phone_mobile_search', 'ilike', '0475')])
        self.assertEqual(results, test_phone_records[:5])
        results = self.env['mail.test.sms.bl'].search([('phone_mobile_search', 'ilike', '101')])
        self.assertEqual(results, test_phone_records[1])

        # test search using +32/0032
        results = self.env['mail.test.sms.bl'].search([('phone_mobile_search', 'ilike', '+32475')])
        self.assertEqual(results, test_phone_records[5:8],
                         'Search on phone_mobile_search: +32/0032 likeliness')
        results = self.env['mail.test.sms.bl'].search([('phone_mobile_search', 'ilike', '0032475')])
        self.assertEqual(results, test_phone_records[5:8],
                         'Search on phone_mobile_search: +32/0032 likeliness')

        # test inverse ilike search
        results = self.env['mail.test.sms.bl'].search([('phone_mobile_search', 'not ilike', '0475')])
        self.assertEqual(results, test_phone_records - test_phone_records[:5])
        results = self.env['mail.test.sms.bl'].search([('phone_mobile_search', 'not ilike', '101')])
        self.assertEqual(results, test_phone_records - test_phone_records[1])
