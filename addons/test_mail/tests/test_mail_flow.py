from odoo import tools
from odoo.addons.mail.tests.common import mail_new_test_user, MailCommon
from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE
from odoo.addons.test_mail.tests.common import TestRecipients
from odoo.tools.mail import formataddr
from odoo.tests import tagged


@tagged('mail_gateway', 'mail_flow', 'post_install', '-at_install')
class TestMailFlow(MailCommon, TestRecipients):
    """ Test flows matching business cases with incoming / outgoing emails. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_employee_2 = mail_new_test_user(
            cls.env,
            company_id=cls.user_employee.company_id.id,
            email='eglantine@example.com',
            groups='base.group_user,base.group_partner_manager',
            login='employee2',
            name='Eglantine Employee',
            notification_type='email',
            signature='--\nEglantine',
        )
        cls.partner_employee_2 = cls.user_employee_2.partner_id
        cls.user_employee_3 = mail_new_test_user(
            cls.env,
            company_id=cls.user_employee.company_id.id,
            email='emmanuel@example.com',
            groups='base.group_user,base.group_partner_manager',
            login='employee3',
            name='Emmanuel Employee',
            notification_type='email',
            signature='--\nEmmanuel',
        )
        cls.partner_employee_3 = cls.user_employee_3.partner_id
        cls.user_portal = cls._create_portal_user()
        cls.partner_portal = cls.user_portal.partner_id

        cls.test_emails = [
            # emails only
            '"Sylvie Lelitre" <sylvie.lelitre@zboing.com>',
            '"Josiane Quichopoils" <accounting@zboing.com>',
            'pay@zboing.com',
            'invoicing@zboing.com',
            # existing partners
            '"Robert Brutijus" <robert@zboing.com>',
            # existing portal users
            '"Portal Zboing" <portal@zboing.com>',
        ]
        cls.test_emails_normalized = [
            'sylvie.lelitre@zboing.com', 'accounting@zboing.com', 'invoicing@zboing.com',
            'pay@zboing.com', 'robert@zboing.com', 'portal@zboing.com',
        ]
        cls.customer_zboing = cls.env['res.partner'].create({
            'email': cls.test_emails[4],
            'name': 'Robert Brutijus',
            'phone': '+32455335577',
        })
        cls.user_portal_zboing = mail_new_test_user(
            cls.env,
            email=cls.test_emails[5],
            groups='base.group_portal',
            login='portal_zboing',
            name='Portal Zboing',
        )
        cls.customer_portal_zboing = cls.user_portal_zboing.partner_id

        # lead@test.mycompany.com will cause the creation of new mail.test.lead
        cls.mail_test_lead_model = cls.env['ir.model']._get('mail.test.lead')
        cls.alias = cls.env['mail.alias'].create({
            'alias_domain_id': cls.mail_alias_domain.id,
            'alias_contact': 'everyone',
            'alias_model_id': cls.mail_test_lead_model.id,
            'alias_name': 'lead',
        })
        # help@test.mycompany.com will cause the creation of new mail.test.ticket.mc
        cls.ticket_template = cls.env['mail.template'].create({
            'auto_delete': True,
            'body_html': '<p>Received <t t-out="object.name"/></p>',
            'email_from': '{{ object.user_id.email_formatted or user.email_formatted }}',
            'lang': '{{ object.customer_id.lang }}',
            'model_id': cls.env['ir.model']._get_id('mail.test.ticket.partner'),
            'name': 'Received',
            'subject': 'Received {{ object.name }}',
            'use_default_to': True,
        })
        cls.container = cls.env['mail.test.container.mc'].create({
            # triggers automatic answer yay !
            'alias_defaults': {'state': 'new', 'state_template_id': cls.ticket_template.id},
            'alias_name': 'help',
            'company_id': cls.user_employee.company_id.id,
            'name': 'help',
        })
        cls.container.alias_id.write({
            'alias_model_id': cls.env['ir.model']._get_id('mail.test.ticket.partner')
        })

    def test_assert_initial_values(self):
        """ Assert base values for tests """
        self.assertEqual(
            self.env['res.partner'].search([('email_normalized', 'in', self.test_emails_normalized)]),
            self.customer_zboing + self.customer_portal_zboing,
        )

    def test_lead_mailgateway(self):
        """ Flow of this test
        * incoming email creating a lead -> email set as first message
        * a salesperson is assigned
        * - he adds followers (internal and portal)
        * - he replies through chatter, using suggested recipients
        * - customer replies, adding other people

        Tested features
        * cc / to support
        * suggested recipients computation
        * outgoing SMTP envelope

        Recipients
        * incoming: From: sylvie (email) - To: employee, accounting (email) - Cc: pay (email), portal (portal)
        * reply: creates partner for sylvie and pay through suggested recipients
        * customer reply: Cc: invoicing (email) and robert (partner)
        """
        # incoming customer email: lead alias + recipients (to + cc)
        # ------------------------------------------------------------
        email_to = f'lead@{self.alias_domain}, {self.test_emails[1]}, {self.partner_employee.email_formatted}'
        email_cc = f'{self.test_emails[2]}, {self.test_emails[5]}'
        with self.mock_mail_gateway(), self.mock_mail_app():
            lead = self.format_and_process(
                MAIL_TEMPLATE,
                self.test_emails[0],
                email_to,
                cc=email_cc,
                subject='Inquiry',
                target_model='mail.test.lead',
            )
        self.assertEqual(lead.email_cc, email_cc, 'Filled by mail.thread.cc mixin')
        self.assertEqual(lead.email_from, self.test_emails[0])
        self.assertEqual(lead.name, 'Inquiry')
        self.assertFalse(lead.partner_id)
        # followers
        self.assertFalse(lead.message_partner_ids)
        # messages
        self.assertEqual(len(lead.message_ids), 1, 'Incoming email should be only message, no creation message')
        incoming_email = lead.message_ids
        self.assertMailNotifications(
            incoming_email,
            [
                {
                    'content': 'Please call me as soon as possible',
                    'message_type': 'email',
                    'message_values': {
                        'author_id': self.env['res.partner'],
                        'email_from': self.test_emails[0],
                        'incoming_email_cc': email_cc,
                        'incoming_email_to': email_to,
                        'mail_server_id': self.env['ir.mail_server'],
                        'parent_id': self.env['mail.message'],
                        'notified_partner_ids': self.env['res.partner'],
                        # only recognized partners
                        'partner_ids': self.partner_employee + self.customer_portal_zboing,
                        'subject': 'Inquiry',
                        'subtype_id': self.env.ref('mail.mt_comment'),
                    },
                    'notif': [],  # no notif, mailgateway sets recipients without notification
                },
            ],
        )

        # user is assigned, should notify him
        with self.mock_mail_gateway(), self.mock_mail_app():
            lead.write({'user_id': self.user_employee.id})
        lead_as_emp = lead.with_user(self.user_employee.id)
        self.assertEqual(lead_as_emp.message_partner_ids, self.partner_employee)

        # adds other employee and a portal customer as followers
        lead_as_emp.message_subscribe(partner_ids=(self.partner_employee_2 + self.partner_portal).ids)
        self.assertEqual(lead_as_emp.message_partner_ids, self.partner_employee + self.partner_employee_2 + self.partner_portal)
        # updates some customer information
        lead_as_emp.write({
            'customer_name': 'Sylvie Lelitre (Zboing)',
            'phone': '+32455001122',
            'lang_code': 'fr_FR',
        })

        # uses Chatter: fetches suggested recipients, post a message
        # - checks all suggested: email_cc field, primary email
        # ------------------------------------------------------------
        suggested_all = lead_as_emp._message_get_suggested_recipients(
            reply_discussion=True, no_create=False,
        )
        partner_sylvie = self.env['res.partner'].search(
            [('email_normalized', '=', 'sylvie.lelitre@zboing.com')]
        )
        partner_pay = self.env['res.partner'].search(
            [('email_normalized', '=', 'pay@zboing.com')]
        )
        partner_accounting = self.env['res.partner'].search(
            [('email_normalized', '=', 'accounting@zboing.com')]
        )
        expected_all = [
            {  # existing partners come first
                'create_values': {},
                'email': 'portal@zboing.com',
                'name': 'Portal Zboing',
                'partner_id': self.customer_portal_zboing.id,
            },
            {  # primary email comes first
                'create_values': {},
                'email': 'sylvie.lelitre@zboing.com',
                'name': 'Sylvie Lelitre (Zboing)',
                'partner_id': partner_sylvie.id,
            },
            {  # mail.thread.cc: email_cc field
                'create_values': {},
                'email': 'pay@zboing.com',
                'name': 'pay@zboing.com',
                'partner_id': partner_pay.id,
            },
            {  # reply message
                'create_values': {},
                'email': 'accounting@zboing.com',
                'name': 'Josiane Quichopoils',
                'partner_id': partner_accounting.id,
            },
        ]
        for suggested, expected in zip(suggested_all, expected_all):
            self.assertDictEqual(suggested, expected)

        # finally post the message with recipients
        with self.mock_mail_gateway():
            responsible_answer = lead_as_emp.message_post(
                body='<p>Well received !',
                partner_ids=(partner_sylvie + partner_pay + partner_accounting + self.customer_portal_zboing).ids,
                message_type='comment',
                subject=f'Re: {lead.name}',
                subtype_id=self.env.ref('mail.mt_comment').id,
            )
        self.assertEqual(lead_as_emp.message_partner_ids, self.partner_employee + self.partner_employee_2 + self.partner_portal)

        external_partners = partner_sylvie + partner_pay + partner_accounting + self.customer_portal_zboing + self.partner_portal
        internal_partners = self.partner_employee + self.partner_employee_2
        expected_chatter_reply_to = formataddr(
            (f'{self.env.company.name} {lead.name}', f'{self.alias_catchall}@{self.alias_domain}')
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
                        'author_id': self.partner_employee,
                        'email_from': self.partner_employee.email_formatted,
                        'incoming_email_cc': False,
                        'incoming_email_to': False,
                        'mail_server_id': self.env['ir.mail_server'],
                        # followers + recipients - author
                        'notified_partner_ids': external_partners + self.partner_employee_2,
                        'parent_id': incoming_email,
                        # matches posted message
                        'partner_ids': partner_sylvie + partner_pay + partner_accounting + self.customer_portal_zboing,
                        'reply_to': expected_chatter_reply_to,
                        'subtype_id': self.env.ref('mail.mt_comment'),
                    },
                    'notif': [
                        {'partner': partner_sylvie, 'type': 'email'},
                        {'partner': partner_pay, 'type': 'email'},
                        {'partner': partner_accounting, 'type': 'email'},
                        {'partner': self.customer_portal_zboing, 'type': 'email'},
                        {'partner': self.partner_employee_2, 'type': 'email'},
                        {'partner': self.partner_portal, 'type': 'email'},
                    ],
                },
            ],
        )
        # expected Msg['To'] : actual recipient, same as SMTP To
        for partner in responsible_answer.notified_partner_ids:
            with self.subTest(name=partner.name):
                self.assertSMTPEmailsSent(
                    mail_server=self.mail_server_notification,
                    msg_from=formataddr(
                        (self.partner_employee.name, f'{self.default_from}@{self.alias_domain}')
                    ),
                    smtp_from=self.mail_server_notification.from_filter,
                    smtp_to_list=[partner.email_normalized],
                    msg_to_lst=[partner.email_formatted],
                )

        # customer replies using "Reply" + adds new people
        # added: Cc: invoicing (email) and robert (partner)
        # ------------------------------------------------------------
        self.gateway_mail_reply_from_smtp_email(
            MAIL_TEMPLATE, [partner_sylvie.email_normalized], reply_all=False,
            cc=f'{self.test_emails[3]}, {self.test_emails[4]}',  # used mainly for existing partners currently
        )
        external_partners += self.customer_zboing  # added in CC just above
        self.assertEqual(len(lead.message_ids), 3, 'Incoming email + chatter reply + customer reply')
        self.assertEqual(
            lead.message_partner_ids,
            partner_sylvie + internal_partners + self.partner_portal,
            'Mail gateway: author (partner_sylvie) added in followers')

        customer_reply = lead.message_ids[0]
        self.assertMailNotifications(
            customer_reply,
            [
                {
                    'content': 'Please call me as soon as possible',
                    'message_type': 'email',
                    'message_values': {
                        'author_id': partner_sylvie,
                        'email_from': partner_sylvie.email_formatted,
                        # Cc: received email CC - an email still not partnerized (invoicing) and customer_zboing
                        'incoming_email_cc': f'{self.test_emails[3]}, {self.test_emails[4]}',
                        'incoming_email_to': expected_chatter_reply_to,  # reply_all not already implemented, hence just alias
                        'mail_server_id': self.env['ir.mail_server'],
                        # notified: followers, behaves like classic post, and not
                        # customer in Cc as gateway does not do double notification
                        'notified_partner_ids': internal_partners + self.partner_portal,
                        'parent_id': incoming_email,
                        # reply-all when being only recipients = only new To/Cc, with
                        # recognized partners only
                        'partner_ids': self.customer_zboing,
                        'subject': f'Re: Re: {lead.name}',
                        'subtype_id': self.env.ref('mail.mt_comment'),
                    },
                    # portal was already in email_to, hence not notified twice through odoo
                    'notif': [
                        {'partner': self.partner_employee, 'type': 'inbox'},
                        {'partner': self.partner_employee_2, 'type': 'email'},
                        {'partner': self.partner_portal, 'type': 'email'},
                    ],
                },
            ],
        )

    def test_ticket_mailgateway(self):
        """ Flow of this test
        * incoming email creating a ticket in 'new' state
        * automatic answer based on template
        """
        # incoming customer email: help alias + recipients (to + cc)
        # ------------------------------------------------------------
        email_to = f'help@{self.alias_domain}, {self.test_emails[1]}, {self.partner_employee.email_formatted}'
        email_cc = f'{self.test_emails[2]}, {self.test_emails[5]}'
        with self.mock_mail_gateway(), self.mock_mail_app():
            ticket = self.format_and_process(
                MAIL_TEMPLATE,
                self.test_emails[0],
                email_to,
                cc=email_cc,
                subject='Inquiry',
                target_model='mail.test.ticket.partner',
            )
            self.flush_tracking()

        # author -> partner, as automatic email creates partner
        partner_sylvie = self.env['res.partner'].search([('email_normalized', '=', 'sylvie.lelitre@zboing.com')])
        self.assertTrue(partner_sylvie, 'Acknowledgement template should create a partner for incoming email')
        self.assertEqual(partner_sylvie.email, 'sylvie.lelitre@zboing.com', 'Should parse name/email correctly')
        self.assertEqual(partner_sylvie.name, 'sylvie.lelitre@zboing.com', 'TDE FIXME: should parse name/email correctly')
        # create ticket
        self.assertEqual(ticket.container_id, self.container)
        self.assertEqual(
            ticket.customer_id, partner_sylvie,
            'Should put partner as customer, due to after hook')
        self.assertEqual(ticket.email_from, self.test_emails[0])
        self.assertEqual(ticket.name, 'Inquiry')
        self.assertEqual(ticket.state, 'new', 'Should come from alias defaults')
        self.assertEqual(ticket.state_template_id, self.ticket_template, 'Should come from alias defaults')
        # followers
        self.assertFalse(ticket.message_partner_ids)
        # messages
        self.assertEqual(len(ticket.message_ids), 3, 'Incoming email + Acknowledgement + Tracking')

        # first message: incoming email
        incoming_email = ticket.message_ids[2]
        self.assertMailNotifications(
            incoming_email,
            [
                {
                    'content': 'Please call me as soon as possible',
                    'message_type': 'email',
                    'message_values': {
                        'author_id': self.env['res.partner'],
                        'email_from': self.test_emails[0],
                        # coming from incoming email
                        'incoming_email_cc': email_cc,
                        'incoming_email_to': email_to,
                        'mail_server_id': self.env['ir.mail_server'],
                        'parent_id': self.env['mail.message'],
                        'notified_partner_ids': self.env['res.partner'],
                        # only recognized partners
                        'partner_ids': self.partner_employee + self.customer_portal_zboing,
                        'subject': 'Inquiry',
                        # subtype from '_creation_subtype'
                        'subtype_id': self.env.ref('test_mail.st_mail_test_ticket_partner_new'),
                    },
                    'notif': [],  # no notif, mailgateway sets recipients without notification
                },
            ],
        )

        # second message: acknowledgement
        acknowledgement = ticket.message_ids[1]
        self.assertMailNotifications(
            acknowledgement,
            [
                {
                    'content': f'Received {ticket.name}',
                    'message_type': 'auto_comment',
                    'message_values': {
                        # defined by template, root is the cron user as no responsible
                        'author_id': self.partner_root,
                        'email_from': self.partner_root.email_formatted,
                        'incoming_email_cc': False,
                        'incoming_email_to': False,
                        'mail_server_id': self.env['ir.mail_server'],
                        # no followers, hence only template default_to
                        'notified_partner_ids': partner_sylvie,
                        'parent_id': incoming_email,
                        # no followers, hence only template default_to
                        'partner_ids': partner_sylvie,
                        'subject': f'Received {ticket.name}',
                        # subtype from '_track_template'
                        'subtype_id': self.env.ref('mail.mt_note'),
                    },
                    'notif': [
                        {'partner': partner_sylvie, 'type': 'email',},
                    ],
                },
            ],
        )
