# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo import exceptions
from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.whatsapp.tests.common import WhatsAppCommon
from odoo.fields import Datetime
from odoo.tests import tagged, users


class WhatsAppComposerCase(WhatsAppCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # WRITE access on partner is required to be able to post a message on it
        cls.user_employee.write({'groups_id': [(4, cls.env.ref('base.group_partner_manager').id)]})

        # test records for sending messages
        cls.customers = cls.env['res.partner'].create([
            {
                'country_id': cls.env.ref('base.in').id,
                'name': 'Customer-IN',
                'mobile': "+91 12345 67891",
            }, {
                'country_id': cls.env.ref('base.be').id,
                'name': 'Customer-BE',
                'mobile': "0456001122",
            }
        ])

        # templates (considered as approved)
        cls.template_basic, cls.template_dynamic_cplx = cls.env['whatsapp.template'].create([
            {
                'body': 'Hello World',
                'name': 'Test-basic',
                'status': 'approved',
                'wa_account_id': cls.whatsapp_account.id,
            }, {
                'body': '''Hello I am {{1}},
Here my mobile number: {{2}},
You are coming from {{3}}.
Welcome to {{4}} office''',
                'name': 'Test-dynamic-complex',
                'status': 'approved',
                'variable_ids': [
                    (5, 0, 0),
                    (0, 0, {'name': "{{1}}", 'line_type': "body", 'field_type': "user_name", 'demo_value': "Jigar"}),
                    (0, 0, {'name': "{{2}}", 'line_type': "body", 'field_type': "user_mobile", 'demo_value': "+91 12345 12345"}),
                    (0, 0, {'name': "{{3}}", 'line_type': "body", 'field_type': "field", 'demo_value': "sample country", 'field_name': 'country_id.name'}),
                    (0, 0, {'name': "{{4}}", 'line_type': "body", 'field_type': "free_text", 'demo_value': "Odoo In"}),
                ],
                'wa_account_id': cls.whatsapp_account.id,
            }
        ])


@tagged('wa_composer')
class WhatsAppComposerInternals(WhatsAppComposerCase, CronMixinCase):

    def test_assert_initial_data(self):
        """ Ensure base data for tests, to ease understanding them """
        self.assertEqual(self.company_admin.country_id, self.env.ref('base.us'))
        self.assertEqual(self.user_admin.country_id, self.env.ref('base.be'))

    @users('employee')
    def test_composer_check_user_number(self):
        """ When using 'user_mobile' in template variables, number should be
        set on sender. """
        template = self.template_dynamic_cplx.with_user(self.env.user)

        for mobile, should_crash in [
            (False, True),
            ('', True),
            ('zboing', False)
        ]:
            with self.subTest(mobile=mobile):
                self.env.user.mobile = mobile

                composer_form = self._wa_composer_form(template, self.customers[0])
                composer = composer_form.save()
                if should_crash:
                    with self.assertRaises(exceptions.ValidationError), self.mockWhatsappGateway():
                        composer.action_send_whatsapp_template()
                else:
                    with self.mockWhatsappGateway():
                        composer.action_send_whatsapp_template()

    @users('employee')
    def test_composer_number_on_template_change(self):
        """ Test composer behavior when templates changes, also test contextual
        value that forces the value on top of template phone field path. """
        template_1 = self.template_basic
        template_1.write({'phone_field': 'phone'})
        template_2 = self.env['whatsapp.template'].sudo().create({
            'body': 'Hello world',
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'name': 'Template 1',
            'phone_field' : 'mobile',
            'wa_account_id': self.whatsapp_account.id,
        })

        # verify phone doesn't change with default phone context key in single mode
        composer_1 = self._wa_composer_form(
            template_1, from_records=self.customers[0],
            with_user=self.env.user, add_context={'default_phone': '+32455998877'},
        )
        self.assertEqual(composer_1.phone, '+32455998877', "Default context value should be used")
        composer_1.wa_template_id = template_2
        self.assertEqual(composer_1.phone, '+32455998877', "Default context value should be kept")
        composer_1.wa_template_id = self.env['whatsapp.template']
        self.assertEqual(composer_1.phone, '+32455998877', "Default context value should be kept")

        # Verify phone change according to template with no default phone
        composer_2 = self._wa_composer_form(
            template_1, from_records=self.customers[0],
            with_user=self.env.user,
        )
        self.assertTrue(not(composer_2.phone) and not(self.customers[0].phone),  # '' != False
                         "Phone should be taken from record, phone_field of template 1")
        composer_2.wa_template_id = template_2
        self.assertEqual(composer_2.phone, self.customers[0].mobile,
                         "Phone should be taken from record, phone_field of template 2")
        composer_2.wa_template_id = self.env['whatsapp.template']
        self.assertEqual(composer_2.phone, self.customers[0].mobile,
                         "Phone should not be reset when there is one")

    @users('employee')
    def test_composer_number_validation(self):
        """ Test number computation and validation in single / batch mode. Also
        test direct send by cron / delegate behavior. """
        template = self.template_basic.with_env(self.env)
        date_reference = Datetime.from_string('2023-11-22 09:00:00')
        invalid_customer = self.env['res.partner'].sudo().create({
            'country_id': self.env.ref('base.in').id,
            'mobile': "12321",
            'name': 'Customer-IN',
        })
        default_phone_number = "+32455112233"
        all_test_records = invalid_customer + self.customers

        for test_records, use_default, force_cron, exp_phone, exp_invalid_count, exp_crash, exp_batch, exp_cron_trigger in [
            (
                all_test_records[0], False, False,
                '12321', 1, True, False, False,  # single record without cron
            ), (
                all_test_records[0], False, True,
                '12321', 1, False, False, True,  # single record with cron
            ), (
                all_test_records[0], True, False,
                '+32455112233', 0, False, False, False,  # no need to force cron in single mode / won't crash as default context value
            ), (
                all_test_records, False, False,
                '12321, 911234567891, 0456001122', 1, False, True, True,  # batch mode always force cron
            ), (
                all_test_records, True, False,
                '+32455112233', 1, False, True, True,  # batch mode always force cron
            ), (
                all_test_records, False, True,
                '12321, 911234567891, 0456001122', 1, False, True, True
            ),
        ]:
            with self.subTest(test_records=test_records, use_default=use_default, force_cron=force_cron):
                test_records = test_records.with_env(self.env)
                add_context = {'default_phone': default_phone_number} if use_default else {}
                composer_form = self._wa_composer_form(
                    template, from_records=test_records,
                    add_context=add_context,
                )
                self.assertEqual(composer_form.batch_mode, exp_batch)
                self.assertEqual(composer_form.invalid_phone_number_count, exp_invalid_count)
                self.assertEqual(composer_form.phone, exp_phone)
                composer = composer_form.save()
                self.assertEqual(composer.phone, exp_phone)

                # Test that the WhatsApp composer fails validation when there is invalid number.
                with freeze_time(date_reference), \
                     self.capture_triggers('whatsapp.ir_cron_send_whatsapp_queue') as captured_triggers, \
                     self.mockWhatsappGateway():
                    if exp_crash:
                        with self.assertRaises(exceptions.UserError):
                            composer._send_whatsapp_template(force_send_by_cron=force_cron)
                    else:
                        composer._send_whatsapp_template(force_send_by_cron=force_cron)

                # in batch mode: three messages ready to be sent if sent with force_cron parameter, else two messages
                if exp_batch:
                    self.assertEqual(len(self._new_wa_msg), 3 if force_cron else 2)
                    for exp_contacted in self.customers:
                        self.assertWAMessageFromRecord(
                            exp_contacted,
                            status="outgoing",
                        )
                if exp_cron_trigger:
                    self.assertEqual(len(captured_triggers.records), 1)
                    self.assertEqual(
                        captured_triggers.records[0].cron_id,
                        self.env.ref('whatsapp.ir_cron_send_whatsapp_queue'))
                    self.assertEqual(captured_triggers.records[0].call_at, date_reference)
                else:
                    self.assertFalse(captured_triggers.records)

    @users('employee')
    def test_composer_tpl_button(self):
        """ Test adding buttons on templates """
        for button_values in [
            {'button_type': 'quick_reply'},
            {'button_type': 'phone_number', 'call_number': '+91 (835) 902-5723'},
            {'button_type': 'url', 'website_url': 'https://www.odoo.com'},
        ]:
            with self.subTest(button_values=button_values):
                self.template_basic.write({'button_ids': [(5, 0)]})
                self._add_button_to_template(self.template_basic, f"Test {button_values['button_type']}", **button_values)

                template = self.template_basic.with_env(self.env)
                composer = self._instanciate_wa_composer_from_records(template, from_records=self.customers[0])
                with self.mockWhatsappGateway():
                    composer.action_send_whatsapp_template()

                self.assertWAMessage()

    def test_composer_variable_evaluation(self):
        """ Test various field paths to check corner cases of evaluation """
        variable = self.template_dynamic_cplx.variable_ids.filtered(lambda v: v.field_name == 'country_id.name')
        template = self.env['whatsapp.template'].create({
            'body': "Please evaluate {{1}}.",
            'name': 'Test-various-field-path',
            'status': 'approved',
            'variable_ids': [
                (5, 0, 0),
                (0, 0, {'name': "{{1}}", 'line_type': "body", 'field_type': "field", 'demo_value': "sample country", 'field_name': 'country_id.name'}),
            ],
            'wa_account_id': self.whatsapp_account.id,
        })

        test_tags = self.env['res.partner.category'].create([
            {'color': idx, 'name': f'Tag{idx}'} for idx in range(3)
        ])
        test_partner = self.env['res.partner'].create({
            'category_id': test_tags.ids,
            'color': False,
            'country_id': self.env.ref('base.be').id,
            'mobile': '+32455001122',
            'name': 'Test Partner',
            'title': False,
        })

        for (field_path, expected_value) in zip(
            [
                # many2one with value
                'country_id', 'country_id.name',
                # many2one without value
                'title', 'title.name',
                # many2many
                'category_id', 'category_id.color', 'category_id.partner_ids',
                # integer without value
                'color',
            ], [
                'Belgium', 'Belgium',
                '', '',
                'Tag0 Tag1 Tag2', '0 1 2', 'Test Partner',
                '0',
            ]
        ):
            with self.subTest(field_path=field_path):
                template.variable_ids.write({
                    'field_name': field_path
                })

                composer = self._instanciate_wa_composer_from_records(template, from_records=test_partner, with_user=self.user_employee)
                with self.mockWhatsappGateway():
                    composer.action_send_whatsapp_template()
                self.assertWAMessage(
                    mail_message_values={
                        'body': f'<p>Please evaluate {expected_value}.</p>',
                    }
                )

        # should crash
        for field_path in [
            # does not exist on distant model
            'country_id.wrong',
            # does not exist
            'wrong',
            # void is not supported
            '', False, None,
        ]:
            with self.subTest(field_path=field_path):
                with self.assertRaises(exceptions.ValidationError):
                    variable.write({
                        'field_name': field_path
                    })


@tagged('wa_composer')
class WhatsAppComposerPreview(WhatsAppComposerCase):

    @users('user_wa_admin')
    def test_composer_preview(self):
        """ Test preview feature from composer """
        body_var = 'Nishant'
        header_var = 'Jigar'
        template = self.env['whatsapp.template'].create({
            'body': 'Feel *free* to *contact* {{1}}; he is ~great~ ~super~ super great !',
            'footer_text': 'Thank *you*',
            'header_text': 'Header ```Code Content``` {{1}}',
            'header_type': 'text',
            'variable_ids': [
                (5, 0, 0),
                (0, 0, {
                'name': "{{1}}",
                'line_type': 'body',
                'field_type': "free_text",
                'demo_value': body_var,
                }),
                (0, 0, {
                'name': "{{1}}",
                'line_type': 'header',
                'field_type': "free_text",
                'demo_value': header_var,
                }),
            ],
            'wa_account_id': self.whatsapp_account.id,
        })
        composer = self._instanciate_wa_composer_from_records(template, from_records=self.customers[0])

        for expected_str in [
            f'Header <code>Code Content</code> {header_var}',
            f'Feel <b>free</b> to <b>contact</b> {body_var}; he is <s>great</s> <s>super</s> super great !',
            'Thank *you*',
        ]:
            self.assertIn(expected_str, composer.preview_whatsapp)


@tagged('wa_composer')
class WhatsAppComposerUsage(WhatsAppComposerCase):

    def test_composer_template_send_user_access(self):
        """ Test that WA message send through SUDO-ed flow, involving public
        user """
        self._setup_share_users()

        for test_user in self.test_public_user + self.test_portal_user + self.user_employee:
            with self.subTest(test_user_login=test_user.login):
                composer = self.env['whatsapp.composer'].with_context(
                    active_model=self.customers[0]._name, active_ids=self.customers[0].ids,
                ).with_user(test_user).sudo().create({
                    'wa_template_id': self.template_dynamic_cplx.id,
                })

                with self.mockWhatsappGateway():
                    composer.sudo().action_send_whatsapp_template()
                    self.assertWAMessage(
                        "sent",
                        fields_values={
                            "create_uid": test_user,
                            "body": f"<p>Hello I am { test_user.name },<br>Here my mobile number: { test_user.mobile },"
                                    f"<br>You are coming from { self.customers[0].country_id.name }.<br>Welcome to Odoo In office</p>",
                        },
                    )
