# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.tests.common import HttpCase, tagged
from odoo.tools import html2plaintext


@tagged('-at_install', 'post_install')
class TestWebsiteProject(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_project = cls.env['project.project'].create({'name': 'Project_1'})
        cls.test_partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
            'email': 'test@partner.com',
        })

    def test_portal_task_submission(self):
        """ Public user should be able to submit a task"""
        self.authenticate(None, None)
        task_data = {
            'name': "test_task_portal",
            'email_from': 'test@test.com',
            'description': 'This test task is created by Portal',
            'project_id': self.test_project.id,
            'csrf_token': http.Request.csrf_token(self),
            'partner_phone': '+5 555-555-555',
            'partner_name': 'Bagha kumar',
            'partner_company_name': 'Boulangerie Vortex',
        }
        response = self.url_open('/website/form/project.task', data=task_data)
        task = self.env['project.task'].browse(response.json().get('id'))
        self.assertTrue(task.exists())
        self.assertFalse(task.partner_id, "Partner id should be False")
        self.assertEqual(task.email_cc, 'test@test.com', "email_cc should be same as added on website")
        self.assertIn('EXTERNAL SUBMISSION - Customer not verified', html2plaintext(task.description), "Warning message should be displayed in description of task")

        mail_message = task.message_ids.filtered(lambda m: m.body == '<div class="alert alert-info">/!\\ EXTERNAL SUBMISSION - Customer not verified</div>')
        self.assertEqual(len(mail_message), 1, "Alert message should be displayed in the chatter of the task created.")
        self.assertEqual(mail_message.author_id, self.env.ref('base.partner_root'), 'The author of the warning message should be OdooBot.')

    def test_admin_task_submission(self):
        """ Admin should be able to submit a task"""
        self.authenticate("admin", "admin")
        task_data = {
            'name': "test_task_admin",
            'email_from': 'test@partner.com',
            'description': 'This test task is created by Admin',
            'project_id': self.test_project.id,
            'csrf_token': http.Request.csrf_token(self),
            'partner_phone': '+5 555-555-555',
            'partner_name': 'Bagha kumar',
            'partner_company_name': 'Boulangerie Vortex',
        }
        response = self.url_open('/website/form/project.task', data=task_data)
        task = self.env['project.task'].browse(response.json().get('id'))
        self.assertTrue(task.exists())
        self.assertEqual(task.partner_id, self.test_partner, "Partner id should not be False")
        self.assertFalse(task.email_cc, "email_cc field should be empty")
        admin_user = self.env.ref('base.user_admin')
        asserttext = '%s (%s)' % (admin_user.name, admin_user.email)
        self.assertIn('This Task was submitted by %s on behalf of test@partner.com' % asserttext, html2plaintext(task.description), "Warning message should be displayed in description of task")

        mail_message = task.message_ids.filtered(lambda m: m.body == '<div class="alert alert-info">This Task was submitted by %s on behalf of test@partner.com</div>' % asserttext)
        self.assertEqual(len(mail_message), 1, "Alert message should be displayed in the chatter of the task created.")
