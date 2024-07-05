# Part of Odoo. See LICENSE file for full copyright and licensing details.

from re import search

from odoo import Command
from odoo.tests import HttpCase

from odoo.addons.portal.controllers.mail import PortalChatter
from odoo.addons.project.tests.test_project_sharing import TestProjectSharingCommon
from odoo.addons.website.tools import MockRequest


class TestProjectPortalAccess(TestProjectSharingCommon, HttpCase):
    def test_post_chatter_as_portal_user(self):
        self.env['project.share.wizard'].create({
            'res_model': 'project.project',
            'res_id': self.project_no_collabo.id,
            'access_mode': 'edit',
            'partner_ids': [Command.set([self.user_portal.partner_id.id])],
        }).action_send_mail()
        message = self.env['mail.message'].search([
            ('partner_ids', 'in', self.user_portal.partner_id.id),
        ])

        share_link = str(message.body.split('href="')[1].split('">')[0])
        match = search(r"access_token=([^&]+)&amp;pid=([^&]+)&amp;hash=([^&]*)", share_link)
        access_token, pid, _hash = match.groups()

        with self.with_user('chell'), MockRequest(self.env, path=share_link):
            PortalChatter().portal_chatter_post(
                res_model='project.task',
                res_id=self.task_no_collabo.id,
                message='(-b ±√[b²-4ac]) / 2a',
                attachment_ids=None,
                attachment_tokens=None,
                token=access_token,
                pid=pid,
                hash=_hash,
            )

        self.assertTrue(
            self.env['mail.message'].sudo().search([
                ('author_id', '=', self.user_portal.partner_id.id),
            ])
        )
