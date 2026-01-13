# Part of Odoo. See LICENSE file for full copyright and licensing details.

from re import search

from odoo import http
from odoo.tests import HttpCase

from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.project.tests.test_project_sharing import TestProjectSharingCommon
from odoo.addons.http_routing.tests.common import MockRequest


class TestProjectPortalAccess(TestProjectSharingCommon, HttpCase):
    def test_post_chatter_as_portal_user(self):
        self.project_no_collabo.privacy_visibility = 'portal'
        message = self.get_project_share_link()
        share_link = str(message.body.split('href="')[1].split('">')[0])
        match = search(r"access_token=([^&]+)&amp;pid=([^&]+)&amp;hash=([^&]*)", share_link)
        access_token, pid, _hash = match.groups()

        with self.with_user('chell'), MockRequest(self.env, path=share_link):
            ThreadController().mail_message_post(
                thread_model='project.task',
                thread_id=self.task_no_collabo.id,
                post_data={'body': '(-b ±√[b²-4ac]) / 2a'},
                token=access_token,
                pid=pid,
                hash=_hash,
            )

        self.assertTrue(
            self.env['mail.message'].sudo().search([
                ('author_id', '=', self.user_portal.partner_id.id),
            ])
        )

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
            'partner_phone': '+1234567',
            'partner_company_name': 'foo',
            'description': 'Fix this',
            'project_id': self.project_portal.id,
            'csrf_token': http.Request.csrf_token(self),
        }
        response = self.url_open('/website/form/project.task', data=ticket_data)
        task = self.env['project.task'].browse(response.json().get('id'))
        self.assertTrue(task.exists())
        self.assertEqual(partner.name, 'Jean Michel')
