# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import common

class TestEventHrSkills(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.alice = cls.env['hr.employee'].create({
            'name': 'Alice',
            'email': 'alice@example.com',
        })
        cls.training_category_tag = cls.env['event.tag.category'].create({
            'name': 'Training',
            'show_on_resume': True,
            'tag_ids': [
                Command.create({'name': 'Sponsored MOOC'}),
                Command.create({'name': 'Internal Training'}),
            ],
        })
        cls.training_tag = cls.training_category_tag.tag_ids[1]
        cls.frobination_training = cls.env['event.event'].create({
            'name': 'Frobination Training',
            'tag_ids': [Command.link(cls.training_tag.id)]
        })

    def _register_employee(self, employee=None, event=None):
        employee = employee or self.alice
        event = event or self.frobination_training

        registration = self.env['event.registration'].create({
            'event_id': event.id,
            'partner_id': employee.work_contact_id.id,
        })
        registration.action_set_done()
        return registration

    def test_attending_creates_resume_line(self):
        """ Check if an employee attends a ``show_on_resume`` tagged event,
            a resume line is created.
        """
        registration = self.env['event.registration'].create({
            'event_id': self.frobination_training.id,
            'partner_id': self.alice.work_contact_id.id,
        })
        self.assertEqual(0, len(registration.resume_line_ids))
        registration.action_set_done()

        self.assertEqual(1, len(registration.resume_line_ids))
        line = registration.resume_line_ids[0]
        self.assertEqual(line.name, self.frobination_training.name)
        self.assertEqual(line.employee_id, self.alice)
        self.assertEqual(line.event_id, self.frobination_training)

    def test_creating_resume_line_creates_registration(self):
        self.env['hr.resume.line'].create({
            'employee_id': self.alice.id,
            'name': "Attended Frobination Training",
            'date_start': date(2024, 1, 1),
            'event_id': self.frobination_training.id,
        })

        registration = self.env['event.registration'].search([
            ('event_id', '=', self.frobination_training.id),
            ('partner_id', '=', self.alice.work_contact_id.id),
        ])
        self.assertEqual(len(registration), 1)

    def test_show_on_resume(self):
        """ Check that un/setting the ``show_on_resume`` field affects the line
        """
        registration = self._register_employee()

        self.training_category_tag.show_on_resume = False
        self.assertEqual(0, len(registration.resume_line_ids), "Resume line should have been deleted")

        self.training_category_tag.show_on_resume = True
        self.assertEqual(1, len(registration.resume_line_ids))

    def test_tag_ids(self):
        """ Check that modifying the tag_ids affects the line
        """
        registration = self._register_employee()

        self.frobination_training.tag_ids = self.env['event.tag']
        self.assertEqual(0, len(registration.resume_line_ids), "Resume line should have been deleted")

        self.frobination_training.tag_ids = self.training_tag
        self.assertEqual(1, len(registration.resume_line_ids))

    def test_registration_state(self):
        """ Check that setting the state of a registration to anything other
            than 'done' or deleting it affects the line.
        """
        registration = self._register_employee()

        registration.state = 'open'
        self.assertEqual(0, len(registration.resume_line_ids), "Resume line should have been deleted")

        registration.state = 'done'
        self.assertEqual(1, len(registration.resume_line_ids))

        registration.unlink()
        resume_lines =  self.env['hr.resume.line'].search([
            ('employee_id', '=', self.alice.id),
            ('event_id', '=', self.frobination_training.id),
        ])
        self.assertEqual(0, len(resume_lines), "Resume line should have been deleted")

    def test_error_on_change_event(self):
        registration = self._register_employee()
        with self.assertRaises(UserError):
            registration.resume_line_ids[0].event_id = False
