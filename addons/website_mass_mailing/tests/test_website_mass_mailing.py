from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.addons.website_mass_mailing.tests.common import WebsiteMassMailingMultiCompanyCommon
from odoo.tests.common import HttpCase, tagged, users


@tagged('mass_mailing')
class TestWebsiteMassMailing(WebsiteMassMailingMultiCompanyCommon, MassMailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_contact_a, cls.test_contact_b = cls.env['res.partner'].create([
            {
                'name': 'Test Recipient A',
                'email': 'test.recipient.a@example.com',
                'company_id': cls.company_admin.id,
            },
            {
                'name': 'Test Recipient B',
                'email': 'test.recipient.b@example.com',
                'company_id': cls.company_2.id,
            },
        ])

    @users('user_marketing')
    def test_mailing_unsubscribe_url_multi_company_partner(self):
        """ Each recipient's links must use the host of the website resolved
        from its own company, regardless of web.base.url: the unsubscribe, view
        and tracking URLs all stay on the recipient's website. """
        test_mailing = self.env['mailing.mailing'].create({
            'body_html': """
<p>Hello <t t-out="object.name"/>
    <a href="/unsubscribe_from_list">UNSUBSCRIBE</a>
    <a href="/view">VIEW</a>
</p>""",
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
            'mailing_domain': [('id', 'in', (self.test_contact_a + self.test_contact_b).ids)],
            'mailing_type': 'mail',
            'name': 'TestMailing',
            'subject': 'Test for {{ object.name }}',
        })

        with self.mock_mail_gateway(mail_unlink_sent=False):
            test_mailing.action_send_mail()

        for contact, expected_base_url, unexpected_base_url in (
            (self.test_contact_a, 'http://website-a.test', 'http://website-b.test'),
            (self.test_contact_b, 'http://website-b.test', 'http://website-a.test'),
        ):
            # rendered body, before the placeholder links are substituted
            new_mail = self._find_mail_mail_wrecord(contact)
            self.assertIn(f'{expected_base_url}/unsubscribe_from_list', new_mail.body)
            self.assertIn(f'{expected_base_url}/view', new_mail.body)

            # outgoing email, after substitution
            email = self._find_sent_email_wemail(contact.email_formatted)
            self.assertNotIn('/unsubscribe_from_list', email['body'])
            self.assertNotIn(unexpected_base_url, email['body'])
            self.assertIn(f'{expected_base_url}/mailing/{test_mailing.id}/confirm_unsubscribe', email['body'])
            self.assertIn(f'{expected_base_url}/mailing/{test_mailing.id}/view?', email['body'])
            self.assertIn(f'{expected_base_url}/mail/track/', email['body'])
            self.assertIn(
                f'{expected_base_url}/mailing/{test_mailing.id}/unsubscribe_oneclick',
                email['headers']['List-Unsubscribe'],
            )


@tagged('mass_mailing', 'post_install', '-at_install')
class TestWebsiteMassMailingControllers(WebsiteMassMailingMultiCompanyCommon, MassMailCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_contact_b = cls.env['res.partner'].create({
            'name': 'Test Recipient B',
            'email': 'test.recipient.b@example.com',
            'company_id': cls.company_2.id,
        })
        cls.test_mailing = cls.env['mailing.mailing'].create({
            'body_html': '<p>Hello <t t-out="object.name"/><a href="/unsubscribe_from_list">UNSUBSCRIBE</a></p>',
            'mailing_model_id': cls.env['ir.model']._get('res.partner').id,
            'mailing_type': 'mail',
            'name': 'TestMailing',
            'subject': 'Test',
        })

    def test_mailing_view_public_token_uses_recipient_website(self):
        """ A public recipient opening /view with a valid token gets a working
        page whose unsubscribe link stays on their own website (company_2 ->
        website B), even though web.base.url points at website A. """
        contact = self.test_contact_b
        hash_token = self.test_mailing._generate_mailing_recipient_token(contact.id, contact.email_normalized)
        res = self.url_open(
            f'/mailing/{self.test_mailing.id}/view'
            f'?email={contact.email_normalized}&document_id={contact.id}&hash_token={hash_token}'
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn(
            f'http://website-b.test/mailing/{self.test_mailing.id}/confirm_unsubscribe',
            res.text,
        )
