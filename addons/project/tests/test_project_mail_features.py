from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE
from odoo.tests import tagged, users
from odoo.tools import formataddr, mute_logger
from odoo.tools.mail import email_normalize


@tagged('post_install', '-at_install', 'mail_flow', 'mail_tools')
class TestProjectMailFeatures(TestProjectCommon, MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # be sure to test emails
        cls.user_employee.notification_type = 'email'
        cls.user_projectuser.notification_type = 'email'
        cls.user_projectmanager.notification_type = 'inbox'

        # simple template used in auto acknowledgement
        cls.test_template = cls.env['mail.template'].create({
            'auto_delete': True,
            'body_html': '<p>Hello <t t-out="object.partner_id.name"/></p>',
            'lang': '{{ object.partner_id.lang or object.user_ids[:1].lang or user.lang }}',
            'model_id': cls.env['ir.model']._get_id('project.task'),
            'name': 'Test Acknowledge',
            'subject': 'Test Acknowledge {{ object.name }}',
            'use_default_to': True,
        })

        # Test followers-based project
        cls.project_followers = cls.env['project.project'].create({
            'alias_name': 'help',
            'name': 'Goats',
            'partner_id': cls.partner_1.id,
            'privacy_visibility': 'followers',
            'type_ids': [
                (0, 0, {
                    'mail_template_id': cls.test_template.id,
                    'name': 'New',
                    'sequence': 1,
                }),
                (0, 0, {
                    'name': 'Validated',
                    'sequence': 10,
                })],
        })
        cls.project_followers_alias = cls.project_followers.alias_id
        # add some project followers to check followers propagation notably
        cls.project_followers.message_subscribe(
            partner_ids=(cls.user_projectuser.partner_id + cls.user_projectmanager.partner_id).ids,
            # follow 'new tasks' to receive notification for incoming emails directly
            subtype_ids=(cls.env.ref('mail.mt_comment') + cls.env.ref('project.mt_project_task_new')).ids
        )

    def setUp(self):
        super().setUp()
        with mute_logger('odoo.addons.mail.models.mail_thread'):
            self.test_task = self.format_and_process(
                MAIL_TEMPLATE, self.user_portal.email_formatted,
                self.project_followers_alias.alias_full_name,
                cc=self.partner_2.email_formatted,
                subject='Data Test Task',
                target_model='project.task',
            )
            self.flush_tracking()

    def test_assert_initial_values(self):
        """ Check base values coherency for tests clarity """
        self.assertEqual(
            self.project_followers.message_partner_ids,
            self.user_projectuser.partner_id + self.user_projectmanager.partner_id)
        self.assertEqual(self.test_task.project_id, self.project_followers)

        # check for partner creation, should not pre-exist
        self.assertFalse(self.env['res.partner'].search(
            [('email_normalized', 'in', {'new.cc@test.agrolait.com', 'new.customer@test.agrolait.com', 'new.author@test.agrolait.com'})])
        )

    def test_project_notify_get_recipients_groups(self):
        projects = self.env['project.project'].create([
            {
                'name': 'public project',
                'privacy_visibility': 'portal',
                'partner_id': self.partner_1.id,
            },
            {
                'name': 'internal project',
                'privacy_visibility': 'employees',
                'partner_id': self.partner_1.id,
            },
            {
                'name': 'private project',
                'privacy_visibility': 'followers',
                'partner_id': self.partner_1.id,
            },
        ])
        for project in projects:
            groups = project._notify_get_recipients_groups(self.env['mail.message'], False)
            groups_per_key = {g[0]: g for g in groups}
            for key, group in groups_per_key.items():
                has_button_access = group[2]['has_button_access']
                if key in ['portal', 'portal_customer']:
                    self.assertEqual(
                        has_button_access,
                        project.name == 'public project',
                        "Only the public project should have its name clickable in the email sent to the customer when an email is sent via a email template set in the project stage for instance."
                    )
                elif key == 'user':
                    self.assertTrue(has_button_access)

    def test_task_creation_no_stage(self):
        """ Test receiving email in a project without stage, should create task as intended """
        internal_followers = self.user_projectuser.partner_id + self.user_projectmanager.partner_id
        self.project_followers.type_ids = [(5, 0)]

        with self.mock_mail_gateway():
            task = self.format_and_process(
                MAIL_TEMPLATE,
                self.user_portal.email_formatted,
                f'{self.project_followers_alias.alias_full_name}, {self.partner_1.email_formatted}, "New Customer" <new.customer@test.agrolait.com>',
                cc=f'"New Cc" <new.cc@test.agrolait.com>, {self.partner_2.email_formatted}',
                subject=f'Test from {self.user_portal.name}',
                target_model='project.task',
            )
            self.flush_tracking()
        self.assertEqual(task.project_id, self.project_followers)
        self.assertFalse(task.stage_id)

        self.assertEqual(len(task.message_ids), 1)
        self.assertMailNotifications(
            task.message_ids,
            [
                {
                    'content': 'Please call me as soon as possible',
                    'message_type': 'email',
                    'message_values': {
                        'author_id': self.user_portal.partner_id,
                        'email_from': self.user_portal.email_formatted,
                        'mail_server_id': self.env['ir.mail_server'],
                        # followers of 'new task' subtype (but not original To as they
                        # already received the email)
                        'notified_partner_ids': internal_followers,
                        # deduced from 'To' and 'Cc' (recognized only)
                        'partner_ids': self.partner_1 + self.partner_2,
                        'parent_id': self.env['mail.message'],
                        'reply_to': formataddr((
                            f'{self.env.company.name} {self.project_followers.name}',
                            self.project_followers_alias.alias_full_name
                        )),
                        'subject': f'Test from {self.user_portal.name}',
                        'subtype_id': self.env.ref('project.mt_task_new'),
                    },
                    'notif': [
                        {'partner': self.user_projectmanager.partner_id, 'type': 'inbox',},
                        {'partner': self.user_projectuser.partner_id, 'type': 'email',},
                    ],
                },
            ],
        )

    def test_task_creation_notifies_author(self):
        """ Check auto acknowledgment mail sent at new task. It should notify
        task creator, based on stage template. """
        internal_followers = self.user_projectuser.partner_id + self.user_projectmanager.partner_id
        new_partner_email = '"New Author" <new.author@test.agrolait.com>'

        for test_user in (self.user_employee, self.user_portal, False):
            with self.subTest(user_name=test_user.name if test_user else new_partner_email):
                email_from = test_user.email_formatted if test_user else new_partner_email
                with self.mock_mail_gateway():
                    task = self.format_and_process(
                        MAIL_TEMPLATE, email_from,
                        f'{self.project_followers_alias.alias_full_name}, {self.partner_1.email_formatted}, "New Customer" <new.customer@test.agrolait.com>',
                        cc=f'"New Cc" <new.cc@test.agrolait.com>, {self.partner_2.email_formatted}',
                        subject=f'Test from {email_from}',
                        target_model='project.task',
                    )
                    self.flush_tracking()

                if test_user:
                    author = test_user.partner_id
                else:
                    author = self.env['res.partner'].search([('email_normalized', '=', 'new.author@test.agrolait.com')])
                    self.assertTrue(author, 'Project automatically creates a partner for incoming email')
                    self.assertEqual(author.email, 'new.author@test.agrolait.com', 'Should parse name/email correctly')
                    self.assertEqual(author.name, 'New Author', 'Should parse name/email correctly')

                # do not converts Cc into partners, used only to populate email_cc field
                new_partner_cc = self.env['res.partner'].search([('email_normalized', '=', 'new.cc@test.agrolait.com')])
                self.assertFalse(new_partner_cc)
                # do not convert other people in To, simply recognized if they exist
                new_partner_to = self.env['res.partner'].search([('email_normalized', '=', 'new.customer@test.agrolait.com')])
                self.assertFalse(new_partner_to)

                self.assertIn('Please call me as soon as possible', task.description)
                self.assertEqual(task.email_cc, f'"New Cc" <new.cc@test.agrolait.com>, {self.partner_2.email_formatted}')
                # email cc is transformed into partner when sending ack email, hence not
                # added in followers at task creation time; recognized cc is added
                self.assertEqual(task.message_partner_ids, internal_followers + author + self.partner_1 + self.partner_2)
                self.assertEqual(task.name, f'Test from {author.email_formatted}')
                self.assertEqual(task.partner_id, author)
                self.assertEqual(task.project_id, self.project_followers)
                self.assertEqual(task.stage_id, self.project_followers.type_ids[0])

                self.assertEqual(len(task.message_ids), 2)
                # first message: incoming email: sent to email followers
                incoming_email = task.message_ids[1]
                self.assertMailNotifications(
                    incoming_email,
                    [
                        {
                            'content': 'Please call me as soon as possible',
                            'message_type': 'email',
                            'message_values': {
                                'author_id': author,
                                'email_from': formataddr((author.name, author.email_normalized)),
                                'mail_server_id': self.env['ir.mail_server'],
                                # followers of 'new task' subtype (but not original To as they
                                # already received the email)
                                'notified_partner_ids': internal_followers,
                                # deduced from 'To' and 'Cc' (recognized partners)
                                'partner_ids': self.partner_1 + self.partner_2,
                                'parent_id': self.env['mail.message'],
                                'reply_to': formataddr((
                                    f'{self.env.company.name} {self.project_followers.name}',
                                    self.project_followers_alias.alias_full_name
                                )),
                                'subject': f'Test from {author.email_formatted}',
                                'subtype_id': self.env.ref('project.mt_task_new'),
                            },
                            'notif': [
                                {'partner': self.user_projectmanager.partner_id, 'type': 'inbox',},
                                {'partner': self.user_projectuser.partner_id, 'type': 'email',},
                            ],
                        },
                    ],
                )

                # second message: acknowledgment: sent to email author
                acknowledgement = task.message_ids[0]
                # task created by odoobot if not incoming user -> odoobot author of ack email
                acknowledgement_author = test_user.partner_id if test_user else self.partner_root
                self.assertMailNotifications(
                    acknowledgement,
                    [
                        {
                            'content': f'Hello {author.name}',
                            'message_type': 'auto_comment',
                            'message_values': {
                                'author_id': acknowledgement_author,
                                'email_from': acknowledgement_author.email_formatted,
                                'mail_server_id': self.env['ir.mail_server'],
                                # default recipients: partner_id, no note followers
                                'notified_partner_ids': author,
                                # default recipients: partner_id
                                'partner_ids': author,
                                'parent_id': incoming_email,
                                'reply_to': formataddr((
                                    f'{self.env.company.name} {self.project_followers.name}',
                                    self.project_followers_alias.alias_full_name
                                )),
                                'subject': f'Test Acknowledge {task.name}',
                                'subtype_id': self.env.ref('mail.mt_note'),
                            },
                            'notif': [
                                # specific email for portal customer, due to portal mixin
                                {'partner': author, 'type': 'email', 'group': 'portal_customer',},
                            ],
                        },
                    ],
                )

                # uses Chatter: fetches suggested recipients, post a message
                # - checks all suggested: incoming email to + cc are included
                # - for all notified people: expected 'email_to' is them
                # ------------------------------------------------------------
                suggested_all = task.with_user(self.user_projectuser)._message_get_suggested_recipients()
                expected_all = [
                    {  # mail.thread.cc: email_cc field
                        'create_values': {},
                        'email': '"New Cc" <new.cc@test.agrolait.com>',
                        'lang': None,
                        'name': '"New Cc" <new.cc@test.agrolait.com>',
                        'reason': 'CC Email',
                    },
                    # other CC (partner_2) and customer (partner_id) already follower
                ]
                for suggested, expected in zip(suggested_all, expected_all):
                    self.assertDictEqual(suggested, expected)
                # check recipients, which creates them (simulating discuss in a quick way)
                task.with_user(self.user_projectuser)._partner_find_from_emails_single([sug['email'] for sug in suggested_all])
                new_partner_cc = self.env['res.partner'].search([('email_normalized', '=', 'new.cc@test.agrolait.com')])
                self.assertEqual(new_partner_cc.email, 'new.cc@test.agrolait.com')
                self.assertEqual(new_partner_cc.name, 'New Cc')

                # finally post the message with recipients
                with self.mock_mail_gateway():
                    responsible_answer = task.with_user(self.user_projectuser).message_post(
                        body='<p>Well received !',
                        partner_ids=new_partner_cc.ids,
                        message_type='comment',
                        subject=f'Re: {task.name}',
                        subtype_id=self.env.ref('mail.mt_comment').id,
                    )
                self.assertEqual(task.message_partner_ids, internal_followers + author + self.partner_1 + self.partner_2)

                expected_chatter_reply_to = formataddr(
                    (f'{self.env.company.name} {self.project_followers.name}', self.project_followers_alias.alias_full_name)
                )
                self.assertMailNotifications(
                    responsible_answer,
                    [
                        {
                            'content': 'Well received !',
                            'mail_mail_values': {
                                'mail_server_id': self.env['ir.mail_server'],  # no specified server
                            },
                            'message_type': 'comment',
                            'message_values': {
                                'author_id': self.user_projectuser.partner_id,
                                'email_from': self.user_projectuser.partner_id.email_formatted,
                                'mail_server_id': self.env['ir.mail_server'],
                                # projectuser not notified of its own message, even if follower
                                'notified_partner_ids': self.user_projectmanager.partner_id + author + self.partner_1 + self.partner_2 + new_partner_cc,
                                'parent_id': incoming_email,
                                'partner_ids': new_partner_cc,
                                'reply_to': expected_chatter_reply_to,
                                'subtype_id': self.env.ref('mail.mt_comment'),
                            },
                            'notif': [
                                # original author has a specific email with links and tokens
                                {'partner': author, 'type': 'email', 'group': 'portal_customer'},
                                {'partner': self.partner_1, 'type': 'email'},
                                {'partner': self.partner_2, 'type': 'email'},
                                {'partner': new_partner_cc, 'type': 'email'},
                                {'partner': self.user_projectmanager.partner_id, 'type': 'inbox'},
                            ],
                        },
                    ],
                )

                # SMTP emails really sent (not Inbox guy then), checking Msg[To] notably
                # as well as Msg[From] which depends on smtp server
                for partner in (responsible_answer.notified_partner_ids - self.user_projectmanager.partner_id):
                    with self.subTest(name=partner.name):
                        self.assertSMTPEmailsSent(
                            mail_server=self.mail_server_notification,
                            msg_from=formataddr((self.user_projectuser.name, f'{self.default_from}@{self.alias_domain}')),
                            smtp_from=self.mail_server_notification.from_filter,
                            smtp_to_list=[partner.email_normalized],
                            msg_to_lst=[partner.email_formatted],
                        )

                # customer replies using "Reply All" + adds new people
                # ------------------------------------------------------------
                self.gateway_mail_reply_from_smtp_email(
                    MAIL_TEMPLATE, [author.email_normalized], reply_all=True,
                    cc=f'"Another Cc" <another.cc@test.agrolait.com>, {self.partner_3.email}',  # used mainly for existing partners currently
                    target_model='project.task',
                )
                self.assertEqual(
                    task.email_cc,
                    '"Another Cc" <another.cc@test.agrolait.com>, valid.poilboeuf@gmail.com, "New Cc" <new.cc@test.agrolait.com>, "Valid Poilvache" <valid.other@gmail.com>',
                    'Updated with new Cc')
                self.assertEqual(len(task.message_ids), 4, 'Incoming email + acknowledgement + chatter reply + customer reply')
                self.assertEqual(task.message_partner_ids, internal_followers + author + self.partner_1 + self.partner_2 + self.partner_3)

                self.assertMailNotifications(
                    task.message_ids[0],
                    [
                        {
                            'content': 'Please call me as soon as possible',
                            'message_type': 'email',
                            'message_values': {
                                'author_id': author,
                                'email_from': author.email_formatted,
                                'mail_server_id': self.env['ir.mail_server'],
                                # notified: followers, behaves like classic post
                                'notified_partner_ids': internal_followers + self.partner_1 + self.partner_2 + self.partner_3,
                                'parent_id': incoming_email,
                                # reply-all when being only recipients = no other recipients
                                'partner_ids': self.partner_3,
                                'subject': f'Re: Re: {task.name}',
                                'subtype_id': self.env.ref('mail.mt_comment'),
                            },
                            'notif': [
                                {'partner': self.user_projectuser.partner_id, 'type': 'email',},
                                {'partner': self.user_projectmanager.partner_id, 'type': 'inbox',},
                                {'partner': self.partner_1, 'type': 'email',},
                                {'partner': self.partner_2, 'type': 'email',},
                                {'partner': self.partner_3, 'type': 'email',},
                            ],
                        },
                    ],
                )

                # clear for other loops
                (new_partner_cc + new_partner_to).unlink()

    @users('bastien')
    def test_task_notification_on_project_update(self):
        """ Test changing task's project notifies people following 'New Task' """
        test_task = self.test_task.with_user(self.env.user)
        with self.mock_mail_gateway():
            test_task.project_id = False
            self.flush_tracking()
        # voiding project should not do anything
        self.assertNotSentEmail()

        with self.mock_mail_gateway():
            test_task.project_id = self.project_goats.id
            self.flush_tracking()
        self.assertNotSentEmail()

        with self.mock_mail_gateway():
            test_task.project_id = self.project_followers.id
            self.flush_tracking()

        # find notification, not in message_ids as it is a personal message
        notification_msg = self.env['mail.message'].search([
            ('model', '=', 'project.task'), ('res_id', '=', test_task.id),
            ('body', 'ilike', 'Transferred from Project')
        ])
        self.assertTrue(notification_msg)

        # should trigger a notification
        self.assertSentEmail(self.env.user.email_formatted, [self.user_projectuser.email_formatted])

        self.assertMailNotifications(
            notification_msg,
            [
                {
                    'content': 'Transferred from Project',
                    'message_type': 'user_notification',
                    'message_values': {
                        'author_id': self.user_projectmanager.partner_id,
                        'email_from': self.user_projectmanager.partner_id.email_formatted,
                        'mail_server_id': self.env['ir.mail_server'],
                        # followers of 'new task' type but not author itself
                        'notified_partner_ids': self.user_projectuser.partner_id,
                        # followers of 'new task' type
                        'partner_ids': (self.user_projectuser + self.user_projectmanager).partner_id,
                        'parent_id': self.env['mail.message'],
                        'reply_to': formataddr((
                            f'{self.env.company.name} {self.project_followers.name}',
                            self.project_followers_alias.alias_full_name
                        )),
                        'subject': test_task.name,
                        'subtype_id': self.env.ref('mail.mt_note'),
                    },
                    'notif': [
                        {'partner': self.user_projectuser.partner_id, 'type': 'email',},
                    ],
                },
            ],
        )

    def test_task_notification_on_user_ids_update(self):
        """ This test will check that an assignment mail is sent when adding an assignee to a task """
        # avoid messing with followers to ease notif check
        self.project_followers.message_unsubscribe(partner_ids=self.project_followers.message_partner_ids.ids)

        with self.mock_mail_gateway():
            test_task = self.env['project.task'].create({
                'name': 'Mail Task',
                'user_ids': self.user_projectuser,
                'project_id': self.project_followers.id
            })
            self.flush_tracking()
        self.assertSentEmail(self.env.user.email_formatted, [self.user_projectuser.email_formatted])

        with self.mock_mail_gateway():
            test_task.copy()
            self.flush_tracking()
        # check that no mail was received for the assignee of the task
        self.assertNotSentEmail(self.user_projectuser.email_formatted)
