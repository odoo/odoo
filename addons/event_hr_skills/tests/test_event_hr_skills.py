# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.event.tests.common import EventCase
from odoo.tests import users


class TestEventHrSkills(EventCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_contact = cls.env['res.partner'].create({'name': 'Bob'})
        cls.test_employee = cls.env['hr.employee'].create({
            'name': 'Alice',
            'email': 'alice@example.com',
        })
        cls.test_category_tag = cls.env['event.tag.category'].create({
            'name': 'Training',
            'hr_resume_line_type_id': cls.env.ref('hr_skills.resume_type_experience').id,
            'tag_ids': [
                Command.create({'name': 'Sponsored MOOC'}),
                Command.create({'name': 'Internal Training'}),
            ],
        })
        cls.test_tag = cls.test_category_tag.tag_ids[1]
        cls.test_event = cls.env['event.event'].create({
            'name': 'Frobination Training',
            'tag_ids': [Command.link(cls.test_tag.id)]
        })

    @users('admin', 'user_eventmanager')
    def test_attending_creates_resume_line(self):
        registrations = self._create_registrations(self.test_event, 3).with_env(self.env)
        registrations[0].partner_id = self.test_employee.work_contact_id.id
        registrations[1].partner_id = self.test_contact
        registrations.state = 'done'

        resume_line = self.env['hr.resume.line'].search([('event_id', '=', self.test_event.id)])
        self.assertEqual(len(resume_line), 1, "Should have created a resume line for the event")
        self.assertEqual(resume_line.line_type_id, self.env.ref('hr_skills.resume_type_experience'), "resume section should be determined by the event category")
        self.assertEqual(resume_line.employee_id, self.test_employee, "resume line should be on the correct employee")

    @users('admin', 'user_eventmanager')
    def test_creating_done_registrations_creates_resume_lines(self):
        self.env['event.registration'].create([{
            'event_id': self.test_event.id,
            'name': f'Test registration {i}',
            'partner_id': partner_id,
            'state': 'done',
        } for i, partner_id in enumerate([
            self.test_employee.work_contact_id.id,
            self.test_contact.id,
            False,
        ])])

        resume_line = self.env['hr.resume.line'].search([('event_id', '=', self.test_event.id)])
        self.assertEqual(len(resume_line), 1, "Should have created a resume line for the event")
        self.assertEqual(resume_line.line_type_id, self.env.ref('hr_skills.resume_type_experience'), "resume section should be determined by the event category")
        self.assertEqual(resume_line.employee_id, self.test_employee, "resume line should be on the correct employee")
