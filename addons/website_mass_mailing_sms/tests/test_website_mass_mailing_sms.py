from odoo.addons.mass_mailing_sms.tests.common import MassSMSCommon
from odoo.addons.website_mass_mailing.tests.common import WebsiteMassMailingMultiCompanyCommon
from odoo.tests.common import tagged, users


@tagged('mass_mailing', 'mass_mailing_sms')
class TestWebsiteMassMailingSMS(WebsiteMassMailingMultiCompanyCommon, MassSMSCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        country_be = cls.env.ref('base.be')
        cls.test_contact_a, cls.test_contact_b = cls.env['res.partner'].create([
            {
                'name': 'Test Recipient A',
                'country_id': country_be.id,
                'phone': '0456000011',
                'company_id': cls.company_admin.id,
            },
            {
                'name': 'Test Recipient B',
                'country_id': country_be.id,
                'phone': '0456000022',
                'company_id': cls.company_2.id,
            },
        ])

    @users('user_marketing')
    def test_mailing_sms_unsubscribe_url_multi_company_partner(self):
        """ The SMS opt-out link must use the host of the website resolved from
        the recipient's own company, regardless of web.base.url. """
        mailing = self.env['mailing.mailing'].create({
            'body_plaintext': 'Hello {{ object.name }}',
            'mailing_domain': [('id', 'in', (self.test_contact_a + self.test_contact_b).ids)],
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
            'mailing_type': 'sms',
            'name': 'TestSMSMailing',
            'sms_allow_unsubscribe': True,
            'sms_force_send': True,
            'subject': 'Test',
        })

        with self.mockSMSGateway():
            mailing.action_send_sms()

        for contact, expected_base_url, unexpected_base_url in (
            (self.test_contact_a, 'http://website-a.test', 'http://website-b.test'),
            (self.test_contact_b, 'http://website-b.test', 'http://website-a.test'),
        ):
            sms_sent = self._find_sms_sent(contact, None)
            self.assertIn(f'{expected_base_url}/sms/{mailing.id}/', sms_sent['body'])
            self.assertNotIn(unexpected_base_url, sms_sent['body'])
