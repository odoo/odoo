from odoo.addons.mail.tests.common import mail_new_test_user, MailCommon
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged, users
from odoo.tools import mute_logger


@tagged('mail_wizards')
class TestMailResend(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailResend, cls).setUpClass()
        cls.test_record = cls.env['mail.test.simple'].with_context(cls._test_context).create({'name': 'Test', 'email_from': 'ignasse@example.com'})

        cls.user1 = mail_new_test_user(cls.env, login='e1', groups='base.group_user', name='Employee 1', notification_type='email', email='e1')  # invalid email
        cls.user2 = mail_new_test_user(cls.env, login='e2', groups='base.group_portal', name='Employee 2', notification_type='email', email='e2@example.com')
        cls.partner1 = cls.env['res.partner'].with_context(cls._test_context).create({
            'name': 'Partner 1',
            'email': 'p1'  # invalid email
        })
        cls.partner2 = cls.env['res.partner'].with_context(cls._test_context).create({
            'name': 'Partner 2',
            'email': 'p2@example.com'
        })
        cls.partners = cls.env['res.partner'].concat(cls.user1.partner_id, cls.user2.partner_id, cls.partner1, cls.partner2)
        cls.invalid_email_partners = cls.env['res.partner'].concat(cls.user1.partner_id, cls.partner1)

    def test_mail_resend_workflow(self):
        self._reset_bus()
        with self.assertSinglePostNotifications(
                [{'partner': partner, 'type': 'email', 'status': 'exception'} for partner in self.partners],
                message_info={'message_type': 'notification'}):
            def _connect(*args, **kwargs):
                raise Exception("Some exception")
            self.connect_mocked.side_effect = _connect
            message = self.test_record.with_user(self.user_admin).message_post(partner_ids=self.partners.ids, subtype_xmlid='mail.mt_comment', message_type='notification')

        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})
        self.assertEqual(wizard.notification_ids.mapped('res_partner_id'), self.partners, "wizard should manage notifications for each failed partner")

        # three more failure sent on bus, one for each mail in failure and one for resend
        self._reset_bus()
        expected_bus_notifications = [
            (self.cr.dbname, 'res.partner', self.env.user.partner_id.id),
            (self.cr.dbname, 'res.partner', self.partner_admin.id),
        ]
        with self.mock_mail_gateway(), self.assertBus(expected_bus_notifications * 3):
            wizard.resend_mail_action()
        done_msgs, done_notifs = self.assertMailNotifications(message, [
            {'content': '', 'message_type': 'notification',
             'notif': [{'partner': partner, 'type': 'email', 'status': 'exception' if partner in self.user1.partner_id | self.partner1 else 'sent'} for partner in self.partners]}],
            bus_notif_count=3,
        )
        self.assertEqual(wizard.notification_ids, done_notifs)
        self.assertEqual(done_msgs, message)

        self.user1.write({"email": 'u1@example.com'})

        # two more failure update sent on bus, one for failed mail and one for resend
        self._reset_bus()
        with self.mock_mail_gateway(), self.assertBus(expected_bus_notifications * 2):
            self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({}).resend_mail_action()
        done_msgs, done_notifs = self.assertMailNotifications(message, [
            {'content': '', 'message_type': 'notification',
             'notif': [{'partner': partner, 'type': 'email', 'status': 'exception' if partner == self.partner1 else 'sent', 'check_send': partner == self.partner1} for partner in self.partners]}],
            bus_notif_count=2,
        )
        self.assertEqual(wizard.notification_ids, done_notifs)
        self.assertEqual(done_msgs, message)

        self.partner1.write({"email": 'p1@example.com'})

        # A success update should be sent on bus once the email has no more failure
        self._reset_bus()
        with self.mock_mail_gateway(), self.assertBus(expected_bus_notifications):
            self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({}).resend_mail_action()
        self.assertMailNotifications(message, [
            {'content': '', 'message_type': 'notification',
             'notif': [{'partner': partner, 'type': 'email', 'status': 'sent', 'check_send': partner == self.partner1} for partner in self.partners]}]
        )

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_remove_mail_become_canceled(self):
        # two failure sent on bus, one for each mail
        self._reset_bus()
        with self.mock_mail_gateway(), self.assertBus([(self.cr.dbname, 'res.partner', self.partner_admin.id)] * 2):
            message = self.test_record.with_user(self.user_admin).message_post(partner_ids=self.partners.ids, subtype_xmlid='mail.mt_comment', message_type='notification')

        self.assertMailNotifications(message, [
            {'content': '', 'message_type': 'notification',
             'notif': [{'partner': partner, 'type': 'email', 'status': 'exception' if partner in self.user1.partner_id | self.partner1 else 'sent'} for partner in self.partners]}],
            bus_notif_count=2,
        )

        self._reset_bus()
        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})
        partners = wizard.recipient_ids.mapped("partner_id")
        self.assertEqual(self.invalid_email_partners, partners)
        wizard.recipient_ids.filtered(lambda p: p.partner_id == self.partner1).write({"resend": False})
        wizard.resend_mail_action()

        self.assertMailNotifications(message, [
            {'content': '', 'message_type': 'notification',
             'notif': [{'partner': partner, 'type': 'email',
                        'status': (partner == self.user1.partner_id and 'exception') or (partner == self.partner1 and 'canceled') or 'sent'} for partner in self.partners]}],
            bus_notif_count=2,
        )

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_cancel_all(self):
        self._reset_bus()
        with self.mock_mail_gateway(), self.assertBus([(self.cr.dbname, 'res.partner', self.partner_admin.id)] * 2):
            message = self.test_record.with_user(self.user_admin).message_post(partner_ids=self.partners.ids, subtype_xmlid='mail.mt_comment', message_type='notification')

        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})
        # one update for cancell
        self._reset_bus()
        expected_bus_notifications = [
            (self.cr.dbname, 'res.partner', self.env.user.partner_id.id),
            (self.cr.dbname, 'res.partner', self.partner_admin.id),
        ]
        with self.mock_mail_gateway(), self.assertBus(expected_bus_notifications):
            wizard.cancel_mail_action()

        self.assertMailNotifications(message, [
            {'content': '', 'message_type': 'notification',
             'notif': [{'partner': partner, 'type': 'email',
                        'check_send': partner in self.user1.partner_id | self.partner1,
                        'status': 'canceled' if partner in self.user1.partner_id | self.partner1 else 'sent'} for partner in self.partners]}]
        )

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('e1')
    def test_update_recipient(self):
        """Check that users are not allowed to forcefully modify partners through the wizard."""
        def _connect(*args, **kwargs):
            raise Exception("Some exception")
        with self.mock_mail_gateway():
            self.connect_mocked.side_effect = _connect
            message = self.test_record.with_user(self.env.user).message_post(partner_ids=self.partners.ids, subtype_xmlid='mail.mt_comment', message_type='notification')

        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})

        with self.assertRaises(AccessError):
            wizard.recipient_ids[0].name = 'abc'

        with self.assertRaises(AccessError):
            wizard.recipient_ids[0].email = 'abc@test.lan'

