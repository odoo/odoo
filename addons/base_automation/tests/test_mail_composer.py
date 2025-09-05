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
        automation.write({'action_server_ids': [(4, server_action.id)]})
        partner = self.env["res.partner"].create({"name": "Jane", "email": "jane@example.com"})
        user_partner = self.env["res.partner"].create({"name": "Not A Demo User", "email":  "NotADemoUser@mail.com"})
        user = self.env["res.users"].create({
            "name": "Not A Demo User",
            "login": "nadu",
            "partner_id": user_partner.id
        })
        partner.message_subscribe(partner_ids=[self.user_admin.partner_id.id])
        with self.mock_mail_app():
            self.start_tour(
                f"/odoo/res.partner/{partner.id}",
                "mail/static/tests/tours/mail_composer_test_tour.js",
                login=self.user_employee.login
            )
        messages = self._new_msgs.filtered(lambda message: message.author_id == self.user_employee.partner_id)
        self.assertEqual(len(messages), 3)
        self.assertIn(user.partner_id, messages[0].partner_ids)

    def test_mail_html_composer_test_tour(self):
        self.env['mail.template'].create({
            'auto_delete': True,
            'lang': '{{ object.lang }}',
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'name': 'Test template',
            'partner_to': '{{ object.id }}',
        })

        automation = self.env['base.automation'].create({
            'name': 'Test',
            'active': True,
            'trigger': 'on_change',
            'on_change_field_ids': (4, self.ref('mail.field_mail_compose_message__template_id')),
            'model_id': self.env.ref('mail.model_mail_compose_message').id,
        })
        server_action = self.env['ir.actions.server'].create({
            'name': 'Test',
            'base_automation_id': automation.id,
            'state': 'code',
            'model_id': self.env.ref('mail.model_mail_compose_message').id,
        })
        automation.write({'action_server_ids': [(4, server_action.id)]})
        partner = self.env["res.partner"].create({"name": "Jane", "email": "jane@example.com"})
        partner.message_subscribe(partner_ids=[self.user_admin.partner_id.id])
        with self.mock_mail_app():
            self.start_tour(
                f"/odoo/res.partner/{partner.id}",
                "mail/static/tests/tours/mail_html_composer_test_tour.js",
                login=self.user_employee.login,
            )
