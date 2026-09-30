from odoo.addons.sms.tests.common import SMSCommon
from odoo.addons.test_mail_sms.tests.common import TestSMSRecipients
from odoo.tests import Form, tagged


@tagged('sms_composer')
class TestSMSNoThread(SMSCommon, TestSMSRecipients):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._test_body_dyn = 'Hello {{ object.name }} zizisse an SMS.'
        cls._test_body_sta = 'Hello Zboing'
        cls.test_nothreads = cls.env['sms.test.nothread'].create([
            {
                'name': 'Test',
                'customer_id': cls.partner_1.id,
            }, {
                'name': 'Test',
                'customer_id': cls.partner_2.id,
            }, {
                'name': 'Test (no partner)',
                'customer_id': False,
            },
        ])
        cls.sms_template = cls._create_sms_template(
            cls.test_nothreads._name,
            body=cls._test_body_dyn,
        )

    def test_composer_comment(self):
        with self.with_user('employee'):
            test_record = self.test_nothreads[0].with_env(self.env)
            composer_form = Form(self.env['sms.composer'].with_context(
                default_res_id=test_record.id,
                default_res_model=test_record._name,
            ))
            composer_form.body = self._test_body_sta
            composer = composer_form.save()
            self.assertTrue(composer.comment_single_recipient)
            self.assertEqual(composer.composition_mode, 'comment')
            self.assertEqual(composer.recipient_valid_count, 0)
            self.assertEqual(composer.recipient_invalid_count, 1)
            self.assertEqual(composer.recipient_single_description, self.partner_1.name)
            self.assertEqual(composer.recipient_single_number, '+32456001122')
            self.assertEqual(composer.recipient_single_number_itf, '+32456001122')
            self.assertTrue(composer.recipient_single_valid)
            self.assertEqual(composer.number_field_name, 'phone')
            self.assertFalse(composer.numbers)
            self.assertFalse(composer.sanitized_numbers)

            with self.mockSMSGateway():
                composer._action_send_sms()

    def test_composer_comment_res_ids(self):
        with self.with_user('employee'):
            test_record = self.test_nothreads[0].with_env(self.env)
            composer_form = Form(self.env['sms.composer'].with_context(
                default_res_ids=test_record.ids,
                default_res_model=test_record._name,
            ))
            composer_form.body = self._test_body_sta
            composer = composer_form.save()
            # TDE FIXME: mono/mass mode should be fixed
            self.assertFalse(composer.comment_single_recipient)
            self.assertEqual(composer.composition_mode, 'comment')
            self.assertEqual(composer.recipient_valid_count, 1)
            self.assertEqual(composer.recipient_invalid_count, 0)
            self.assertFalse(composer.recipient_single_description)
            self.assertFalse(composer.recipient_single_number)
            self.assertFalse(composer.recipient_single_number_itf)
            self.assertFalse(composer.recipient_single_valid)
            self.assertFalse(composer.number_field_name)
            self.assertFalse(composer.numbers)
            self.assertFalse(composer.sanitized_numbers)

            with self.mockSMSGateway():
                composer._action_send_sms()

    def test_composer_comment_res_users(self):
        for ctx, expected in [
            ({}, {}),
            ({'default_number_field_name': 'mobile'}, {}),
        ]:
            with self.subTest(ctx=ctx):
                with self.with_user('employee'):
                    ctx['default_res_id'] = self.user_admin.id
                    ctx['default_res_model'] = self.user_admin._name
                    composer_form = Form(self.env['sms.composer'].with_context(**ctx))
                    composer_form.body = self._test_body_sta
                    composer = composer_form.save()
                    self.assertTrue(composer.comment_single_recipient)
                    self.assertEqual(composer.composition_mode, 'comment')
                    if ctx.get('default_number_field_name') == 'mobile':
                        stored_number = ''  # invalid field + single recipient -> no number
                        self.assertEqual(composer.recipient_valid_count, 0)
                        self.assertEqual(composer.recipient_invalid_count, 1)
                    else:
                        stored_number = '+32455135790'
                        self.assertEqual(composer.recipient_valid_count, 1)
                        self.assertEqual(composer.recipient_invalid_count, 0)
                    self.assertEqual(composer.recipient_single_description, self.user_admin.name)
                    self.assertEqual(composer.recipient_single_number, '+32455135790')
                    self.assertEqual(composer.recipient_single_number_itf, stored_number)
                    self.assertTrue(composer.recipient_single_valid)
                    self.assertEqual(composer.number_field_name, ctx.get('default_number_field_name', 'phone'))
                    self.assertFalse(composer.numbers)
                    self.assertFalse(composer.sanitized_numbers)

                    with self.mockSMSGateway():
                        composer._action_send_sms()

                    # even if the stored number is correct, fall back on the computed number
                    self.assertSMS(self.env['res.partner'], '+32455135790', 'pending')
