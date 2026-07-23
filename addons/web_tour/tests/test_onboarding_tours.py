# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestOnboardingTours(HttpCase):

    tour_names = ['hr_expense_tour', 'event_tour']

    def setUp(self):
        super().setUp()
        # Email company is always set on a configured instance
        self.env.ref('base.main_company').email = 'admin@yourcompany.example.com'

    def _get_tours(self):
        tours = self.env['web_tour.tour'].search([('name', 'in', self.tour_names)])
        self.assertEqual(
            len(tours), len(self.tour_names),
            "Some onboarding tours were not found: is the module that defines them installed?",
        )
        return tours

    def test_onboarding_tours(self):
        for tour in self._get_tours():
            with self.subTest(tour_name=tour.name):
                self.start_tour(tour.url or '/odoo', tour.name, login="admin")

    def test_onboarding_tours_mobile(self):
        self.browser_size = '375x667'
        self.touch_enabled = True
        for tour in self._get_tours():
            with self.subTest(tour_name=tour.name):
                self.start_tour(tour.url or '/odoo', tour.name, login="admin")
