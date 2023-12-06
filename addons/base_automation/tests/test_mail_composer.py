# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import tagged, HttpCase


@tagged('-at_install', 'post_install', 'mail_composer')
class TestMailFullComposer(MailCommon, HttpCase):

    def test_mail_composer_test_tour(self):
        self.env['mail.template'].create({
            'auto_delete': True,
            'lang': '{{ object.lang }}',
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'name': 'Test template',
            'partner_to': '{{ object.id }}',
        })
<<<<<<< HEAD
        self.user_employee.write({
            'groups_id': [(4, self.env.ref('base.group_partner_manager').id)],
||||||| parent of e443e0e9f3e9 (temp)
        test_user = self.env['res.users'].create({
            'email': 'testuser@testuser.com',
            'groups_id': [
                (6, 0, [self.ref('base.group_user'), self.ref('base.group_partner_manager')]),
            ],
            'name': 'Test User',
            'login': 'testuser',
            'password': 'testuser',
=======
        user = self.env['res.users'].create({
            'email': 'testuser@testuser.com',
            'groups_id': [
                (6, 0, [self.ref('base.group_user'), self.ref('base.group_partner_manager')]),
            ],
            'name': 'Test User',
            'login': 'testuser',
            'password': 'testuser',
>>>>>>> e443e0e9f3e9 (temp)
        })

        automation = self.env['base.automation'].create({
            'name': 'Test',
            'active': True,
            'trigger': 'on_change',
            'on_change_field_ids': (4, self.ref('mail.field_mail_compose_message__template_id'),),
            'model_id': self.env.ref('mail.model_mail_compose_message').id,
        })
        server_action = self.env['ir.actions.server'].create({
            'name': 'Test',
            'base_automation_id': automation.id,
            'state': 'code',
            'model_id': self.env.ref('mail.model_mail_compose_message').id,
        })
<<<<<<< HEAD
        automation.write({'action_server_ids': [(4, server_action.id)]})
        partner = self.env["res.partner"].create({"name": "Jane", "email": "jane@example.com"})
        user = self.env["res.users"].create({"name": "Not A Demo User", "login": "nadu"})
        with self.mock_mail_app():
            self.start_tour(
                f"/web#id={partner.id}&model=res.partner",
                "mail/static/tests/tours/mail_composer_test_tour.js",
                login=self.user_employee.login
            )
        message = self._new_msgs.filtered(lambda message: message.author_id == self.user_employee.partner_id)
        self.assertEqual(len(message), 1)
        self.assertIn(user.partner_id, message.partner_ids)
||||||| parent of e443e0e9f3e9 (temp)

        self.start_tour("/web#id=%d&model=res.partner" % test_user.partner_id, 'mail/static/tests/tours/mail_full_composer_test_tour.js', login='testuser')

        automated_action.unlink()
=======
        partner = self.env["res.partner"].create({"name": "Jane", "email": "jane@example.com"})
        with self.mock_mail_app():
            self.start_tour(f"/web#id={partner.id}&model=res.partner", 'mail/static/tests/tours/mail_full_composer_test_tour.js', login='testuser')
        message = self._new_msgs.filtered(lambda message: message.author_id == user.partner_id)
        self.assertEqual(len(message), 1)
        automated_action.unlink()
>>>>>>> e443e0e9f3e9 (temp)
