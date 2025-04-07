from odoo.tests.common import TransactionCase
from odoo.tests import Form
from odoo.tools import mute_logger


class TestProductExternalId(TransactionCase):
    """Tests for the product_external_id module."""

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
            'module': 'product_external_id',
            'model': 'product.template',
            'res_id': cls.product_template.id,
        })
        
        cls.env['ir.model.data'].create({
            'name': 'test_product_variant',
            'module': 'product_external_id',
            'model': 'product.product',
            'res_id': cls.product_variant.id,
        })
        
        cls.env['ir.model.data'].create({
            'name': 'test_product_template_alt',
            'module': 'product_external_id',
            'model': 'product.template',
            'res_id': cls.product_template.id,
        })

    def test_product_template_external_id(self):
        """Test that external IDs are correctly computed for product templates."""
        self.product_template.env.cache.invalidate()
        
        expected_ids = "product_external_id.test_product_template, product_external_id.test_product_template_alt"
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
            "product_external_id.test_product_variant",
            "External IDs should be correctly computed for product variants"
        )
        
    def test_no_external_id(self):
        """Test that products without external IDs return False."""
        product_without_id = self.env['product.template'].create({
            'name': 'Product Without External ID',
            'default_code': 'PWI-001',
        })
        
        self.assertFalse(
            product_without_id.external_id,
            "Products without external IDs should have external_id field set to False"
        )
    
    def test_product_template_form_view(self):
        """Test that the product template form view loads correctly and contains the external_id field."""
        with Form(self.product_template) as form:
            self.assertIn("external_id", form._values)
            expected_ids = "product_external_id.test_product_template, product_external_id.test_product_template_alt"
            actual_ids = ", ".join(sorted(form._values["external_id"].split(", ")))
            self.assertEqual(actual_ids, expected_ids)

    def test_product_variant_form_view(self):
        """Test that the product variant form view loads correctly and contains the external_id field."""
        with Form(self.product_variant) as form:
            self.assertIn("external_id", form._values)
            self.assertEqual(form._values["external_id"], "product_external_id.test_product_variant")

    def test_product_template_tree_view(self):
        """Test that the product template tree view contains the external_id field."""
        tree_view = self.env.ref('product.product_template_tree_view')
        inherited_view = self.env.ref('product_external_id.product_template_tree_view_inherit_external_id')
        
        self.assertTrue(inherited_view, "Inherited tree view should exist")
        self.assertEqual(inherited_view.inherit_id, tree_view, 
                         "Inherited view should extend the product template tree view")
        
        self.assertIn('field name="external_id"', inherited_view.arch,
                      "Tree view should contain the external_id field")

    def test_product_template_search_view(self):
        """Test that the product template search view contains the external_id field."""
        search_view = self.env.ref('product.product_template_search_view')
        inherited_view = self.env.ref('product_external_id.product_template_search_view_inherit_external_id')
        
        self.assertTrue(inherited_view, "Inherited search view should exist")
        self.assertEqual(inherited_view.inherit_id, search_view, 
                         "Inherited view should extend the product template search view")
        
        self.assertIn('field name="external_id"', inherited_view.arch,
                      "Search view should contain the external_id field")

    @mute_logger('odoo.models')
    def test_multiple_products(self):
        """Test that external IDs are correctly computed for multiple products."""

        products = self.env['product.template']
        for i in range(5):
            product = self.env['product.template'].create({
                'name': f'Batch Test Product {i}',
                'default_code': f'BTP-00{i}',
            })
            products += product
            
            self.env['ir.model.data'].create({
                'name': f'batch_test_product_{i}',
                'module': 'product_external_id',
                'model': 'product.template',
                'res_id': product.id,
            })
        
        products.env.cache.invalidate()
        
        for i, product in enumerate(products):
            self.assertEqual(
                product.external_id,
                f"product_external_id.batch_test_product_{i}",
                f"External ID should be correctly computed for batch product {i}"
            ) 