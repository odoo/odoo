# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import babel

from odoo.tests import common


class TestGroupbyWeek(common.TransactionCase):
    """ Test for read_group() with group by week: the first day of the week
    depends on the language.
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Model = cls.env['test_read_group.fill_temporal']
        # same for all locales
        cls.iso_weeks = {
            52: 2,  # 2022-01-01 and 2022-01-02 (W52 of 2021)
             1: 1,  # 2022-01-03
            21: 3,  # 2022-05-27, 2022-05-28, 2022-05-29
            22: 1,  # 2022-05-30
            24: 2,  # 2022-06-18 and 2022-06-19
            25: 1,  # 2022-06-20
        }
        cls.per_locale = {
            # same as ISO
            "fr_BE": {
                "W52 2021": 2,
                "W1 2022": 1,
                "W21 2022": 3,
                "W22 2022": 1,
                "W24 2022": 2,
                "W25 2022": 1
            },
            # non-iso, start of week = sat
            "ar_SY": {
                "W1 2022": 3,
                "W21 2022": 1,
                "W22 2022": 3,
                "W25 2022": 3,
            },
            # non-iso, start of week = sun
            "en_US": {
                "W1 2022": 1,
                "W2 2022": 2,
                "W22 2022": 2,
                "W23 2022": 2,
                "W25 2022": 1,
                "W26 2022": 2,
            }
        }
        cls.records = cls.Model.create([  # BE,  SY,  US
            {'date': '2022-01-01'},       # W52, W01, W01
            {'date': '2022-01-02'},       # W52, W01, W02
            {'date': '2022-01-03'},       # W01, W01, W02
            {'date': '2022-05-27'},       # W21, W21, W22
            {'date': '2022-05-28'},       # W21, W22, W22
            {'date': '2022-05-29'},       # W21, W22, W23
            {'date': '2022-05-30'},       # W22, W22, W23
            {'date': '2022-06-18'},       # W24, W25, W25
            {'date': '2022-06-19'},       # W24, W25, W26
            {'date': '2022-06-20'},       # W25, W25, W26
        ])

    def test_belgium(self):
        """ fr_BE - first day of the week = Monday """
        self.assertEqual(
            babel.Locale.parse("fr_BE").first_week_day,
            0,
        )
        self.env['res.lang']._activate_lang('fr_BE')
        groups = self.Model.with_context(lang='fr_BE').read_group(
            [('id', 'in', self.records.ids)], fields=['date'], groupby=['date:week'])
        self.assertDictEqual(
            {week['date:week']: week['date_count'] for week in groups if week['date:week']},
            self.per_locale["fr_BE"],
            "Week groups not matching when the first day of the week is Monday"
        )

        # same test as above with week_number as aggregate
        groups = self.Model.with_context(lang='fr_BE').read_group(
            [('id', 'in', self.records.ids)], fields=['date'], groupby=['date:iso_week_number'])
        self.assertDictEqual(
            {week['date:iso_week_number']: week['date_count'] for week in groups if week['date:iso_week_number']},
            self.iso_weeks,
            "Week groups not matching when the first day of the week is Monday"
        )

    def test_syria(self):
        """ ar_SY - first day of the week = Saturday """
        self.assertEqual(
            babel.Locale.parse("ar_SY").first_week_day,
            5,
        )
        self.env['res.lang']._activate_lang('ar_SY')
        groups = self.Model.with_context(lang='ar_SY').read_group(
            [('id', 'in', self.records.ids)], fields=['date'], groupby=['date:week'])
        self.assertDictEqual(
            {week['date:week']: week['date_count'] for week in groups if week['date:week']},
            self.per_locale["ar_SY"],
            "Week groups not matching when the first day of the week is Saturday"
        )

        # same test as above with week_number as aggregate
        groups = self.Model.with_context(lang='ar_SY').read_group(
            [('id', 'in', self.records.ids)], fields=['date'], groupby=['date:iso_week_number'])
        self.assertDictEqual(
            {week['date:iso_week_number']: week['date_count'] for week in groups if week['date:iso_week_number']},
            self.iso_weeks,
            "Week groups not matching when the first day of the week is Saturday"
        )

    def test_united_states(self):
        """ en_US - first day of the week = Sunday """
        self.assertEqual(
            babel.Locale.parse("en_US").first_week_day,
            6,
        )
        groups = self.Model.with_context(lang='en_US').read_group(
            [('id', 'in', self.records.ids)], fields=['date'], groupby=['date:week'])
        self.assertDictEqual(
            {week['date:week']: week['date_count'] for week in groups if week['date:week']},
            self.per_locale["en_US"],
            "Week groups not matching when the first day of the week is Sunday"
        )

        # same test as above with week_number as aggregate
        groups = self.Model.with_context(lang='en_US').read_group(
            [('id', 'in', self.records.ids)], fields=['date'], groupby=['date:iso_week_number'])
        self.assertDictEqual(
            {week['date:iso_week_number']: week['date_count'] for week in groups if week['date:iso_week_number']},
            self.iso_weeks,
            "Week groups not matching when the first day of the week is Sunday"
        )
