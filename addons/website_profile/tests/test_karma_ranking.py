# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.gamification.tests.common import TransactionCaseKarmaTracking
from odoo.tests import new_test_user, tagged


@tagged('post_install', '-at_install')
class TestKarmaRanking(TransactionCaseKarmaTracking):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['gamification.karma.tracking'].search([]).unlink()
        cls.user_a = new_test_user(cls.env, 'test_ranking_a', website_published=True)
        cls.user_b = new_test_user(cls.env, 'test_ranking_b', website_published=True)

        cls.test_date = datetime(2021, 6, 1)
        cls._create_trackings(cls.user_a, 10, 20, cls.test_date, days_delta=2)
        cls._create_trackings(cls.user_b, 20, 2, cls.test_date, days_delta=30)
        cls._create_trackings(cls.user_b, -5, 1, cls.test_date + relativedelta(months=2))

    def test_get_users_karma_ranking(self):
        user_a, user_b = self.user_a, self.user_b

        # Format: (kwargs, {user_id: (expected_position, expected_gain, expected_in_page)})
        test_cases = [
            # all time: ranked on total karma
            ({}, {
                user_a.id: (1, 200, True),
                user_b.id: (2, 35, True),
            }),
            ({'to_date': self.test_date + relativedelta(day=2)}, {
                user_b.id: (1, 20, True),
                user_a.id: (2, 10, True),
            }),
            ({'from_date': self.test_date + relativedelta(months=1)}, {
                user_a.id: (1, 50, True),
                user_b.id: (2, 15, True),
            }),
            ({'from_date': self.test_date + relativedelta(months=1), 'limit': 1, 'offset': 1}, {
                user_b.id: (2, 15, True),
            }),
            # no karma change in the timeframe: still ranked, with a gain of 0
            ({'from_date': self.test_date + relativedelta(months=1, day=2),
              'to_date': self.test_date + relativedelta(months=1, day=31)}, {
                user_a.id: (1, 40, True),
                user_b.id: (2, 0, True),
            }),
            # same gain: ranked on total karma
            ({'from_date': self.test_date + relativedelta(months=1, day=10),
              'to_date': self.test_date + relativedelta(months=1, day=31)}, {
                user_a.id: (1, 0, True),
                user_b.id: (2, 0, True),
            }),
            # karma lost in the timeframe: ranked after users without change
            ({'from_date': self.test_date + relativedelta(months=2)}, {
                user_a.id: (1, 0, True),
                user_b.id: (2, -5, True),
            }),
            # always included user outside of the page: returned anyway
            ({'limit': 1, 'always_include_user_ids': [user_b.id]}, {
                user_a.id: (1, 200, True),
                user_b.id: (2, 35, False),
            }),
            # always included user already in the page: returned as part of it
            ({'limit': 2, 'always_include_user_ids': [user_b.id]}, {
                user_a.id: (1, 200, True),
                user_b.id: (2, 35, True),
            }),
            # several always included users, in and out of the page
            ({'limit': 1, 'offset': 1, 'always_include_user_ids': [user_a.id, user_b.id]}, {
                user_a.id: (1, 200, False),
                user_b.id: (2, 35, True),
            }),
            # always included user not matching the search: not returned
            ({'search_domain': [('id', '=', user_a.id)], 'always_include_user_ids': [user_b.id]}, {
                user_a.id: (1, 200, True),
            }),
            # search: positions stay those of the whole ranking, pagination is done on the search results
            ({'search_domain': [('id', '=', user_b.id)]}, {
                user_b.id: (2, 35, True),
            }),
            ({'search_domain': [('id', '=', user_a.id)], 'to_date': self.test_date + relativedelta(day=2), 'limit': 1}, {
                user_a.id: (2, 10, True),
            }),
            ({'search_domain': [('id', '=', user_b.id)], 'limit': 1, 'offset': 1}, {}),
        ]

        for kwargs, expected in test_cases:
            with self.subTest(**kwargs):
                results = self.env['res.users']._get_users_karma_ranking(**kwargs)
                self.assertEqual(list(results), list(expected), "Users should be returned ordered by position")
                for user_id, (expected_position, expected_gain, expected_in_page) in expected.items():
                    self.assertEqual(results[user_id]['karma_position'], expected_position)
                    self.assertEqual(results[user_id]['karma_gain'], expected_gain)
                    self.assertEqual(results[user_id]['in_page'], expected_in_page)
