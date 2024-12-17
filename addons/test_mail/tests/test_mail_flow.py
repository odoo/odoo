from odoo import tools
from odoo.addons.mail.tests.common import mail_new_test_user, MailCommon
from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE
from odoo.addons.test_mail.tests.common import TestRecipients
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
            '"Sylvie Lelitre" <sylvie.lelitre@zboing.com>',
            '"Josiane Quichopoils" <accounting@zboing.com>',
            'pay@zboing.com',
            '"Portal Zboing" <portal@zboing.com>',
        ]
        cls.test_emails_normalized = ['sylvie.lelitre@zboing.com', 'accounting@zboing.com', 'pay@zboing.com', 'portal@zboing.com']
        cls.customer_portal_zboing = cls.env['res.partner'].create({
            'email': cls.test_emails[3],
            'name': "Portal Zboing",
            'phone': '+32455001122',
        })

        # lead@test.mycompany.com will cause the creation of new mail.test.lead
        cls.mail_test_lead_model = cls.env['ir.model']._get('mail.test.lead')
        cls.alias = cls.env['mail.alias'].create({
            'alias_domain_id': cls.mail_alias_domain.id,
            'alias_contact': 'everyone',
            'alias_model_id': cls.mail_test_lead_model.id,
            'alias_name': 'lead',
        })

    def test_assert_initial_values(self):
        """ Assert base values for tests """
        self.assertEqual(
            self.env['res.partner'].search([('email_normalized', 'in', self.test_emails_normalized)]),
            self.customer_portal_zboing,
        )

    def test_lead_mailgateway(self):
        """ Flow and checks in this test

        * incoming email creating a lead -> email set as first message
        * a salesperson is assigned
        * he adds followers (internal and portal)
        """
        # incoming customer email through mailgateway
        # ------------------------------------------------------------
        email_to = f'lead@{self.alias_domain}, {self.test_emails[1]}, {self.partner_employee.email_formatted}'
        email_cc = f'{self.test_emails[2]}, {self.test_emails[3]}'
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
        self.assertMailNotifications(
            lead.message_ids,
            [
                {
                    'content': 'Please call me as soon as possible',
                    'message_type': 'email',
                    'message_values': {
                        'email_cc': email_cc,
                        'email_from': self.test_emails[0],
                        'email_to': email_to,
                        'mail_server_id': self.env['ir.mail_server'],
                        'partner_ids': self.partner_employee + self.customer_portal_zboing,
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

        # uses Chatter: fetches suggested recipients, post a message
        # - checks all suggested: incoming email to + cc are included
        # - for all notified people: expected 'email_to' is them + external
        #   email addresses -> including portal customers
        # ------------------------------------------------------------
        suggested_all = lead_as_emp._message_get_suggested_recipients(reply_discussion=True, no_create=False)
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
                'name': 'Sylvie Lelitre',
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
        with self.mock_mail_gateway():
            message = lead_as_emp.message_post(
                body='<p>Well received !',
                partner_ids=(partner_sylvie + partner_pay + partner_accounting + self.customer_portal_zboing).ids,
                message_type='comment',
                subtype_id=self.env.ref('mail.mt_comment').id,
            )
        self.assertMailNotifications(
            message,
            [
                {
                    'content': 'Well received !',
                    'mail_mail_values': {
                        'mail_server_id': self.env['ir.mail_server'],  # no specified server
                    },
                    'message_type': 'comment',
                    'message_values': {
                        'email_cc': False,
                        'email_from': self.partner_employee.email_formatted,
                        'email_to': False,
                        'mail_server_id': self.env['ir.mail_server'],
                        'notified_partner_ids': (
                            partner_sylvie + partner_pay + partner_accounting + self.customer_portal_zboing +
                            self.partner_employee_2 + self.partner_portal
                        ),
                        'partner_ids': partner_sylvie + partner_pay + partner_accounting + self.customer_portal_zboing,
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
        # expected Msg['To'] : actual recipient + all "not internal partners" + catchall (to receive answers)
        external_partners = partner_sylvie + partner_pay + partner_accounting + self.customer_portal_zboing + self.partner_portal
        for partner in message.notified_partner_ids:
            exp_msg_to_partners = partner | external_partners
            exp_msg_to = exp_msg_to_partners.mapped('email_formatted')
            with self.subTest(name=partner.name):
                self.assertSMTPEmailsSent(
                    mail_server=self.mail_server_notification,
                    # msg_from=tools.mail.formataddr((self.partner_employee.name, f'{self.default_from}@{self.alias_domain}')),  # to check
                    msg_from=f'{self.partner_employee.name} <{self.default_from}@{self.alias_domain}>',  # to check
                    smtp_from=self.mail_server_notification.from_filter,
                    smtp_to_list=[partner.email_normalized],
                    msg_to_lst=exp_msg_to,
                )
