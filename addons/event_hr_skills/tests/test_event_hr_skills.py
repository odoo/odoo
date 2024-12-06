from odoo.tests import common
from odoo import Command
from datetime import date

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
        cls.event_line_type = cls.env.ref('event_hr_skills.resume_type_events')

    def _event_resume_lines(self, employee):
        return employee.resume_line_ids.filtered(lambda l: l.line_type_id == self.event_line_type)

    def test_attending_creates_resume_line(self):
        """ Check an employee attends a ``show_on_resume`` tagged event,
            a resume line is created.
        """

        registration = self.env['event.registration'].create({
            'event_id': self.frobination_training.id,
            'partner_id': self.alice.work_contact_id.id,
        })
        registration.action_set_done()

        self.assertEqual(1, len(self._event_resume_lines(self.alice)))
        self.assertEqual(self._event_resume_lines(self.alice)[0].name, self.frobination_training.name)
        self.assertEqual(self._event_resume_lines(self.alice)[0].line_type_id.id, self.env['hr.resume.line'].get_event_type_id())

    def test_action_register_employee(self):
        """ Test that the action (used on resumes) create *both*
            a resume line and an event registration
        """
        self.frobination_training.with_context(active_employee_id=self.alice.id).action_register_employee()

        self.assertEqual(1, len(self._event_resume_lines(self.alice)))
        self.assertEqual(self._event_resume_lines(self.alice)[0].name, self.frobination_training.name)
        self.assertEqual(self._event_resume_lines(self.alice)[0].line_type_id.id, self.env['hr.resume.line'].get_event_type_id())

        registration = self.env['event.registration'].search([
            ('event_id', '=', self.frobination_training.id),
            ('partner_id', '=', self.alice.work_contact_id.id),
        ])
        self.assertEqual(len(registration), 1)

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
