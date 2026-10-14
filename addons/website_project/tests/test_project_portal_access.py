# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from re import search

from odoo.tests import tagged, HttpCase

from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.project.tests.test_project_sharing import TestProjectSharingCommon
from odoo.addons.website_project.controllers.main import WebsiteForm
from odoo.addons.http_routing.tests.common import MockRequest


class TestProjectPortalAccess(TestProjectSharingCommon, HttpCase):
    def test_post_chatter_as_portal_user(self):
        self.project_no_collabo.privacy_visibility = 'portal'

        # With user collaborator
        message = self.get_project_share_link()
        share_link = str(message.body.split('href="')[1].split('">')[0])
        match = search(r"redirect=([^&]+)", share_link)
        redirect = match.groups()

        with self.with_user('chell'), MockRequest(self.env, path=share_link):
            ThreadController().mail_message_post(
                thread_model='project.task',
                thread_id=self.task_no_collabo.id,
                post_data={'body': '(-b ±√[b²-4ac]) / 2a'},
                redirect=redirect
            )

        self.assertTrue(
            self.env['mail.message'].sudo().search([
                ('author_id', '=', self.user_portal.partner_id.id),
            ])
        )

        # With non-user collaborator
        partner = self.env['res.partner'].create({
            'name': 'Test',
            'email': 'test@example.portal',
            'company_id': False,
        })
        message = self.get_project_share_link_partner(partner)
        share_link = str(message.body.split('href="')[1].split('">')[0])
        match = search(r"token=([^&]+)&amp;redirect=([^&]+)", share_link)
        token, redirect = match.groups()
        self.assertTrue(token, 'Token must be present for the signup')

    def test_portal_task_submission(self):
        """ Public user should be able to submit a task"""
        self.authenticate(None, None)
        partner = self.env['res.partner'].create({
            'name': 'Jean Michel',
            'email': 'jean@michel.com',
        })
        ticket_data = {
            'name': 'FIX',
            'partner_name': 'Not Jean Michel',
            'email_from': 'jean@michel.com',
            'partner_company_name': 'foo',
            'description': 'Fix this',
            'project_id': self.project_portal.id,
            'csrf_token': self.csrf_token(),
        }
        response = self.url_open('/website/form/project.task', data=ticket_data)
        task = self.env['project.task'].browse(response.json().get('id'))
        self.assertTrue(task.exists())
        self.assertEqual(partner.name, 'Jean Michel')
        # The description should not contain the partner_phone since it was not provided
        self.assertEqual(str(task.description), ('<p>Fix this</p><h4>Other Information</h4>Email : jean@michel.com<br>\n'
            'partner_name : Not Jean Michel<br>\npartner_company_name : foo'))

    def test_portal_task_submission_without_existing_partner_email(self):
        """
        Test the creation of a project task via the website form when the
        provided email does not match any existing partner.
        """
        ticket_data = {
            'name': 'FIX',
            'partner_name': 'Test demo',
            'email_from': 'test@demo.com',
            'description': 'Fix this',
            'project_id': self.project_portal.id,
        }
        response = self.url_open('/website/form/project.task', data=ticket_data)
        self.assertEqual(response.status_code, 200)

        task = self.env['project.task'].browse(response.json().get('id'))
        self.assertTrue(task.exists())
        self.assertEqual(task.name, ticket_data['name'])
        self.assertEqual(task.email_from, ticket_data['email_from'])

    def test_task_submission_does_not_overwrite_existing_partner(self):
        """ Submitting a task via Contact Us with new visitor data should not
            overwrite the name (or other fields) of the project's existing partner.
        """
        self.authenticate(None, None)
        self.project_portal.partner_id = self.partner_1
        task_data = {
            'name': 'New Task From Website',
            'partner_name': 'TEST',
            'email_from': 'test_new_visitor@unknown.com',
            'description': 'Hello',
            'project_id': self.project_portal.id,
            'csrf_token': self.csrf_token(),
        }
        response = self.url_open('/website/form/project.task', data=task_data)
        new_task = self.env['project.task'].browse(response.json().get('id'))
        self.assertTrue(new_task.exists())
        self.assertFalse(new_task.partner_id)
        # the existing partner must NOT be renamed
        self.assertEqual(self.partner_1.name, 'Valid Lelitre')
        # The project's partner must remain unchanged
        self.assertEqual(self.project_portal.partner_id.name, 'Valid Lelitre')

    def test_task_submission_partner_phone(self):
        """ Submitting a task via Contact Us should set the value of partner_phone ONLY IF :
        - It creates a new partner
        - The associated partner is the currently connected user
        """
        self.authenticate(None, None)

        def create_users():
            users = self.env['res.users'].create([
                {
                    'name': 'Jean Michel',
                    'login': 'jean@michel.com',
                },
                {
                    'name': 'Marie Dubois',
                    'login': 'marie@dubois.com',
                }
            ])
            for user in users:
                user.partner_id.email = user.login
            users[0].partner_id.phone = '12345'
            return users
        test_cases = [
            # Public user with already existing partner's email => In description
            (-1, 'jean@michel.com', 'description'),
            # Partner with its own email => In partner_phone
            (0, 'jean@michel.com', 'partner_phone'),
            # Partner with another partner's email => In description
            (1, 'jean@michel.com', 'description'),
            # Public user with a new email => In partner_phone
            (-1, 'new@email.com', 'partner_phone'),
        ]
        task_data = {
            'name': 'New Task From Website',
            'partner_name': 'Jean Michel',
            'partner_phone': '6789',
            'description': 'Hello',
            'project_id': str(self.project_portal.id),
        }
        WebsiteFormController = WebsiteForm()
        for user_index, email, phone_field in test_cases:
            users = create_users()
            user = self.user_public if user_index < 0 else users[user_index]
            with self.subTest(user=user, email=email, phone_field=phone_field):
                with (
                    self.env.registry.cursor() as test_cr,
                    MockRequest(self.env(cr=test_cr, user=user)) as request,
                ):
                    # The email_normalized of the partners don't seem to
                    # be properly computed in the form processing if we don't do this
                    self.env['res.partner'].sudo().search([('email_normalized', '=', 'a')])
                    request.params = {
                        'email_from': email,
                        'model_name': 'project.task',
                        **task_data
                    }
                    response = WebsiteFormController.website_form('project.task', **task_data)
                    new_task = self.env['project.task'].browse(json.loads(response.data).get('id'))
                self.assertTrue(new_task.exists())
                if phone_field == 'partner_phone':
                    self.assertEqual(new_task.partner_phone, '6789')
                else:
                    self.assertIn('phone : 6789', str(new_task.description))
                    new_task.invalidate_recordset(['partner_phone'])
                    self.assertEqual(new_task.partner_phone, '12345')
            users.unlink()
