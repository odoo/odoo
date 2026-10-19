from odoo.tests import tagged, TransactionCase


@tagged('-at_install', 'post_install', 'website_visitor')
class TestWebsiteVisitor(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.lead = cls.env['crm.lead'].create({
            'name': 'Test Lead',
            'phone': '+1 555-555-5556',
        })

        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
            'phone': '+1 555-555-5557',
        })

    def test_sms_composer_on_website_visitor_without_partner(self):
        """Test opening the SMS composer for a visitor without a linked partner."""
        visitor = self.env['website.visitor'].create({
            'access_token': 'f9d28aad05ebee0bca215837b129aa00',
            'lead_ids': [(4, self.lead.id)],
        })

        action = visitor.action_send_sms()

        self.assertEqual(action['res_model'], 'sms.composer')
        self.assertEqual(action['context']['default_res_model'], 'crm.lead')
        self.assertEqual(action['context']['number_field_name'], 'phone')

    def test_sms_composer_on_website_visitor_with_partner(self):
        """Test opening the SMS composer for a visitor with a linked partner."""
        visitor = self.env['website.visitor'].create({
            'partner_id': self.partner.id,
            'access_token': self.partner.id,
            'lead_ids': [(4, self.lead.id)],
        })

        action = visitor.action_send_sms()

        self.assertEqual(action['res_model'], 'sms.composer')
        self.assertEqual(action['context']['default_res_model'], 'res.partner')
        self.assertEqual(action['context']['default_number_field_name'], 'phone')
