# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import common


class TestGroupbyWeek(common.TransactionCase):
    """ Test for read_group() with group by week: the first day of the week
    depends on the language.
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Model = cls.env['test_read_group.fill_temporal']
        cls.records = cls.Model.create([  # BE,  SY,  US
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
        self.env['res.lang']._activate_lang('fr_BE')
        groups = self.Model.with_context(lang='fr_BE').read_group(
            [('id', 'in', self.records.ids)], fields=['date'], groupby=['date:week'])
        self.assertDictEqual(
            {week['date:week']: week['date_count'] for week in groups if week['date:week']},
            {
                'W21 2022': 3,
                'W22 2022': 1,
                'W24 2022': 2,
                'W25 2022': 1,
            },
            "Week groups not matching when the first day of the week is Monday"
        )

    def test_syria(self):
        """ ar_SY - first day of the week = Saturday """
        self.env['res.lang']._activate_lang('ar_SY')
        groups = self.Model.with_context(lang='ar_SY').read_group(
            [('id', 'in', self.records.ids)], fields=['date'], groupby=['date:week'])
        self.assertDictEqual(
            {week['date:week']: week['date_count'] for week in groups if week['date:week']},
            {
                'W21 2022': 1,
                'W22 2022': 3,
                'W25 2022': 3,
            },
            "Week groups not matching when the first day of the week is Saturday"
        )

    def test_united_states(self):
        """ en_US - first day of the week = Sunday """
        groups = self.Model.with_context(lang='en_US').read_group(
            [('id', 'in', self.records.ids)], fields=['date'], groupby=['date:week'])
        self.assertDictEqual(
            {week['date:week']: week['date_count'] for week in groups if week['date:week']},
            {
                'W22 2022': 2,
                'W23 2022': 2,
                'W25 2022': 1,
                'W26 2022': 2,
            },
            "Week groups not matching when the first day of the week is Sunday"
        )
