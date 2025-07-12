from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestResPartnerValidation(TransactionCase):
    """Validate contact fields (phone, email, website) formatting."""

    def test_valid_contact_fields(self):
        Partner = self.env['res.partner']
        valid = Partner.create({
            'name': 'Valid Partner',
            'phone': '+1234567890',
            'mobile': '123-456-7890',
            'email': 'test@example.com',
            'website': 'https://valid.com',
        })
        self.assertTrue(valid.id > 0)

    def test_invalid_phone(self):
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': 'Invalid Phone',
                'phone': 'abc'
            })

    def test_invalid_email(self):
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': 'Invalid Email',
                'email': 'invalid@'
            })

    def test_website_invalid_URL(self):
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': 'Invalid Website URL',
                'website': 'http://localhost' 
            })
