# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import tagged, HttpCase
from odoo import Command


@tagged('-at_install', 'post_install', 'mail_composer')
class TestMailFullComposer(MailCommon, HttpCase):

    def test_full_composer_tour(self):
        self.env['mail.template'].create({
            'name': 'Test template',
            'partner_to': '{{ object.id }}',
            'lang': '{{ object.lang }}',
            'auto_delete': True,
            'model_id': self.ref('base.model_res_partner'),
        })
        user = self.env['res.users'].create({
            'email': 'testuser@testuser.com',
            'groups_id': [Command.set([self.ref('base.group_user'), self.ref('base.group_partner_manager')])],
            'name': 'Test User',
            'login': 'testuser',
            'password': 'testuser',
        })
        partner = self.env["res.partner"].create({"name": "Jane", "email": "jane@example.com"})
        with self.mock_mail_app():
            self.start_tour(f"/web#id={partner.id}&model=res.partner", 'mail/static/tests/tours/mail_full_composer_test_tour.js', login='testuser')
        message = self._new_msgs.filtered(lambda message: message.author_id == user.partner_id)
        self.assertEqual(len(message), 1)
