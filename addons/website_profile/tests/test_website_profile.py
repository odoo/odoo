# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from datetime import date
from dateutil.relativedelta import relativedelta
import odoo.tests

from odoo.addons.gamification.tests.common import HttpCaseGamification
from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website_profile.controllers.main import WebsiteProfile


@odoo.tests.tagged('post_install', '-at_install')
class TestWebsiteProfile(HttpCaseGamification):
    def test_prepare_url_from_info(self):
        controller = WebsiteProfile()
        base_url = self.base_url()
        base_url_other = 'https://other-domain.com'
        no_url_from = {'url_from': None, 'url_from_label': None}
        for referer, expected in (
            ('/forum?p=1#f=2', {'url_from': '/forum?p=1#f=2', 'url_from_label': 'Forum'}),
            ('/forum/test?p=1#f=2', {'url_from': '/forum/test?p=1#f=2', 'url_from_label': 'Forum'}),
            ('/slides?p=1#f=2', {'url_from': '/slides?p=1#f=2', 'url_from_label': 'All Courses'}),

            ('/profile', no_url_from),
            (None, no_url_from),
        ):
            with (MockRequest(self.env, url_root=base_url, path='/profile/user/1') as mock_request,
                  self.subTest(referer=referer)):
                mock_request.httprequest.headers = {'Referer': f'{base_url}{referer}' if referer else None}
                expected_with_base_url = {
                    'url_from': f'{base_url}{expected["url_from"]}' if expected.get("url_from") else None,
                    'url_from_label': expected["url_from_label"],
                }
                self.assertEqual(controller._prepare_url_from_info(), expected_with_base_url)

                mock_request.httprequest.headers = {'Referer': f'{base_url_other}{referer}' if referer else None}
                self.assertEqual(controller._prepare_url_from_info(), {'url_from': None, 'url_from_label': None})

    def test_save_change_description(self):
        odoo.tests.new_test_user(
            self.env, 'test_user',
            karma=100, website_published=True
        )
        self.env.ref('base.user_admin').write({
            'email': 'mitchell.admin@example.com',
        })
        self.start_tour("/", 'website_profile_description', login="admin")

    @patch('odoo.addons.website_profile.controllers.main.WebsiteProfile._users_per_page', 2)
    def test_leaderboard_pagination_by_period(self):
        """Test that pagination works correctly when grouping by week/month/all."""
        users = self.env['res.users']
        for user_name in ['a', 'b', 'c', 'd']:
            users |= odoo.tests.new_test_user(
                self.env, f'test_user_{user_name}',
                name=f'Test User {user_name.upper()}',
                website_published=True,
            )
        user_a, user_b, user_c, user_d = users

        # Wipe any stray tracking in the DB to neutralize demo/admin users
        self.env['gamification.karma.tracking'].search([]).unlink()

        one_year_ago = date.today() - relativedelta(years=1)
        two_weeks_ago = date.today() - relativedelta(weeks=2)
        today = date.today()

        self.env['gamification.karma.tracking'].create([
            # User A: 40k gained 1 year ago (0 recent gain)
            {'user_id': user_a.id, 'old_value': 0, 'new_value': 40000, 'tracking_date': one_year_ago},
            # User B: 10k gained 1 year ago, 20k gained this month
            {'user_id': user_b.id, 'old_value': 0, 'new_value': 10000, 'tracking_date': one_year_ago},
            {'user_id': user_b.id, 'old_value': 10000, 'new_value': 30000, 'tracking_date': two_weeks_ago},
            # User C: 10k gained 1 year ago, 10k gained this week
            {'user_id': user_c.id, 'old_value': 0, 'new_value': 10000, 'tracking_date': one_year_ago},
            {'user_id': user_c.id, 'old_value': 10000, 'new_value': 20000, 'tracking_date': today},
            # User D: 10k gained 1 year ago, 5k gained this week
            {'user_id': user_d.id, 'old_value': 0, 'new_value': 10000, 'tracking_date': one_year_ago},
            {'user_id': user_d.id, 'old_value': 10000, 'new_value': 15000, 'tracking_date': today},
        ])

        test_cases = [
            # All Time Total Karma: A (40k), B (30k), C (20k), D (15k)
            ('/profile/users', [user_a, user_b]),
            ('/profile/users/page/2', [user_c, user_d]),

            # This Month Karma Gain: B (20k), C (10k), D (5k), A (0)
            ('/profile/users?group_by=month', [user_b, user_c]),
            ('/profile/users/page/2?group_by=month', [user_d]),

            # This Week Karma Gain: C (10k), D (5k), A (0), B (0)
            ('/profile/users?group_by=week', [user_c, user_d]),
            ('/profile/users/page/2?group_by=week', []),
        ]

        for url, expected_users in test_cases:
            with self.subTest(url=url):
                html = self.url_open(url).text
                for user in users:
                    if user in expected_users:
                        self.assertIn(user.name, html)
                    else:
                        self.assertNotIn(user.name, html)
