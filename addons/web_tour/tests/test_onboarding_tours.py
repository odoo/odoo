# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestOnboardingTours(HttpCase):

    tour_names = ['hr_expense_tour']

    def _get_tours(self):
        return self.env['web_tour.tour'].search([('name', 'in', self.tour_names)])

    def test_onboarding_tours(self):
        for tour in self._get_tours():
            with self.subTest(tour_name=tour.name):
                self.start_tour(tour.url or '/odoo', tour.name, login="admin")

    def test_onboarding_tours_mobile(self):
        for tour in self._get_tours():
            with self.subTest(tour_name=tour.name):
                self.start_tour(tour.url or '/odoo', tour.name, login="admin", mobile=True)
