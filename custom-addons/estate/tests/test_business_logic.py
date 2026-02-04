from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo import Command


@tagged('post_install', '-at_install')
class EstateBusinessLogicTestCase(TransactionCase):
    """Test business logic for estate properties and offers"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create property type
        cls.property_type = cls.env['estate.property.type'].create({
            'name': 'Test House'
        })
        
        # Create partners for offers
        cls.partner_1 = cls.env['res.partner'].create({
            'name': 'Test Partner 1'
        })
        
        cls.partner_2 = cls.env['res.partner'].create({
            'name': 'Test Partner 2'
        })
        
        # Create test properties
        cls.property_with_offer = cls.env['estate.property'].create({
            'name': 'Property with Offer',
            'property_type_id': cls.property_type.id,
            'expected_price': 100000,
        })
        
        cls.property_without_offer = cls.env['estate.property'].create({
            'name': 'Property without Offer',
            'property_type_id': cls.property_type.id,
            'expected_price': 150000,
        })
        
        cls.property_sold = cls.env['estate.property'].create({
            'name': 'Sold Property',
            'property_type_id': cls.property_type.id,
            'expected_price': 200000,
            'state': 'new',  # Will be sold in test
        })
        
        # Create and accept an offer for property_with_offer
        cls.offer_1 = cls.env['estate.property.offer'].create({
            'property_id': cls.property_with_offer.id,
            'partner_id': cls.partner_1.id,
            'price': 95000,
        })
        cls.offer_1.action_accept()
    
    def test_cannot_create_offer_for_sold_property(self):
        """Test that creating an offer for a sold property raises an error"""
        
        # First, sell the property
        # Create and accept an offer
        offer = self.env['estate.property.offer'].create({
            'property_id': self.property_sold.id,
            'partner_id': self.partner_1.id,
            'price': 190000,
        })
        offer.action_accept()
        
        # Mark property as sold
        self.property_sold.action_sold()
        self.assertEqual(self.property_sold.state, 'sold')
        
        # Try to create another offer for the sold property
        with self.assertRaises(UserError) as cm:
            self.env['estate.property.offer'].create({
                'property_id': self.property_sold.id,
                'partner_id': self.partner_2.id,
                'price': 200000,
            })
        
        # Verify error message
        self.assertIn('sold property', str(cm.exception))
    
    def test_cannot_sell_property_without_accepted_offer(self):
        """Test that selling a property without accepted offers raises an error"""
        
        # Property has no offers at all
        self.assertEqual(len(self.property_without_offer.offer_ids), 0)
        
        # Try to sell property without offers
        with self.assertRaises(UserError) as cm:
            self.property_without_offer.action_sold()
        
        # Verify error message
        self.assertIn('accepted offer', str(cm.exception))
        
        # Verify property is not sold
        self.assertNotEqual(self.property_without_offer.state, 'sold')
    
    def test_cannot_sell_property_with_only_refused_offers(self):
        """Test that selling a property with only refused offers raises an error"""
        
        # Create property with refused offer
        property_refused = self.env['estate.property'].create({
            'name': 'Property with Refused Offer',
            'property_type_id': self.property_type.id,
            'expected_price': 120000,
        })
        
        # Create and refuse an offer
        offer = self.env['estate.property.offer'].create({
            'property_id': property_refused.id,
            'partner_id': self.partner_1.id,
            'price': 110000,
        })
        offer.action_refuse()
        
        # Try to sell property with only refused offers
        with self.assertRaises(UserError) as cm:
            property_refused.action_sold()
        
        # Verify error message
        self.assertIn('accepted offer', str(cm.exception))
        
        # Verify property is not sold
        self.assertNotEqual(property_refused.state, 'sold')
    
    def test_can_sell_property_with_accepted_offer(self):
        """Test that selling a property with an accepted offer works correctly"""
        
        # Property has an accepted offer (created in setUpClass)
        self.assertEqual(len(self.property_with_offer.offer_ids), 1)
        self.assertEqual(self.property_with_offer.offer_ids[0].status, 'accepted')
        
        # Initial state should not be sold
        self.assertNotEqual(self.property_with_offer.state, 'sold')
        
        # Sell the property
        self.property_with_offer.action_sold()
        
        # Verify property is marked as sold
        self.assertEqual(self.property_with_offer.state, 'sold')
    
    def test_selling_property_sets_correct_state(self):
        """Test that selling a property correctly updates its state"""
        
        # Create property with accepted offer
        property_test = self.env['estate.property'].create({
            'name': 'Test Property State',
            'property_type_id': self.property_type.id,
            'expected_price': 130000,
        })
        
        # Create and accept offer
        offer = self.env['estate.property.offer'].create({
            'property_id': property_test.id,
            'partner_id': self.partner_1.id,
            'price': 125000,
        })
        offer.action_accept()
        
        # Verify initial state
        self.assertIn(property_test.state, ['new', 'offer_received', 'offer_accepted'])
        
        # Sell property
        property_test.action_sold()
        
        # Verify final state
        self.assertRecordValues(property_test, [{
            'name': 'Test Property State',
            'state': 'sold',
        }])
    
    def test_multiple_offers_one_accepted(self):
        """Test that property can be sold with multiple offers if at least one is accepted"""
        
        # Create property
        property_multi = self.env['estate.property'].create({
            'name': 'Property Multiple Offers',
            'property_type_id': self.property_type.id,
            'expected_price': 140000,
        })
        
        # Create multiple offers
        offer_1 = self.env['estate.property.offer'].create({
            'property_id': property_multi.id,
            'partner_id': self.partner_1.id,
            'price': 130000,
        })
        
        offer_2 = self.env['estate.property.offer'].create({
            'property_id': property_multi.id,
            'partner_id': self.partner_2.id,
            'price': 135000,
        })
        
        # Refuse first, accept second
        offer_1.action_refuse()
        offer_2.action_accept()
        
        # Should be able to sell
        property_multi.action_sold()
        
        # Verify property is sold
        self.assertEqual(property_multi.state, 'sold')
    
    def test_cannot_sell_cancelled_property(self):
        """Test that cancelled properties cannot be sold"""
        
        # Create property and cancel it
        property_cancelled = self.env['estate.property'].create({
            'name': 'Cancelled Property',
            'property_type_id': self.property_type.id,
            'expected_price': 160000,
        })
        
        property_cancelled.action_cancel()
        self.assertEqual(property_cancelled.state, 'cancelled')
        
        # Try to sell cancelled property
        with self.assertRaises(UserError) as cm:
            property_cancelled.action_sold()
        
        # Verify error message
        self.assertIn('Cancelled', str(cm.exception))
        
        # Verify property is still cancelled
        self.assertEqual(property_cancelled.state, 'cancelled')