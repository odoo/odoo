# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib

from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestOnboardingTours(HttpCase):

    tour_names = [
        'event_tour', 'discuss_channel_tour',
        'sale_tour', 'purchase_tour', 'mass_mailing_tour',
        'frontdesk_tour', 'hr_expense_extract_tour', 'appointment_tour',
        'sale_subscription_tour', 'project_tour', 'helpdesk_tour',
        'crm_tour',
    ]

    def setUp(self):
        super().setUp()
        # Company and admin emails are always set on a configured instance
        self.env.ref('base.main_company').email = 'company@example.com'
        self.env.ref('base.user_admin').email = 'admin@example.com'

    def _get_tours(self, exclude=()):
        names = [n for n in self.tour_names if n not in exclude]
        tours = self.env['web_tour.tour'].search([('name', 'in', names)])
        if not tours:
            # web_tour only depends on web: the modules defining these onboarding
            # tours (e.g. hr_expense, event) may not be installed in every build.
            self.skipTest("None of the onboarding tours were found: are the modules that define them installed?")
        return tours

    def test_onboarding_tours(self):
        for tour in self._get_tours():
            with self.subTest(tour_name=tour.name), contextlib.closing(self.env.cr.savepoint()):
                code = f"odoo.startTour({tour.name!r}, {{'mode': 'manual', 'robot': true}})"
                self.start_tour(tour.url or '/odoo', tour.name, code=code, login="admin")
