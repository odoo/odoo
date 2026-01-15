from odoo.addons.mail.tests.common import MockEmail
from odoo.addons.payment.tests.common import PaymentCommon
from odoo.tests import tagged, users


@tagged("mail_template", "post_install", "-at_install")
class TestMailing(PaymentCommon, MockEmail):

    @users("admin")
    def test_donation_email(self):
        self.env.company.write({
            'email': 'companybot@company.com',
        })
        tx = self._create_transaction('direct')
        with self.mock_mail_gateway():
            tx._send_donation_email(
                is_internal_notification=True,
                recipient_email=tx.partner_email,
            )
        self.assertMailMailWEmails(
            ['norbert.buyer@example.com'],
            'sent',
            email_values={
                'email_from': self.env.company.email_formatted,
            },
            fields_values={
                'email_from': self.env.company.email_formatted,
            },
        )