@tagged('mail_wizards')
class TestMailResendNoPartner(MailCommon):
    @classmethod
    def setUpClass(cls):
        super(TestMailResendNoPartner, cls).setUpClass()
        cls.valid_email = 'valid@test.lan'
        cls.valid_email2 = 'valid2@test.lan'
        cls.invalid_email1 = 'bob'
        cls.empty_email1 = ''
        cls.valid_emails = {cls.valid_email, cls.valid_email2}
        test_records = cls.env['mail.test.ticket'].with_context(cls._test_context).create([
            {
                'email_from': ','.join(emails),
                'name': f'Test {name} Email',
            }
            for name, emails in [
                ('valid', cls.valid_emails), ('invalid', [cls.invalid_email1]), ('empty', [cls.empty_email1])
            ]
        ])
        # composer without partners required to generate unpartnered_email notifications
        Composer = cls.env['mail.compose.message'].with_user(cls.user_admin)
        cls.valid_composer, cls.invalid_composer, cls.empty_composer = Composer.create([{
            'author_id': cls.partner_admin.id,
            'body': '<p>Test Body</p>',
            'composition_mode': 'mass_mail',
            'email_from': cls.user_admin.email_formatted,
            'message_type': 'notification',
            'model': test_record._name,
            'res_ids': test_record.ids,
            'subject': 'My amazing subject',
        } for test_record in test_records])

    def setUp(self):
        super().setUp()
        # clear admin creation notification as it messes with assertBusNotifications
        self.env['bus.bus'].search([('channel', 'like', f'%res.partner",{self.user_admin.partner_id.id}%')]).unlink()

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('admin')
    def test_mail_resend_workflow_email(self):
        with self.assertSinglePostNotifications(
                [{'email_to': [email], 'type': 'email', 'status': 'exception'} for email in self.valid_emails],
                message_info={'content': 'Test Body', 'message_type': 'email_outgoing', 'subtype': None},):
            def _connect(*args, **kwargs):
                raise Exception("Some exception")
            self.connect_mocked.side_effect = _connect

            mails_sudo, _ = self.valid_composer.with_user(self.env.user)._action_send_mail()

        message = mails_sudo.mail_message_id
        self.assertEqual(len(message), 1)
        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})
        self.assertEqual(set(wizard.notification_ids.mapped('email')), self.valid_emails, "wizard should manage notifications for each failed partner")

        # check notified of resend
        self._reset_bus()
        expected_bus_notifications = [
            (self.cr.dbname, 'res.partner', self.partner_admin.id),
        ]
        # resend without server error and update email
        with self.mock_mail_gateway(), self.assertBus(expected_bus_notifications):
            new_valid_email = 'valid3@example.lan'
            wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})
            wizard.recipient_ids.filtered(lambda r: r.email == self.valid_email2).write({"email": new_valid_email})
            wizard.resend_mail_action()

        done_msgs, done_notifs = self.assertMailNotifications(message, [{
            'content': 'Test Body', 'message_type': 'email_outgoing', 'subtype': None,
            'notif': [
                {'email_to': [email], 'type': 'email', 'status': 'sent'}
                for email in [new_valid_email, self.valid_email]
            ]}]
        )
        self.assertEqual(wizard.notification_ids, done_notifs)
        self.assertEqual(done_msgs, message)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('admin')
    def test_cancel_half_email(self):
        self._reset_bus()
        with self.mock_mail_gateway(), self.assertBus([(self.cr.dbname, 'res.partner', self.partner_admin.id)]):
            def _connect(*args, **kwargs):
                raise Exception("Some exception")
            self.connect_mocked.side_effect = _connect

            mails_sudo, _ = self.valid_composer.with_user(self.env.user)._action_send_mail()
        message = mails_sudo.mail_message_id

        self.assertMailNotifications(message, [{
            'content': 'Test Body', 'message_type': 'email_outgoing', 'subtype': None,
            'notif': [
                {'email_to': [email], 'type': 'email', 'status': 'exception'}
                for email in self.valid_emails
            ]}]
        )

        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})
        email_addrs = set(wizard.recipient_ids.mapped("email"))
        self.assertEqual(self.valid_emails, email_addrs)
        wizard.recipient_ids.filtered(lambda c: c.email == self.valid_email2).write({"resend": False})
        with self.mock_mail_gateway():
            wizard.resend_mail_action()

        self.assertMailNotifications(message, [{
            'content': 'Test Body', 'message_type': 'email_outgoing', 'subtype': None,
            'notif': [
                {
                    'email_to': [email], 'type': 'email',
                    'status': (email == self.valid_email and 'sent') or (email == self.valid_email2 and 'canceled') or 'sent'
                } for email in self.valid_emails
            ]}]
        )

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('admin')
    def test_cancel_all_email(self):
        self._reset_bus()
        with self.mock_mail_gateway(), self.assertBus([(self.cr.dbname, 'res.partner', self.partner_admin.id)]):
            def _connect(*args, **kwargs):
                raise Exception("Some exception")
            self.connect_mocked.side_effect = _connect

            mails_sudo, _ = self.valid_composer.with_user(self.env.user)._action_send_mail()
        message = mails_sudo.mail_message_id

        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})

        self._reset_bus()
        expected_bus_notifications = [
            (self.cr.dbname, 'res.partner', self.partner_admin.id),
        ]
        with self.mock_mail_gateway(), self.assertBus(expected_bus_notifications):
            wizard.cancel_mail_action()

        self.assertMailNotifications(message, [{
            'content': 'Test Body', 'message_type': 'email_outgoing', 'subtype': self.env['mail.message.subtype'],
            'notif': [{
                'email_to': [email], 'type': 'email', 'check_send': True, 'status': 'canceled'
            } for email in self.valid_emails
            ]}]
        )

    @mute_logger('odoo.sql_db')
    @users('admin')
    def test_resend_invalid(self):
        """Check attempting to resend to invalid/empty emails fails, but updating the email works."""
        for composer, name in [(self.invalid_composer, 'invalid email'), (self.empty_composer, 'empty email')]:
            with self.subTest(name=name):
                self._reset_bus()
                # no point in explicitly notifying front-end in mass mail context as it's all mail-based
                with self.mock_mail_gateway(), self.assertBus([]):
                    mails_sudo, _ = self.invalid_composer.with_user(self.env.user)._action_send_mail()
                message = mails_sudo.mail_message_id

                wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})

                recipient = wizard.recipient_ids
                for email_val in [recipient.email, "anotherinvalidaddress", ""]:
                    with self.subTest(recipient_email=email_val):
                        recipient.email = email_val
                        with self.assertRaisesRegex(UserError, "Email should be re-sent to valid email addresses"):
                            wizard.resend_mail_action()

                new_valid_email = "invalidisnowvalid@test.lan"
                recipient.email = new_valid_email

                self._reset_bus()
                expected_bus_notifications = [
                    (self.cr.dbname, 'res.partner', self.partner_admin.id),
                ]
                with self.mock_mail_gateway(), self.assertBus(expected_bus_notifications):
                    wizard.resend_mail_action()
                done_msgs, done_notifs = self.assertMailNotifications(message, [{
                    'content': 'Test Body', 'message_type': 'email_outgoing', 'subtype': None,
                    'notif': [
                        {'email_to': [new_valid_email], 'type': 'email', 'status': 'sent'}
                    ]}]
                )
