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

        # ensure employee can create partners, necessary for templates
        cls.user_employee.write({
            'groups_id': [(4, cls.env.ref('base.group_partner_manager').id)],
        })

        cls.user_employee_2 = mail_new_test_user(
            cls.env,
            email='eglantine@example.com',
            groups='base.group_user',
            login='employee2',
            name='Eglantine Employee',
            notification_type='email',
            signature='--\nEglantine',
        )
        cls.partner_employee_2 = cls.user_employee_2.partner_id

        cls.mail_test_lead_model = cls.env['ir.model']._get('mail.test.lead')
        cls.email_from = '"Sylvie Lelitre" <sylvie.lelitre@agrolait.example.com>'

        # lead@test.mycompany.com will cause the creation of new mail.test.lead
        cls.alias = cls.env['mail.alias'].create({
            'alias_domain_id': cls.mail_alias_domain.id,
            'alias_contact': 'everyone',
            'alias_model_id': cls.mail_test_lead_model.id,
            'alias_name': 'lead',
        })

    def test_lead_mailgateway(self):
        emails_cc = [
            '"Josiane" <accounting@agrolait.example.com>',
            'pay@agrolait.example.com',
        ]

        # incoming customer email through mailgateway
        with self.mock_mail_gateway(), self.mock_mail_app():
            lead = self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f'lead@{self.alias_domain}',
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
        message = lead.message_ids
        self.assertEqual(self._new_msgs, message)
        self.assertIn('Please call me as soon as possible', message.body)
        self.assertEqual(message.email_cc, ','.join(emails_cc),
                         'mail: not that message email_cc is reformated, no spaces')
        self.assertEqual(message.email_from, self.email_from)
        self.assertEqual(message.email_to, f'lead@{self.alias_domain}')
        self.assertFalse(message.partner_ids)

        # user is assigned
        # - should notify him
        with self.mock_mail_gateway(), self.mock_mail_app():
            lead.write({'user_id': self.user_employee.id})
        self.assertFalse(lead.message_partner_ids)
