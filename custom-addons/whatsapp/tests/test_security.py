# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import product

from odoo import exceptions
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.whatsapp.tests.common import WhatsAppCommon, MockIncomingWhatsApp
from odoo.tests import tagged, users
from odoo.tools import mute_logger


class WhatsAppSecurityCase(WhatsAppCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_employee2 = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='user.employee.2@test.mycompany.com',
            groups='base.group_user',
            login='company_1_test_employee_2',
        )

        cls.template_protected_fields = cls.env['whatsapp.template'].create({
            'body': 'Signup link: {{1}}',
            'model_id': cls.env['ir.model']._get_id('res.partner'),
            'name': 'Test Template with Protected Fields',
            'status': 'approved',
            'variable_ids': [
                (0, 0, {
                    'demo_value': 'Customer',
                    'field_name': 'signup_url',
                    'field_type': 'field',
                    'line_type': 'body',
                    'name': '{{1}}',
                }),
            ],
            'wa_account_id': cls.whatsapp_account.id,
        })


@tagged('wa_account', 'security')
class WhatsAppAccountSecurity(WhatsAppSecurityCase):

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_account_access(self):
        """ Test MC-enabled access on whastapp account model """
        # main company access only
        self.assertTrue(self.whatsapp_account.with_user(self.user_admin).name)
        self.assertTrue(self.whatsapp_account.with_user(self.user_employee).name)
        with self.assertRaises(exceptions.AccessError):
            self.assertTrue(self.whatsapp_account.with_user(self.user_employee_c2).name)

        # open to second company
        account_admin = self.whatsapp_account.with_user(self.user_admin)
        account_admin.write({
            'allowed_company_ids': [(4, self.company_2.id)],
        })
        self.assertTrue(self.whatsapp_account.with_user(self.user_employee_c2).name)

    @users('admin')
    def test_account_defaults(self):
        """ Ensure default configuration of account, notably MC / notification
        values. """
        account = self.env['whatsapp.account'].create({
            'account_uid': 'azerty',
            'app_secret': 'azerty',
            'app_uid': 'contact',
            'name': 'Test Account',
            'phone_uid': '987987',
            'token': 'TestToken',
        })
        self.assertEqual(account.allowed_company_ids, self.env.user.company_id)
        self.assertEqual(account.notify_user_ids, self.env.user)


