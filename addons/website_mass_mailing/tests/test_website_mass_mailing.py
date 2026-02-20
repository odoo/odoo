# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests.common import tagged


@tagged("mass_mailing")
class TestWebsiteMassMailing(MassMailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_mailing_unsubscribe_contact(self):
        """ Check unsubscribe url for mailings with contacts recipient model in a multi-website multi-company scenario """

        company2 = self.env['res.company'].sudo().create({'name': 'Test Company 2'})
        self.env['website'].sudo().create({'name': 'My Website 1', 'company_id': self.env.user.company_id.id, 'domain': 'website1.com'})
        self.env['website'].sudo().create({'name': 'My Website 2', 'company_id': company2.id, 'domain': 'website2.com'})
        contact = self.env['res.partner'].sudo().create({'name': 'Test Abigail', 'email': 'test_mailing_unsubscribe_contact@example.com', 'company_id': company2.id})
        test_mailing = self.env['mailing.mailing'].with_user(self.env.user).create({
            "body_html": """
<p>Hello <t t-out="object.name"/>
    <a href="/unsubscribe_from_list">UNSUBSCRIBE</a>
    <a href="/view">VIEW</a>
</p>""",
            'contact_list_ids': [],
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
            'mailing_domain': [('email', 'ilike', 'test_mailing_unsubscribe_contact@example.com')],
            "mailing_type": "mail",
            "name": "TestMailing",
            "subject": "Test for {{ object.name }}",
        })

        with self.mock_mail_gateway(mail_unlink_sent=False):
            test_mailing.action_send_mail()

        new_mail = self._find_mail_mail_wrecord(contact)
        # check the unsubscribe link is present
        self.assertIn("/unsubscribe_from_list", new_mail.body)
        self.assertIn("/view", new_mail.body)

        email = self._find_sent_mail_wemail(contact.email_formatted)
        self.assertNotIn("/unsubscribe_from_list", email["body"])
        self.assertIn("/confirm_unsubscribe", email["body"])
