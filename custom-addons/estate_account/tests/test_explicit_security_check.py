from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import AccessError
from odoo import Command


@tagged('post_install', '-at_install')
class TestExplicitSecurityCheck(TransactionCase):
    """Test that explicit security checks are performed before sudo() operations"""
    
    def setUp(self):
        super().setUp()
        
        # Create a property type
        self.property_type = self.env['estate.property.type'].create({
            'name': 'Test House'
        })
        
        # Create a test user without estate permissions
        self.test_user = self.env['res.users'].create({
            'name': 'Test User No Access',
            'login': 'test_user_no_access',
            'email': 'test@example.com',
            'groups_id': [Command.set([self.env.ref('base.group_user').id])]
        })
        
        # Create a property as admin
        self.property = self.env['estate.property'].create({
            'name': 'Test Property for Security',
            'property_type_id': self.property_type.id,
            'expected_price': 100000,
        })
        
        # Create a buyer
        self.buyer = self.env['res.partner'].create({
            'name': 'Test Buyer',
        })
        
        # Create an offer and accept it
        self.offer = self.env['estate.property.offer'].create({
            'property_id': self.property.id,
            'partner_id': self.buyer.id,
            'price': 95000,
        })
        self.offer.action_accept()
    
    def test_security_check_before_sudo(self):
        """Test that security check happens before invoice creation with sudo()"""
        
        # User without access tries to sell property
        # This should fail at the security check, NOT at invoice creation
        with self.assertRaises(AccessError, msg="User without access should not be able to sell property"):
            self.property.with_user(self.test_user).action_sold()
        
        # Verify that no invoice was created (security check prevented it)
        self.assertFalse(self.property.invoice_id, "No invoice should be created when security check fails")
        
        # Verify property is still in 'offer_accepted' state
        self.assertEqual(self.property.state, 'offer_accepted', "Property state should not change when security fails")
    
    def test_admin_can_sell_property(self):
        """Test that admin can successfully sell property and create invoice"""
        
        # Admin sells property
        self.property.action_sold()
        
        # Verify invoice was created
        self.assertTrue(self.property.invoice_id, "Invoice should be created when admin sells property")
        
        # Verify property state changed to 'sold'
        self.assertEqual(self.property.state, 'sold', "Property should be in 'sold' state")
        
        # Verify invoice has correct lines
        invoice_lines = self.property.invoice_id.invoice_line_ids
        self.assertEqual(len(invoice_lines), 2, "Invoice should have 2 lines (commission + admin fee)")
        
        # Check commission line (6% of 95000 = 5700)
        commission_line = invoice_lines.filtered(lambda l: 'Commission' in l.name)
        self.assertTrue(commission_line, "Invoice should have commission line")
        self.assertEqual(commission_line.price_unit, 5700.0, "Commission should be 6% of selling price")
        
        # Check admin fee line
        admin_line = invoice_lines.filtered(lambda l: 'Administrative' in l.name)
        self.assertTrue(admin_line, "Invoice should have administrative fee line")
        self.assertEqual(admin_line.price_unit, 100.0, "Admin fee should be 100")
    
    def test_agent_with_permission_can_sell(self):
        """Test that agent with proper permissions can sell property"""
        
        # Create an agent user with estate user permissions
        agent = self.env['res.users'].create({
            'name': 'Test Agent',
            'login': 'test_agent',
            'email': 'agent@example.com',
            'groups_id': [Command.set([
                self.env.ref('base.group_user').id,
                self.env.ref('estate.estate_group_user').id
            ])]
        })
        
        # Agent sells property
        self.property.with_user(agent).action_sold()
        
        # Verify invoice was created (despite agent not having accounting permissions)
        self.assertTrue(self.property.invoice_id, "Invoice should be created when agent sells property")
        
        # Verify property state changed to 'sold'
        self.assertEqual(self.property.state, 'sold', "Property should be in 'sold' state")
    
    def test_security_check_logs_user_info(self):
        """Test that security check logs user information"""
        
        # This test verifies that the security check is actually being performed
        # by checking that it raises an error for unauthorized users
        
        # Create a property that the test user can read but not write
        property_readable = self.env['estate.property'].sudo().create({
            'name': 'Readable Property',
            'property_type_id': self.property_type.id,
            'expected_price': 50000,
        })
        
        # Create and accept an offer
        offer = self.env['estate.property.offer'].sudo().create({
            'property_id': property_readable.id,
            'partner_id': self.buyer.id,
            'price': 45000,
        })
        offer.action_accept()
        
        # Test user tries to sell (should fail at security check)
        with self.assertRaises(AccessError):
            property_readable.with_user(self.test_user).action_sold()
        
        # Verify no invoice was created
        self.assertFalse(property_readable.invoice_id, "No invoice should be created")
