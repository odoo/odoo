from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestResPartnerValidation(TransactionCase):
    """Test contact field validation in res.partner"""

    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner']

    def test_valid_contact_fields(self):
        """Test creation with valid contact data"""
        partner = self.Partner.create({
            'name': 'Valid Partner',
            'phone': '+1 (555) 123-4567',  
            'mobile': '555.123.4567',       
            'email': 'valid.email+test@sub.example.com',
            'website': 'https://www.odoo-valid.com/path?query=1'
        })
        self.assertTrue(partner.id > 0)

    def test_phone_validation(self):
        """Test phone/mobile validation scenarios"""
        valid_numbers = [
            '+1234567890',     
            '123 456 7890',    
            '(555)123-4567',   
            '555.123.4567',   
            '1234567890'       
        ]
        
        for number in valid_numbers:
            partner = self.Partner.create({
                'name': f'Test {number}',
                'phone': number
            })
            self.assertTrue(partner.id > 0)

    def test_invalid_phone_format(self):
        """Test invalid phone formats"""
        invalid_numbers = [
            'abc123',          
            '+1 () 123',       
            '123!456',          
            '123 45',           
            '-----'             
        ]
        
        for number in invalid_numbers:
            with self.assertRaises(ValidationError):
                self.Partner.create({
                    'name': f'Invalid {number}',
                    'phone': number
                })

    def test_phone_minimum_digits(self):
        """Test minimum digit requirement"""
        with self.assertRaises(ValidationError):
            self.Partner.create({
                'name': 'Short Number',
                'mobile': '12345'  
            })

    def test_email_validation(self):
        """Test email validation"""
        valid_emails = [
            'simple@example.com',
            'with+tag@example.com',
            'with.dots@sub.example.com'
        ]
        
        for email in valid_emails:
            partner = self.Partner.create({
                'name': f'Test {email}',
                'email': email
            })
            self.assertTrue(partner.id > 0)

        invalid_emails = [
            'missing@dot',
            'invalid@',
            '@missing.local',
            'spaces in@email.com'
        ]
        
        for email in invalid_emails:
            with self.assertRaises(ValidationError):
                self.Partner.create({
                    'name': f'Invalid {email}',
                    'email': email
                })

    def test_invalid_websites(self):
        """Test that invalid websites are rejected"""
        invalid_sites = [
                   
            'javascript:alert(1)', 
            'http://',             
            'example..com',        
            'example.c',           
            'example',             
            'example.com/path with space'  
        ]
        
        for site in invalid_sites:
            with self.assertRaises(ValidationError):
                self.Partner.create({
                    'name': f'Invalid {site}',
                    'website': site
                })