# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

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

    def test_onsite_event_created_from_action(self):
        """ Ensure that an onsite event created from the Onsite action is visible in its kanban view. """
        # The current user needs an employee, as the action does not give any in its context
        employee = self.env.user.employee_id or self.env['hr.employee'].create({
            'name': 'Onsite Action Employee',
            'user_id': self.env.user.id,
        })
        event = self.env['event.event'].with_context(hr_skills_event_add_employee=True).create({
            'name': 'Onsite Action Event',
        })
        self.assertEqual(
            event.registration_ids.partner_id, employee.work_contact_id,
            "The employee of the current user should be registered to the new event",
        )
        # The kanban of the action only shows the events having an employee registered
        onsite_action = self.env.ref('hr_skills_event.event_training_onsite_action')
        self.assertIn(
            event, self.env['event.event'].search(literal_eval(onsite_action.domain)),
            "The new event should appear in the onsite kanban view",
        )