@tagged('wa_account', 'security', 'post_install', '-at_install')
class WhatsAppControllerSecurity(MockIncomingWhatsApp, WhatsAppSecurityCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.whatsapp_account.app_secret = '1234567890abcdef'

    @mute_logger('odoo.addons.whatsapp.controller.main')
    def test_signature_verification(self):
        # valid signature for
        # >>> {"entry": [{"id": "abcdef123456"}]}
        signature = '0a354a1c094d43355c4b478408ba4344564de72fc8ff9699a64ea9095ecb5415'
        response = self._make_webhook_request(
            self.whatsapp_account,
            headers={'X-Hub-Signature-256': f'sha256={signature}'})
        # the endpoint return nothing when everything is fine
        self.assertFalse(response.get('result'))

        # wrong calls
        for signature in [
            False,  # no signature
            'sha256=',  # empty
            signature,  # wrong format
            f'sha256=a{signature[1:]}',  # wrong
        ]:
            with self.subTest(signature=signature):
                headers = {'X-Hub-Signature-256': signature} if signature else None
                response = self._make_webhook_request(self.whatsapp_account, headers=headers)
                self.assertIn("403 Forbidden", response.get('error', {}).get('data', {}).get('message'))


@tagged('wa_message', 'security')
class WhatsAppDiscussSecurity(WhatsAppSecurityCase):

    @users('admin')
    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_member_creation(self):
        channel_channel, channel_wa = self.env['discuss.channel'].create([
            {
                'channel_type': 'channel',
                'name': 'Test',
                'whatsapp_number': '+32456001122',
            }, {
                'channel_type': 'whatsapp',
                'name': 'Test',
                'whatsapp_number': '+32456001122',
            }
        ])
        with self.assertRaises(exceptions.ValidationError):
            channel_channel.with_user(self.user_employee).with_context(
                default_rtc_session_ids=[(0, 0, {'is_screen_sharing_on': True})]
            ).whatsapp_channel_join_and_pin()

        with self.assertRaises(exceptions.AccessError):
            channel_wa.with_user(self.user_employee).with_context(
                default_rtc_session_ids=[(0, 0, {'is_screen_sharing_on': True})]
            ).whatsapp_channel_join_and_pin()

        # Check that admin can join in any whatsapp channel
        employee_channel = self.env['discuss.channel'].with_user(self.user_employee).create({
            'channel_type': 'whatsapp',
            'name': 'employee channel',
            'whatsapp_number': '+32456001122',
        })
        employee_channel.with_user(self.user_admin).with_context(
            default_rtc_session_ids=[(0, 0, {'is_screen_sharing_on': True})]
        ).whatsapp_channel_join_and_pin()


@tagged('wa_message', 'security')
class WhatsAppMessageSecurity(WhatsAppSecurityCase):

    @mute_logger('odoo.addons.auth_signup.models.res_users',
                 'odoo.addons.base.models.ir_cron',
                 'odoo.addons.base.models.ir_model')
    def test_message_signup_token(self):
        """Assert the template values sent to the whatsapp API are not fetched
        as sudo/SUPERUSER, even when going through the cron/queue. """

        # As group_system, create a template to send signup links to new users
        # through whatsapp.It sounds relatively reasonable as valid use case
        # that an admin wants to send user invitation links through a WA message
        env = self.env(user=self.user_admin)
        whatsapp_template_signup = env['whatsapp.template'].create({
            'body': 'Signup link: {{1}}',
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'name': 'Template with Signup Url',
            'status': 'approved',
            'variable_ids': [
                (0, 0, {
                    'demo_value': 'Customer',
                    'field_type': 'field',
                    'field_name': 'signup_url',
                    'line_type': 'body',
                    'name': '{{1}}',
                }),
            ],
            'wa_account_id': self.whatsapp_account.id,
        })

        # Ask for the reset password of the admin
        # This mimics what the `/web/reset_password` URL does, which is publicly available, you just have to know
        # the login of your targeted user ('admin').
        # https://github.com/odoo/odoo/blob/554e6b0898727b6c08a9702e19ea8f2d67632c38/addons/auth_signup/controllers/main.py#L91
        # We could also directly call `/web/reset_password` within this unit test, but this would require:
        # - to convert the test to an httpcase
        # - to get and send the CSRF token.
        # Given the extra overhead, and the fact this is not what we are testing here,
        # just call directly `res.users.reset_password` as sudo, as the `/web/reset_password` route does
        env['res.users'].sudo().reset_password(self.user_admin.login)

        # As whatsapp_admin, take the opportunity of the above whatsapp template
        # to try to use it against the admin, and retrieve his signup token, allowing
        # the whatsapp_admin to change the password of the system admin
        env = self.env(user=self.user_wa_admin)
        # Ensure the whatsapp admin can indeed not read the signup url directly
        with self.assertRaisesRegex(exceptions.AccessError, "You are not allowed to modify 'User'"):
            env.ref('base.user_admin').partner_id.signup_url

        # Now, try to access the signup url of the admin user through a message sent to whatsapp.
        mail_message = self.user_admin.partner_id.message_post(body='foo')
        whatsapp_message = env['whatsapp.message'].create({
            'mail_message_id': mail_message.id,
            'mobile_number': '+32478000000',
            'wa_account_id': whatsapp_template_signup.wa_account_id.id,
            'wa_template_id': whatsapp_template_signup.id,
        })

        # Flush before calling the cron, to write in database pending writes
        # (e.g. `mobile_number_formatted`, which is computed based on `mobile_number`)
        env.flush_all()

        # Use the test_mode/TestCursor
        # To handle the `cr.commit()` in the `send_cron` method:
        # it shouldn't actually commit the transaction, as we are in a test, but simulate it,
        # which is the goal of the test_mode/TestCursor
        self.registry.enter_test_mode(self.cr)
        self.addCleanup(self.registry.leave_test_mode)
        cron_cr = self.registry.cursor()
        self.addCleanup(cron_cr.close)

        # Process the queue to send the whatsapp message through the cron/queue,
        # as the cron queue would do.
        with self.mockWhatsappGateway():
            self.registry['ir.cron']._process_job(
                self.registry.db_name,
                cron_cr,
                self.env.ref('whatsapp.ir_cron_send_whatsapp_queue').read(load=None)[0]
            )

        # Invalidate the cache of the whatsapp message, to force fetching the new values,
        # as the cron wrote on the message using another cursor
        whatsapp_message.invalidate_recordset()
        self.assertEqual(whatsapp_message.failure_reason, "We were not able to fetch value of field 'signup_url'")


@tagged('wa_template', 'security')
class WhatsAppTemplateSecurity(WhatsAppSecurityCase):

    @mute_logger('odoo.addons.base.models.ir_model')
    def test_tpl_create(self):
        """ Creation is for WA admins only """
        template = self.env['whatsapp.template'].with_user(self.user_wa_admin).create({
            'body': 'Hello',
            'name': 'Test',
        })
        self.assertEqual(template.body, 'Hello')

        with self.assertRaises(exceptions.AccessError):
            template = self.env['whatsapp.template'].with_user(self.user_employee).create({
                'body': 'Hello',
                'name': 'Test 2',
            })

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_tpl_read_allowed_users(self):
        """ Test 'allowed_users' that restricts access to the template """
        template = self.env['whatsapp.template'].with_user(self.user_wa_admin).create({
            'body': 'Hello',
            'name': 'Test'})
        self.assertEqual(template.with_user(self.user_employee).name, 'Test')
        self.assertEqual(template.with_user(self.user_employee2).name, 'Test')

        # update, limit allowed users
        template.write({'allowed_user_ids': [(4, self.user_wa_admin.id), (4, self.user_employee.id)]})
        self.assertEqual(template.with_user(self.user_employee).name, 'Test')
        with self.assertRaises(exceptions.AccessError):
            self.assertEqual(template.with_user(self.user_employee2).name, 'Test')

    @mute_logger('odoo.addons.base.models.ir_model')
    def test_tpl_phone_field_update(self):
        """ Check 'phone_field' update is done using the same rules as dynamic
        fields: either limited to allowed fields, either user is a sysadmin. """
        template = self.env['whatsapp.template'].create({
            'body': 'Hello Phone Field Chain',
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'name': 'WhatsApp Template',
            'template_name': 'Phone Field Chain',
            'status': 'approved',
            'wa_account_id': self.whatsapp_account.id,
        })
        test_partner = self.env['res.partner'].create({
            'country_id': self.env.ref('base.be').id,
            'mobile': '0455001122',
            'name': 'Test Partner',
            'phone': '0455334455',
            })

        field_paths_allowed = ['mobile', 'phone', 'phone_sanitized']
        field_paths_allowed_ko = ['x_studio_phone']  # allowed but does not exist
        field_paths_disallowed = ['name']  # not allowed
        field_paths_disallowed_ko = ['my_custom_phone_field']  # not allowed and does not exist
        for field_paths, invalid, admin_only in [
            (field_paths_allowed, False, False),
            (field_paths_allowed_ko, True, False),
            (field_paths_disallowed, False, True),
            (field_paths_disallowed_ko, True, True),
        ]:
            for field_path, test_user in product(field_paths, (self.user_employee, self.user_wa_admin, self.user_admin)):
                with self.subTest(field_path=field_path, test_user_name=test_user.name):
                    template.sudo().write({'phone_field': 'mobile'})
                    template = template.with_user(test_user)
                    # employee can never updates templates; wa_admin allowed fields only
                    if test_user == self.user_employee or (admin_only and test_user == self.user_wa_admin):
                        with self.assertRaises(exceptions.AccessError):
                            template.write({'phone_field': field_path})
                        continue
                    if invalid:
                        with self.assertRaises(exceptions.ValidationError):
                            template.write({'phone_field': field_path})
                        continue
                    template.write({'phone_field': field_path})
                    test_partner = test_partner.with_user(test_user)
                    composer = self._instanciate_wa_composer_from_records(template, test_partner, with_user=test_user)
                    with self.mockWhatsappGateway():
                        # name does not hold a valid number, in single mode it should crash
                        if field_path == 'name':
                            with self.assertRaises(exceptions.UserError):
                                composer.action_send_whatsapp_template()
                        else:
                            composer.action_send_whatsapp_template()

    def test_tpl_safe_field_access(self):
        """ Check field access security """
        template = self.env['whatsapp.template'].create({
            'body': "hello, I am from '{{1}}'.",
            'model_id': self.env['ir.model']._get_id('res.users'),
            'name': 'Test Template',
            'status': 'approved',
        })

        # Verify that a System User can use any field in template.
        template.with_user(self.user_admin).variable_ids = [
            (5, 0, 0),
            (0, 0, {
                'demo_value': "pwned",
                'field_name': 'password',
                'field_type': "field",
                'line_type': "body",
                'name': "{{1}}",
            }),
        ]

        # Verify that a WhatsApp Admin can't set unsafe fields in template variable
        with self.assertRaises(exceptions.ValidationError):
            template.with_user(self.user_wa_admin).variable_ids = [
                (5, 0, 0),
                (0, 0, {
                    'demo_value': "pwned",
                    'field_name': 'password',
                    'field_type': "field",
                    'line_type': "body",
                    'name': "{{1}}",
                }),
            ]

        with self.assertRaises(exceptions.ValidationError):
            template.with_user(self.user_wa_admin).model_id = self.env['ir.model']._get_id('res.partner')

        # try to change the model of the variable with x2many command
        with self.assertRaises(exceptions.ValidationError):
            self.env['whatsapp.template'].with_user(self.user_wa_admin).create({
                'body': "hello, I am from '{{1}}'.",
                'model_id': self.env['ir.model']._get_id('res.partner'),
                'name': 'Test Template',
                'status': 'approved',
                'variable_ids': [(4, template.variable_ids.id)],
            })

    @users('user_wa_admin')
    def test_tpl_update_wa_admin(self):
        """ Check WA admins update involving field access. """
        template = self.template_protected_fields.with_env(self.env)

        # changing fields other than variables should not trigger security check
        template.write({'name': 'Can Update'})
        self.assertEqual(template.name, 'Can Update')
