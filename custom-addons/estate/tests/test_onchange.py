from odoo.tests.common import TransactionCase
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class EstateOnchangeTestCase(TransactionCase):
    """Test onchange methods for estate properties"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create property type for tests
        cls.property_type = cls.env['estate.property.type'].create({
            'name': 'Test House'
        })
    
    def test_garden_onchange_sets_values_when_checked(self):
        """Test that checking Garden checkbox sets default values for garden_area and garden_orientation"""
        
        # Create a Form to trigger onchange
        with Form(self.env['estate.property']) as property_form:
            property_form.name = 'Test Property with Garden'
            property_form.property_type_id = self.property_type
            property_form.expected_price = 100000
            
            # Initially garden is False
            self.assertFalse(property_form.garden)
            
            # Check the garden checkbox
            property_form.garden = True
            
            # Verify that onchange set the default values
            self.assertEqual(property_form.garden_area, 10)
            self.assertEqual(property_form.garden_orientation, 'north')
    
    def test_garden_onchange_resets_values_when_unchecked(self):
        """Test that unchecking Garden checkbox resets garden_area and garden_orientation
        
        This test ensures that the garden fields are properly reset when the garden
        checkbox is unchecked. This prevents data inconsistency where a property
        without a garden still has garden area and orientation values.
        
        Bug scenario: Someone might modify the onchange method and forget to reset
        the values when garden is unchecked. This test catches that regression.
        """
        
        # Create a Form to trigger onchange
        with Form(self.env['estate.property']) as property_form:
            property_form.name = 'Test Property Garden Reset'
            property_form.property_type_id = self.property_type
            property_form.expected_price = 150000
            
            # First, enable garden and set values
            property_form.garden = True
            self.assertEqual(property_form.garden_area, 10)
            self.assertEqual(property_form.garden_orientation, 'north')
            
            # Manually change garden values
            property_form.garden_area = 50
            property_form.garden_orientation = 'south'
            
            # Now uncheck the garden checkbox
            property_form.garden = False
            
            # Verify that onchange reset the values
            self.assertEqual(property_form.garden_area, 0, 
                           "Garden area should be reset to 0 when garden is unchecked")
            self.assertFalse(property_form.garden_orientation,
                           "Garden orientation should be reset to False when garden is unchecked")
    
    def test_garden_onchange_with_custom_values(self):
        """Test that custom garden values are preserved when garden remains checked"""
        
        # Create a Form to trigger onchange
        with Form(self.env['estate.property']) as property_form:
            property_form.name = 'Test Property Custom Garden'
            property_form.property_type_id = self.property_type
            property_form.expected_price = 120000
            
            # Enable garden
            property_form.garden = True
            
            # Set custom values
            property_form.garden_area = 100
            property_form.garden_orientation = 'east'
            
            # Verify custom values are set
            self.assertEqual(property_form.garden_area, 100)
            self.assertEqual(property_form.garden_orientation, 'east')
            
            # Save the property
            property = property_form.save()
            
            # Verify values persisted
            self.assertEqual(property.garden_area, 100)
            self.assertEqual(property.garden_orientation, 'east')
    
    def test_garden_onchange_multiple_toggles(self):
        """Test that toggling garden checkbox multiple times works correctly"""
        
        # Create a Form to trigger onchange
        with Form(self.env['estate.property']) as property_form:
            property_form.name = 'Test Property Multiple Toggles'
            property_form.property_type_id = self.property_type
            property_form.expected_price = 130000
            
            # Toggle 1: Enable garden
            property_form.garden = True
            self.assertEqual(property_form.garden_area, 10)
            self.assertEqual(property_form.garden_orientation, 'north')
            
            # Toggle 2: Disable garden
            property_form.garden = False
            self.assertEqual(property_form.garden_area, 0)
            self.assertFalse(property_form.garden_orientation)
            
            # Toggle 3: Enable garden again
            property_form.garden = True
            self.assertEqual(property_form.garden_area, 10)
            self.assertEqual(property_form.garden_orientation, 'north')
            
            # Toggle 4: Disable garden again
            property_form.garden = False
            self.assertEqual(property_form.garden_area, 0)
            self.assertFalse(property_form.garden_orientation)
    
    def test_garden_onchange_does_not_affect_other_fields(self):
        """Test that garden onchange does not modify other property fields"""
        
        # Create a Form to trigger onchange
        with Form(self.env['estate.property']) as property_form:
            property_form.name = 'Test Property Other Fields'
            property_form.property_type_id = self.property_type
            property_form.expected_price = 140000
            property_form.living_area = 200
            property_form.bedrooms = 3
            
            # Store original values
            original_name = property_form.name
            original_expected_price = property_form.expected_price
            original_living_area = property_form.living_area
            original_bedrooms = property_form.bedrooms
            
            # Toggle garden
            property_form.garden = True
            
            # Verify other fields unchanged
            self.assertEqual(property_form.name, original_name)
            self.assertEqual(property_form.expected_price, original_expected_price)
            self.assertEqual(property_form.living_area, original_living_area)
            self.assertEqual(property_form.bedrooms, original_bedrooms)
            
            # Toggle garden off
            property_form.garden = False
            
            # Verify other fields still unchanged
            self.assertEqual(property_form.name, original_name)
            self.assertEqual(property_form.expected_price, original_expected_price)
            self.assertEqual(property_form.living_area, original_living_area)
            self.assertEqual(property_form.bedrooms, original_bedrooms)