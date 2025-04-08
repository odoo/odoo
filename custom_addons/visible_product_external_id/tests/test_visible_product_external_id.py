from odoo.tests.common import TransactionCase
from odoo.tests import Form
from odoo.tools import mute_logger


class TestVisibleProductExternalId(TransactionCase):
    """Tests for the visible_product_external_id module."""

    @classmethod
    def setUpClass(cls):
        """Set up test data."""
        super().setUpClass()
        cls.product_template = cls.env['product.template'].create({
            'name': 'Test Product Template',
            'default_code': 'TPT-001',
        })
        
        cls.product_variant = cls.env['product.product'].create({
            'name': 'Test Product Variant',
            'default_code': 'TPV-001',
        })
        
        cls.env['ir.model.data'].create({
            'name': 'test_product_template',
            'module': 'visible_product_external_id',
            'model': 'product.template',
            'res_id': cls.product_template.id,
        })
        
        cls.env['ir.model.data'].create({
            'name': 'test_product_variant',
            'module': 'visible_product_external_id',
            'model': 'product.product',
            'res_id': cls.product_variant.id,
        })
        
        cls.env['ir.model.data'].create({
            'name': 'test_product_template_alt',
            'module': 'visible_product_external_id',
            'model': 'product.template',
            'res_id': cls.product_template.id,
        })

        cls.product_without_id = cls.env['product.template'].create({
            'name': 'Product Without External ID',
            'default_code': 'PWI-001',
        })

    def test_product_template_external_id(self):
        """Test that external IDs are correctly computed for product templates."""
        self.product_template.env.cache.invalidate()
        
        expected_ids = "test_product_template, test_product_template_alt"
        actual_ids = ", ".join(sorted(self.product_template.external_id.split(", ")))
        
        self.assertEqual(
            actual_ids, 
            expected_ids,
            "External IDs should be correctly computed for product templates"
        )

    def test_product_variant_external_id(self):
        """Test that external IDs are correctly computed for product variants."""
        self.product_variant.env.cache.invalidate()
        
        self.assertEqual(
            self.product_variant.external_id,
            "test_product_variant",
            "External IDs should be correctly computed for product variants"
        )
        
    def test_no_external_id(self):
        """Test that products without external IDs return False."""
        self.assertFalse(
            self.product_without_id.external_id,
            "Products without external IDs should have external_id field set to False"
        )
    
    def test_product_template_form_view(self):
        """Test that the product template form view loads correctly and contains the external_id field."""
        with Form(self.product_template) as form:
            self.assertIn("external_id", form._values)
            expected_ids = "test_product_template, test_product_template_alt"
            actual_ids = ", ".join(sorted(form._values["external_id"].split(", ")))
            self.assertEqual(actual_ids, expected_ids)

    def test_product_variant_form_view(self):
        """Test that the product variant form view loads correctly and contains the external_id field."""
        with Form(self.product_variant) as form:
            self.assertIn("external_id", form._values)
            self.assertEqual(form._values["external_id"], "test_product_variant")
        
    def test_search_by_external_id(self):
        """Test searching by external ID substring."""
        products = self.env['product.template'].search([
            ('external_id', 'ilike', 'test_product_template')
        ])
        self.assertEqual(len(products), 1)
        self.assertEqual(products, self.product_template)
        
        variants = self.env['product.product'].search([
            ('external_id', 'ilike', 'test_product_variant')
        ])
        self.assertEqual(len(variants), 1)
        self.assertEqual(variants, self.product_variant)
        
    def test_search_no_results(self):
        """Test searching with no results."""
        products = self.env['product.template'].search([
            ('external_id', 'ilike', 'non_existent_id')
        ])
        self.assertEqual(len(products), 0)
        
    def test_search_empty_value(self):
        """Test searching with empty value."""
        products = self.env['product.template'].search([
            ('external_id', 'ilike', '')
        ])
        self.assertEqual(len(products), 0)
        
        products = self.env['product.template'].search([
            ('external_id', '=', False)
        ])
        self.assertEqual(len(products), 0)