from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE
from odoo.tests import tagged, users, new_test_user
from odoo.tools import formataddr, mute_logger
from odoo.fields import Command


@tagged('post_install', '-at_install', 'mail_flow', 'mail_tools')
class TestProjectMailFeatures(TestProjectCommon, MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # set high threshold to be sure to not hit mail limit during tests for a model
        cls.env['ir.config_parameter'].sudo().set_param('mail.gateway.loop.threshold', 50)

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

        incoming_cc = f'"New Cc" <new.cc@test.agrolait.com>, {self.partner_2.email_formatted}'
        incoming_to = f'{self.project_followers_alias.alias_full_name}, {self.partner_1.email_formatted}, "New Customer" <new.customer@test.agrolait.com>'
        incoming_to_filtered = f'{self.partner_1.email_formatted}, "New Customer" <new.customer@test.agrolait.com>'
        with self.mock_mail_gateway():
            task = self.format_and_process(
                MAIL_TEMPLATE,
                self.user_portal.email_formatted,
                incoming_to,
                cc=incoming_cc,
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
                        # coming from incoming email
                        'incoming_email_cc': incoming_cc,
                        'incoming_email_to': incoming_to_filtered,
                        'mail_server_id': self.env['ir.mail_server'],
                        # followers of 'new task' subtype (but not original To as they
                        # already received the email)
                        'notified_partner_ids': internal_followers,
                        # deduced from 'To' and 'Cc' (recognized only)
                        'partner_ids': self.partner_1 + self.partner_2,
                        'parent_id': self.env['mail.message'],
                        'reply_to': formataddr((
                            self.user_portal.name,
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

        incoming_cc = f'"New Cc" <new.cc@test.agrolait.com>, {self.partner_2.email_formatted}'
        incoming_to = f'{self.project_followers_alias.alias_full_name}, {self.partner_1.email_formatted}, "New Customer" <new.customer@test.agrolait.com>'
        incoming_to_filtered = f'{self.partner_1.email_formatted}, "New Customer" <new.customer@test.agrolait.com>'
        for test_user in (self.user_employee, self.user_portal, False):
            with self.subTest(user_name=test_user.name if test_user else new_partner_email):
                email_from = test_user.email_formatted if test_user else new_partner_email
                with self.mock_mail_gateway():
                    task = self.format_and_process(
                        MAIL_TEMPLATE, email_from,
                        incoming_to,
                        cc=incoming_cc,
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
                new_partner_customer = self.env['res.partner'].search([('email_normalized', '=', 'new.customer@test.agrolait.com')])
                self.assertFalse(new_partner_customer)

                self.assertIn('Please call me as soon as possible', task.description)
                self.assertEqual(task.email_cc, f'"New Cc" <new.cc@test.agrolait.com>, {self.partner_2.email_formatted}, {self.partner_1.email_formatted}, "New Customer" <new.customer@test.agrolait.com>')
                self.assertEqual(task.name, f'Test from {author.email_formatted}')
                self.assertEqual(task.partner_id, author)
                self.assertEqual(task.project_id, self.project_followers)
                self.assertEqual(task.stage_id, self.project_followers.type_ids[0])
                # followers: email cc is added in followers at creation time, aka only recognized partners
                self.assertEqual(task.message_partner_ids, internal_followers + author + self.partner_1 + self.partner_2)
                # messages
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
                                # coming from incoming email
                                'incoming_email_cc': incoming_cc,
                                'incoming_email_to': incoming_to_filtered,
                                'mail_server_id': self.env['ir.mail_server'],
                                # followers of 'new task' subtype (but not original To as they
                                # already received the email)
                                'notified_partner_ids': internal_followers,
                                # deduced from 'To' and 'Cc' (recognized partners)
                                'partner_ids': self.partner_1 + self.partner_2,
                                'parent_id': self.env['mail.message'],
                                'reply_to': formataddr((author.name, self.project_followers_alias.alias_full_name)),
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
                                'incoming_email_cc': False,
                                'incoming_email_to': False,
                                'mail_server_id': self.env['ir.mail_server'],
                                # default recipients: partner_id, no note followers
                                'notified_partner_ids': author,
                                # default recipients: partner_id
                                'partner_ids': author,
                                'parent_id': incoming_email,
                                'reply_to': formataddr((acknowledgement_author.name, self.project_followers_alias.alias_full_name)),
                                'subject': f'Test Acknowledge {task.name}',
                                # defined by _track_template
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
                # - checks all suggested: email_cc field, primary email
                # ------------------------------------------------------------
                suggested_all = task.with_user(self.user_projectuser)._message_get_suggested_recipients(
                    reply_discussion=True, no_create=False,
                )
                new_partner_cc = self.env['res.partner'].search(
                    [('email_normalized', '=', 'new.cc@test.agrolait.com')]
                )
                self.assertEqual(new_partner_cc.email, 'new.cc@test.agrolait.com')
                self.assertEqual(new_partner_cc.name, 'New Cc')
                new_partner_customer = self.env['res.partner'].search(
                    [('email_normalized', '=', 'new.customer@test.agrolait.com')]
                )
                self.assertEqual(new_partner_customer.email, 'new.customer@test.agrolait.com')
                self.assertEqual(new_partner_customer.name, 'New Customer')
                expected_all = []
                if not test_user:
                    expected_all = [
                        {  # last message recipient is proposed
                            'create_values': {},
                            'email': 'new.author@test.agrolait.com',
                            'name': 'New Author',
                            'partner_id': author.id,  # already created by project upon initial email reception
                        }
                    ]
                elif test_user == self.user_portal:
                    expected_all = [
                        {  # customer is proposed, even if follower, because shared
                            'create_values': {},
                            'email': self.user_portal.email_normalized,
                            'name': self.user_portal.name,
                            'partner_id': self.user_portal.partner_id.id,
                        }
                    ]
                expected_all += [
                    {  # mail.thread.cc: email_cc field
                        'create_values': {},
                        'email': 'new.cc@test.agrolait.com',
                        'name': 'New Cc',
                        'partner_id': new_partner_cc.id,
                    },
                    {  # incoming email other recipients (new.customer)
                        'create_values': {},
                        'email': 'new.customer@test.agrolait.com',
                        'name': 'New Customer',
                        'partner_id': new_partner_customer.id,
                    },
                    # other CC (partner_2) and customer (partner_id) already follower
                ]
                for suggested, expected in zip(suggested_all, expected_all, strict=True):
                    self.assertDictEqual(suggested, expected)

                # finally post the message with recipients
                with self.mock_mail_gateway():
                    recipients = new_partner_cc + new_partner_customer
                    if not test_user:
                        recipients += author
                    responsible_answer = task.with_user(self.user_projectuser).message_post(
                        body='<p>Well received !',
                        partner_ids=recipients.ids,
                        message_type='comment',
                        subject=f'Re: {task.name}',
                        subtype_id=self.env.ref('mail.mt_comment').id,
                    )
                self.assertEqual(task.message_partner_ids, internal_followers + author + self.partner_1 + self.partner_2)

                external_partners = self.partner_1 + self.partner_2 + new_partner_cc + new_partner_customer
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
                                'incoming_email_cc': False,
                                'incoming_email_to': False,
                                'mail_server_id': self.env['ir.mail_server'],
                                # projectuser not notified of its own message, even if follower
                                'notified_partner_ids': self.user_projectmanager.partner_id + author + external_partners,
                                'parent_id': incoming_email,
                                # coming from post
                                'partner_ids': recipients,
                                'reply_to': formataddr((self.user_projectuser.name, self.project_followers_alias.alias_full_name)),
                                'subject': f'Re: {task.name}',
                                'subtype_id': self.env.ref('mail.mt_comment'),
                            },
                            'notif': [
                                # original author has a specific email with links and tokens
                                {'partner': author, 'type': 'email', 'group': 'portal_customer'},
                                {'partner': self.partner_1, 'type': 'email'},
                                {'partner': self.partner_2, 'type': 'email'},
                                {'partner': new_partner_cc, 'type': 'email'},
                                {'partner': new_partner_customer, 'type': 'email'},
                                {'partner': self.user_projectmanager.partner_id, 'type': 'inbox'},
                            ],
                        },
                    ],
                )

                # SMTP emails really sent (not Inbox guy then)
                # expected Msg['To'] : Reply-All behavior: actual recipient, then
                # all "not internal partners" and catchall (to receive answers)
                for partner in (responsible_answer.notified_partner_ids - self.user_projectmanager.partner_id):
                    exp_msg_to_partners = partner | external_partners
                    if author != self.user_employee.partner_id:  # external only !
                        exp_msg_to_partners |= author
                    exp_msg_to = exp_msg_to_partners.mapped('email_formatted')
                    with self.subTest(name=partner.name):
                        self.assertSMTPEmailsSent(
                            mail_server=self.mail_server_notification,
                            msg_from=formataddr((self.user_projectuser.name, f'{self.default_from}@{self.alias_domain}')),
                            smtp_from=self.mail_server_notification.from_filter,
                            smtp_to_list=[partner.email_normalized],
                            msg_to_lst=exp_msg_to,
                        )

                # customer replies using "Reply All" + adds new people
                # ------------------------------------------------------------
                self.gateway_mail_reply_from_smtp_email(
                    MAIL_TEMPLATE, [author.email_normalized], reply_all=True,
                    cc=f'"Another Cc" <another.cc@test.agrolait.com>, {self.partner_3.email}',
                    target_model='project.task',
                )
                self.assertEqual(
                    task.email_cc,
                    '"Another Cc" <another.cc@test.agrolait.com>, valid.poilboeuf@gmail.com, "New Cc" <new.cc@test.agrolait.com>, '
                    '"Valid Poilvache" <valid.other@gmail.com>, "Valid Lelitre" <valid.lelitre@agrolait.com>, "New Customer" <new.customer@test.agrolait.com>',
                    'Updated with new Cc')
                self.assertEqual(len(task.message_ids), 4, 'Incoming email + acknowledgement + chatter reply + customer reply')
                self.assertEqual(
                    task.message_partner_ids,
                    internal_followers + author + self.partner_1 + self.partner_2 + self.partner_3 + new_partner_cc + new_partner_customer,
                    'Project adds recognized recipients as followers')

                self.assertMailNotifications(
                    task.message_ids[0],
                    [
                        {
                            'content': 'Please call me as soon as possible',
                            'message_type': 'email',
                            'message_values': {
                                'author_id': author,
                                'email_from': author.email_formatted,
                                # coming from incoming email
                                'incoming_email_cc': f'"Another Cc" <another.cc@test.agrolait.com>, {self.partner_3.email}',
                                # To: received email Msg-To - customer who replies, without email Reply-To
                                'incoming_email_to': ', '.join(external_partners.mapped('email_formatted')),
                                'mail_server_id': self.env['ir.mail_server'],
                                # notified: followers - already emailed, aka internal only
                                'notified_partner_ids': internal_followers,
                                'parent_id': responsible_answer,
                                # same reasoning as email_to/cc
                                'partner_ids': external_partners + self.partner_3,
                                'reply_to': formataddr((author.name, self.project_followers_alias.alias_full_name)),
                                'subject': f'Re: Re: {task.name}',
                                'subtype_id': self.env.ref('mail.mt_comment'),
                            },
                            'notif': [
                                {'partner': self.user_projectuser.partner_id, 'type': 'email',},
                                {'partner': self.user_projectmanager.partner_id, 'type': 'inbox',},
                            ],
                        },
                    ],
                )

                # clear for other loops
                (new_partner_cc + new_partner_customer).unlink()

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
                        'reply_to': formataddr((self.user_projectmanager.name, self.project_followers_alias.alias_full_name
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

    def test_copy_task_logs_chatter(self):
        """Test that copying a task logs a message in the chatter."""
        copied_task = self.task_1.copy()

        # Ensure only one message is logged in chatter
        self.assertEqual(
            'Task Created', copied_task.message_ids[0].preview,
            "Expected 'Task Created' message not found in copied task's chatter."
        )

    def test_task_portal_share_adds_followers(self):
        """ Test that sharing a task through the portal share wizard adds recipients as followers.

            Test Cases:
            ===========
            1) Verify that the portal user is not a follower of the task.
            2) Create and execute a portal share wizard to share the task with the portal user.
            3) Verify that the portal user has been added as a follower after sharing.
        """

        self.assertNotIn(self.user_portal.partner_id, self.task_1.message_partner_ids,
                        "Portal user's partner should not be a follower initially")

        share_wizard = self.env['portal.share'].create({
            'res_model': 'project.task',
            'res_id': self.task_1.id,
            'partner_ids': [Command.set(self.user_portal.partner_id.ids)]
        })

        with self.mock_mail_gateway():
            share_wizard.action_send_mail()

        self.assertIn(self.user_portal.partner_id, self.task_1.message_partner_ids,
                    "Portal user's partner should be added as a follower after sharing")

    def test_mail_alais_assignees_from_recipient_list(self):
        # including all types of users in recipient list
        new_user = new_test_user(self.env, 'int_user')

        # format: Name <some@email.com>
        incoming_to_emails_with_name = (
            f"\"{self.project_goats.name}\" <{self.project_goats.alias_name}@{self.project_goats.alias_domain_id.name}>"
            f"\"{self.user_public.name}\" <{self.user_public.email}>,"
            f"\"{self.user_projectmanager.name}\" <{self.user_projectmanager.email}>,"
            f"\"{self.user_portal.name}\" <{self.user_portal.email}>,"
            f"\"{self.user_projectuser.name}\" <{self.user_projectuser.email}>,"
        )
        # format: some@email.com
        incoming_to_emails = (
            f"{self.project_goats.alias_name}@{self.project_goats.alias_domain_id.name},"
            f"{self.user_public.email},"
            f"{self.user_projectmanager.email},"
            f"{self.user_portal.email},"
            f"{self.user_projectuser.email},"
        )

        for incoming_to in [incoming_to_emails_with_name, incoming_to_emails]:
            with self.mock_mail_gateway():
                task = self.format_and_process(
                    MAIL_TEMPLATE,
                    self.user_employee.email,
                    incoming_to,
                    cc=f"{new_user.email}",
                    subject=f'Test task assignees from email to address with {incoming_to}',
                    target_model='project.task',
                )
                self.flush_tracking()
            self.assertTrue(task, "Task has not been created from a incoming email")
            # only internal users are set as asssignees
            self.assertEqual(task.user_ids, self.user_projectmanager + self.user_projectuser, "Assignees have not been set from the to address of the mail")
            # public and portal users are ignored
            self.assertNotIn(task.user_ids, self.user_public + self.user_portal, "Assignees should not be set for user other than internal users")
            # sender should not be added as user in the task
            self.assertNotIn(task.user_ids, self.user_employee, "Sender can never be in assignees")
            # internal users in cc of mail shoudl be added in email_cc field
            self.assertEqual(task.email_cc, new_user.email, "The internal user in CC is not added into email_cc field")

    def test_task_creation_removes_email_signatures(self):
        """
        Tests that email signature is correctly removed from a task
        description when a task is created from an email alias.
        """

        gmail_email_source = f"""From: "{self.user_portal.name}" <{self.user_portal.email_formatted}>
To: {self.project_followers_alias.alias_full_name}
Subject: Test Gmail Signature Removal
Content-Type: text/html;

<p>This is the main email content that should be kept.</p>
<p>Some more important content here.</p>
<span>--</span>
<div data-smartmail="gmail_signature">
<p>John Doe</p>
<p>Software Engineer</p>
</div>
"""

        outlook_email_source = f"""From: "{self.user_portal.name}" <{self.user_portal.email_formatted}>
To: {self.project_followers_alias.alias_full_name}
Subject: Test Outlook Signature Removal
Content-Type: text/html;

<p>This is the main email content that should be kept.</p>
<p>Some more important content here.</p>
<div id="Signature">
<p>John Smith</p>
<p>Software Developer</p>
</div>
"""

        with self.mock_mail_gateway():
            gmail_task_id = self.env['mail.thread'].message_process(
                model='project.task',
                message=gmail_email_source,
                custom_values={'project_id': self.project_followers.id}
            )
            outlook_task_id = self.env['mail.thread'].message_process(
                model='project.task',
                message=outlook_email_source,
                custom_values={'project_id': self.project_followers.id}
            )

        # Verify Gmail signature removal
        self.assertTrue(gmail_task_id, "Gmail task creation should return a valid ID.")
        gmail_task = self.env['project.task'].browse(gmail_task_id)

        self.assertIn("This is the main email content that should be kept", gmail_task.description)
        self.assertNotIn("--", gmail_task.description, "The Gmail signature separator should have been removed.")
        self.assertNotIn("John Doe", gmail_task.description, "The Gmail signature should have been removed.")
        self.assertNotIn("Software Engineer", gmail_task.description, "The Gmail signature should have been removed.")

        # Verify Outlook signature removal
        self.assertTrue(outlook_task_id, "Outlook task creation should return a valid ID.")
        outlook_task = self.env['project.task'].browse(outlook_task_id)

        self.assertIn("This is the main email content that should be kept", outlook_task.description)
        self.assertNotIn("John Smith", outlook_task.description, "The Outlook signature should have been removed.")
        self.assertNotIn("Software Developer", outlook_task.description, "The Outlook signature should have been removed.")

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_task_creation_from_mail(self):
        """ This test checks a `default_` key passed in the context with an invalid field doesn't prevent the task
            creation.

            This is related to the `_ensure_fields_write` method checking field write access rights
            for collaborator portals
        """
        server = self.env['fetchmail.server'].create({
            'name': 'Test server',
            'user': 'test@example.com',
            'password': '',
        })
        task_id = self.env["mail.thread"].with_context(
            default_fetchmail_server_id=server.id
        ).message_process(
            server.object_id.model,
            self.format(
                MAIL_TEMPLATE,
                email_from="chell@gladys.portal",
                to=f"project+pigs@{self.alias_domain}",
                subject="In a cage",
                msg_id="<on.antibiotics@example.com>",
            ),
            save_original=server.original,
            strip_attachments=not server.attach,
        )
        task = self.env['project.task'].browse(task_id)
        self.assertEqual(task.name, "In a cage")
        self.assertEqual(task.project_id, self.project_pigs)
