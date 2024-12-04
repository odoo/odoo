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

        cls.mail_test_lead_model = cls.env['ir.model']._get('mail.test.lead')
        cls.email_from = '"Sylvie Lelitre" <sylvie.lelitre@zboing.example.com>'

        # lead@test.mycompany.com will cause the creation of new mail.test.lead
        cls.alias = cls.env['mail.alias'].create({
            'alias_domain_id': cls.mail_alias_domain.id,
            'alias_contact': 'everyone',
            'alias_model_id': cls.mail_test_lead_model.id,
            'alias_name': 'lead',
        })

    def test_lead_mailgateway(self):
        emails_to = [
            self.partner_employee_2.email_formatted,
            '"Josiane Quichopoils" <accounting@zboing.example.com>',
        ]
        emails_cc = [
            'pay@zboing.example.com',
        ]

        # incoming customer email through mailgateway
        # ------------------------------------------------------------
        with self.mock_mail_gateway(), self.mock_mail_app():
            lead = self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f'lead@{self.alias_domain}, {emails_to[0]}, {emails_to[1]}',
                cc=', '.join(emails_cc),
                subject='Inquiry',
                target_model='mail.test.lead',
            )
        self.assertEqual(lead.email_cc, ', '.join(emails_cc))
        self.assertEqual(lead.email_from, self.email_from)
        self.assertEqual(lead.name, 'Inquiry')
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
                        'email_cc': ', '.join(emails_cc),
                        'email_from': self.email_from,
                        'email_to': f'lead@{self.alias_domain}, {emails_to[0]}, {emails_to[1]}',
                        'partner_ids': self.partner_employee_2,
                    },
                    'notif': [],  # no notif, mailgateway sets recipients without notification
                },
            ],
        )

        # user is assigned, should notify him
        with self.mock_mail_gateway(), self.mock_mail_app():
            lead.write({'user_id': self.user_employee_2.id})
        lead_as_emp2 = lead.with_user(self.user_employee_2.id)
        self.assertEqual(lead_as_emp2.message_partner_ids, self.partner_employee_2)
        # adds other employee as follower
        lead_as_emp2.message_subscribe(partner_ids=self.partner_employee.ids)
        self.assertEqual(lead_as_emp2.message_partner_ids, self.partner_employee_2 + self.partner_employee)

        # uses Chatter: fetches suggested recipients, post a message
        # ------------------------------------------------------------
        suggested_all = lead_as_emp2._message_get_suggested_recipients(reply_discussion=True, no_create=False)
        partner_sylvie = self.env['res.partner'].search(
            [('email_normalized', '=', 'sylvie.lelitre@zboing.example.com')]
        )
        partner_pay = self.env['res.partner'].search(
            [('email_normalized', '=', 'pay@zboing.example.com')]
        )
        partner_accounting = self.env['res.partner'].search(
            [('email_normalized', '=', 'accounting@zboing.example.com')]
        )
        expected_all = [
            {  # primary email comes first
                'create_values': {},
                'email': 'sylvie.lelitre@zboing.example.com',
                'name': 'Sylvie Lelitre',
                'partner_id': partner_sylvie.id,
            },
            {  # mail.thread.cc: email_cc field
                'create_values': {},
                'email': 'pay@zboing.example.com',
                'name': 'pay@zboing.example.com',
                'partner_id': partner_pay.id,
            },
            {  # reply message
                'create_values': {},
                'email': 'accounting@zboing.example.com',
                'name': 'Josiane Quichopoils',
                'partner_id': partner_accounting.id,
            },
        ]
        for suggested, expected in zip(suggested_all, expected_all):
            self.assertDictEqual(suggested, expected)
        with self.mock_mail_gateway():
            message = lead_as_emp2.message_post(
                body='<p>Well received !',
                partner_ids=(partner_sylvie + partner_pay + partner_accounting).ids,
                message_type='comment',
                subtype_id=self.env.ref('mail.mt_comment').id,
            )
        self.assertMailNotifications(
            message,
            [
                {
                    'content': 'Well received !',
                    'email_values': {'email_from': 'pipi'},
                    'message_type': 'comment',
                    'message_values': {
                        'email_cc': False,
                        'email_from': self.partner_employee_2.email_formatted,
                        'email_to': False,
                        'partner_ids': partner_sylvie + partner_pay + partner_accounting,
                    },
                    'notif': [
                        {'partner': self.partner_employee, 'type': 'inbox'},
                        {'partner': partner_sylvie, 'type': 'email'},
                        {'partner': partner_pay, 'type': 'email'},
                        {'partner': partner_accounting, 'type': 'email'},
                    ],
                },
            ],
        )
