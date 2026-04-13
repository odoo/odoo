# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestOnsite(HttpCase):
    def test_onsite_employee_registration(self):
        self.env['hr.employee'].create({
            'name': 'Test Employee',
        })
        # We create this event to check that only events with employees registered are proposed in the resume line form view
        self.env['event.event'].create({
            'name': 'Test Event',
        })
        self.start_tour("/odoo", 'hr_skills_event_onsite_tour', login='admin')
