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
        if not tours:
            # web_tour only depends on web: the modules defining these onboarding
            # tours (e.g. hr_expense, event) may not be installed in every build.
            self.skipTest("None of the onboarding tours were found: are the modules that define them installed?")
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
