# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import users
from odoo.addons.mail.tests.common import MailCommon


class TestMailComposer(MailCommon):
    @classmethod
    def setUpClass(cls):
        super(TestMailComposer, cls).setUpClass()
        cls.env['ir.config_parameter'].set_param('mail.restrict.template.rendering', True)
        cls.user_employee.groups_id -= cls.env.ref('mail.group_mail_template_editor')
        cls.test_record = cls.env['res.partner'].with_context(cls._test_context).create({
            'name': 'Test',
        })
        cls.body_html = """<div>
    <h1>Hello sir!</h1>
    <p>Here! <a href="https://www.example.com">
        <!--[if mso]>
            <i style="letter-spacing: 25px; mso-font-width: -100%; mso-text-raise: 30pt;">&nbsp;</i>
        <![endif]-->
        A link for you! <!-- my favorite example -->
        <!--[if mso]>
            <i style="letter-spacing: 25px; mso-font-width: -100%;">&nbsp;</i>
        <![endif]-->
    </a> Make good use of it.</p>
</div>"""

        cls.mail_template = cls.env['mail.template'].create({
            'name': 'Test template with mso conditionals',
            'subject': 'MSO FTW',
            'body_html': cls.body_html,
            'lang': '{{ object.lang }}',
            'auto_delete': True,
            'model_id': cls.env.ref('base.model_res_partner').id,
        })

    @users('employee')
    def test_mail_mass_mode_template_with_mso(self):
        mail_compose_message = self.env['mail.compose.message'].create({
            'composition_mode': 'mass_mail',
            'model': 'res.partner',
            'template_id': self.mail_template.id,
            'subject': 'MSO FTW',
        })

        values = mail_compose_message.get_mail_values(self.partner_employee.ids)

        self.assertIn(self.body_html,
            values[self.partner_employee.id]['body_html'],
            'We must preserve (mso) comments in email html')

    @users('employee')
    def test_mail_mass_mode_compose_with_mso(self):
        composer = self.env['mail.compose.message'].with_context({
            'default_model': self.test_record._name,
            'default_composition_mode': 'mass_mail',
            'active_ids': [self.test_record.id],
            'active_model': self.test_record._name,
            'active_id': self.test_record.id
        }).create({
            'body': self.body_html,
            'partner_ids': [(4, self.partner_employee.id)],
            'composition_mode': 'mass_mail',
        })
        with self.mock_mail_gateway(mail_unlink_sent=True):
            composer._action_send_mail()

        values = composer.get_mail_values(self.partner_employee.ids)

        self.assertIn(self.body_html,
            values[self.partner_employee.id]['body_html'],
            'We must preserve (mso) comments in email html')
