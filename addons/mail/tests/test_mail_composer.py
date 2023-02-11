# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError
from odoo.tests import Form, tagged, users
from odoo.tools import mute_logger


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
            'auto_delete': True,
            'body_html': cls.body_html,
            'lang': '{{ object.lang }}',
            'model_id': cls.env['ir.model']._get_id('res.partner'),
            'subject': 'MSO FTW',
            'name': 'Test template with mso conditionals',
        })


@tagged('mail_composer')
class TestMailComposerForm(TestMailComposer):
    """ Test mail composer form view usage. """

    @classmethod
    def setUpClass(cls):
        super(TestMailComposerForm, cls).setUpClass()

        cls.user_employee.write({'groups_id': [
            (4, cls.env.ref('base.group_private_addresses').id),
            (4, cls.env.ref('base.group_partner_manager').id),
        ]})
        cls.partner_private, cls.partner_private_2, cls.partner_classic = cls.env['res.partner'].create([
            {
                'email': 'private.customer@text.example.com',
                'phone': '0032455112233',
                'name': 'Private Customer',
                'type': 'private',
            },
            {
                'email': 'private.customer.2@test.example.com',
                'phone': '0032455445566',
                'name': 'Private Customer 2',
                'type': 'private',
            },
            {
                'email': 'not.private@test.example.com',
                'phone': '0032455778899',
                'name': 'Classic Customer',
                'type': 'contact',
            }
        ])

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('employee')
    def test_composer_default_recipients(self):
        """ Test usage of a private partner in composer, as default value """
        partner_classic = self.partner_classic.with_env(self.env)
        test_record = self.test_record.with_env(self.env)

        form = Form(self.env['mail.compose.message'].with_context({
            'default_partner_ids': partner_classic.ids,
            'default_model': test_record._name,
            'default_res_id': test_record.id,
        }))
        form.body = '<p>Hello</p>'
        self.assertEqual(
            form.partner_ids._get_ids(), partner_classic.ids,
            'Default populates the field'
        )
        saved_form = form.save()
        self.assertEqual(
            saved_form.partner_ids, partner_classic,
            'Default value is kept at save'
        )

        with self.mock_mail_gateway():
            saved_form._action_send_mail()

        message = self.test_record.message_ids[0]
        self.assertEqual(message.body, '<p>Hello</p>')
        self.assertEqual(message.partner_ids, partner_classic)
        self.assertEqual(message.subject, f'Re: {test_record.name}')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('employee')
    def test_composer_default_recipients_private(self):
        """ Test usage of a private partner in composer, as default value """
        partner_private = self.partner_private.with_env(self.env)
        partner_classic = self.partner_classic.with_env(self.env)
        test_record = self.test_record.with_env(self.env)

        form = Form(self.env['mail.compose.message'].with_context({
            'default_partner_ids': (partner_private + partner_classic).ids,
            'default_model': test_record._name,
            'default_res_id': test_record.id,
        }))
        form.body = '<p>Hello</p>'
        self.assertEqual(
            sorted(form.partner_ids._get_ids()),
            sorted((partner_private + partner_classic).ids),
            'Default populates the field'
        )
        saved_form = form.save()
        self.assertEqual(
            saved_form.partner_ids, partner_private + partner_classic,
            'Default value is kept at save'
        )

        with self.mock_mail_gateway():
            saved_form._action_send_mail()

        message = self.test_record.message_ids[0]
        self.assertEqual(message.body, '<p>Hello</p>')
        self.assertEqual(message.partner_ids, partner_private + partner_classic)
        self.assertEqual(message.subject, f'Re: {test_record.name}')

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.mail.models.mail_mail')
    @users('employee')
    def test_composer_default_recipients_private_norights(self):
        """ Test usage of a private partner in composer when not having the
        rights to see them, as default value """
        self.user_employee.write({'groups_id': [
            (3, self.env.ref('base.group_private_addresses').id),
        ]})
        with self.assertRaises(AccessError):
            _name = self.partner_private.with_env(self.env).name

        partner_classic = self.partner_classic.with_env(self.env)
        test_record = self.test_record.with_env(self.env)

        with self.assertRaises(AccessError):
            _form = Form(self.env['mail.compose.message'].with_context({
                'default_partner_ids': (self.partner_private + partner_classic).ids,
                'default_model': test_record._name,
                'default_res_id': test_record.id,
            }))

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('employee')
    def test_composer_template_recipients_private(self):
        """ Test usage of a private partner in composer, comint from template
        value """
        email_to_new = 'new.customer@test.example.com'
        self.mail_template.write({
            'email_to': f'{self.partner_private_2.email_formatted}, {email_to_new}',
            'partner_to': f'{self.partner_private.id},{self.partner_classic.id}',
        })
        template = self.mail_template.with_env(self.env)
        partner_private = self.partner_private.with_env(self.env)
        partner_private_2 = self.partner_private_2.with_env(self.env)
        partner_classic = self.partner_classic.with_env(self.env)
        test_record = self.test_record.with_env(self.env)

        form = Form(self.env['mail.compose.message'].with_context({
            'default_model': test_record._name,
            'default_res_id': test_record.id,
            'default_template_id': template.id,
        }))

        # transformation from email_to into partner_ids: find or create
        existing_partner = self.env['res.partner'].search(
            [('email_normalized', '=', self.partner_private_2.email_normalized)]
        )
        self.assertEqual(existing_partner, partner_private_2, 'Should find existing private contact')
        new_partner = self.env['res.partner'].search(
            [('email_normalized', '=', email_to_new)]
        )
        self.assertEqual(new_partner.type, 'contact', 'Should create a new contact')

        self.assertEqual(
            sorted(form.partner_ids._get_ids()),
            sorted((partner_private + partner_classic + partner_private_2 + new_partner).ids),
            'Template populates the field with both email_to and partner_to'
        )
        saved_form = form.save()
        self.assertEqual(
            # saved_form.partner_ids, partner_private + partner_classic + partner_private_2 + new_partner,
            saved_form.partner_ids, partner_classic + new_partner,
            'Template value is kept at save (FIXME: loosing private partner)'
        )

        with self.mock_mail_gateway():
            saved_form._action_send_mail()

        message = self.test_record.message_ids[0]
        self.assertIn('<h1>Hello sir!</h1>', message.body)
        # self.assertEqual(message.partner_ids, partner_private + partner_classic + partner_private_2 + new_partner)
        self.assertEqual(
            message.partner_ids, partner_classic + new_partner,
            'FIXME: loosing private partner'
        )
        self.assertEqual(message.subject, 'MSO FTW')


@tagged('mail_composer')
class TestMailComposerRendering(TestMailComposer):
    """ Test rendering and support of various html tweaks in composer """

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

    @mute_logger('odoo.addons.mail.models.mail_mail')
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
