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
            # duplicated of 0606
            {
                'phone_nbr': '0475110606',
                'mobile_nbr': False,
            }, {
                'phone_nbr': False,
                'mobile_nbr': '0475110606',
            }
        ])
        cls.void_record = cls.test_phone_records[-3]
        cls.dupes = cls.test_phone_records[-2:]

    def test_initial_data(self):
        """ Test initial data for this class, allowing to be sure of I/O of tests. """
        self.assertEqual(
            self.test_phone_records.mapped('mobile_nbr'),
            [
                False, False, False, False, False,
                '+32475000505', '0032475000606', False, False,
                False, '0475110606',
            ]
        )
        self.assertEqual(
            self.test_phone_records.mapped('phone_nbr'),
            [
                '0475000000', '0475000101', '0475000202', '0475000303',
                '0475000404', '+32475110505', '0032475110606', '0032475110707',
                False, '0475110606', False,
            ]
        )
        self.assertEqual(
            self.test_phone_records.mapped('phone_sanitized'),
            [
                '+32475000000', '+32475000101', '+32475000202', '+32475000303',
                '+32475000404', '+32475110505', '+32475110606', '+32475110707',
                False, '+32475110606', '+32475110606',
            ],
        )

    @users('employee')
    def test_search_phone_mobile_search_boolean(self):
        test_phone_records = self.test_phone_records.with_env(self.env)

        # test Falsy -> is set / is not set
        for test_values in [False, '', ' ']:
            # test is not set -> both fields should be not set
            results = self.env['mail.test.sms.bl'].search([('phone_mobile_search', '=', test_values)])
            self.assertEqual(results, self.void_record,
                             'Search on phone_mobile_search: = False: record with two void values')
            # test is set -> at least one field should be set
            results = self.env['mail.test.sms.bl'].search([('phone_mobile_search', '!=', test_values)])
            self.assertEqual(results, test_phone_records - self.void_record,
                             'Search on phone_mobile_search: != False: record at least one value set')

        # test Truthy -> is set / is not set
        results = self.env['mail.test.sms.bl'].search([('phone_mobile_search', '=', True)])
        self.assertEqual(results, test_phone_records - self.void_record,
                         'Search on phone_mobile_search: = True: record at least one value set')
        results = self.env['mail.test.sms.bl'].search([('phone_mobile_search', '!=', True)])
        self.assertEqual(results, self.void_record,
                         'Search on phone_mobile_search: != True: record with two void values')

    @users('employee')
    def test_search_phone_mobile_search_equal(self):
        """ Test searching by phone/mobile with direct search """
        test_phone_records = self.test_phone_records.with_env(self.env)

        for user_country in (self.env.ref("base.be"), self.env.ref("base.us")):
            self.env.user.sudo().country_id = user_country.id
            # test "=" search
            for source, expected in [
                ('0475', self.env['mail.test.sms.bl']),  # incomplete -> no results on "="
                # complete national number
                ('0475000000', test_phone_records[0]),
                # various international numbers
                # ('32475110606', test_phone_records[6]),  # currently not supported, returns nothing
                ('0032475110606', test_phone_records[6]),
                ('+32475110606', test_phone_records[6]),
                ('+32 475 11 06 06', test_phone_records[6]),
            ]:
                with self.subTest(source=source):
                    results = self.env['mail.test.sms.bl'].search([('phone_mobile_search', '=', source)])
                    self.assertEqual(results, expected)

    @users('employee')
    def test_search_phone_mobile_search_ilike(self):
        """ Test searching by phone/mobile on various ilike combinations """
        test_phone_records = self.test_phone_records.with_env(self.env)

        # test ilike search
        for source, ilike_expected, notilike_expected in [
            (
                '0475', test_phone_records[:5] + self.dupes,
                test_phone_records - test_phone_records[:5] - self.dupes
            ),
            ('101', test_phone_records[1], test_phone_records - test_phone_records[1]),
            # not ilike is not the inverse with formatting but hey, that's not easy to do
            ('+32475', test_phone_records[5:8], test_phone_records),
            ('0032475', test_phone_records[5:8], test_phone_records),
        ]:
            # test ilike search
            with self.subTest(source=source, operator="ilike"):
                results = self.env['mail.test.sms.bl'].search([('phone_mobile_search', 'ilike', source)])
                self.assertEqual(results, ilike_expected)

            # test inverse ilike search: should be the complement
            with self.subTest(source=source, operator="not ilike"):
                results = self.env['mail.test.sms.bl'].search([('phone_mobile_search', 'not ilike', source)])
                self.assertEqual(results, notilike_expected)
