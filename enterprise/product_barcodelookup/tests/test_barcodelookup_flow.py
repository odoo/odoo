from odoo.tests import HttpCase, tagged, Form
from ...product_barcodelookup.tests.common import MockAPIBarcodelookup
from odoo import Command


@tagged('post_install', '-at_install')
class TestBarcodelookup(HttpCase, MockAPIBarcodelookup):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_category_1 = cls.env['product.category'].create({'name': 'Business & Industrial'})

    def _verify_product_data(self, product, normalized_view=False, variant_rights=True):
        self.assertEqual(product.name, "Odoo Scale up")
        self.assertEqual(product.categ_id.name, "Business & Industrial")

        # weight is not present in main view, but in normalized view
        if normalized_view:
            self.assertEqual(product.weight, 1.5)

        # check attributes only if not creating from normalized view.
        if not normalized_view:
            # when user have rights to create attributes
            if variant_rights:
                self.assertEqual(len(product.attribute_line_ids), 5)
                self.assertItemsEqual(product.attribute_line_ids.value_ids.mapped('name'), ['Test gender', 'Cotton', 'Odoo s.a', 'Odoo', '9.75 × 8.25 in'])
            else:
                self.assertFalse(product.attribute_line_ids)

    def test_01_barcodelookup_flow(self):
        with self.mockBarcodelookupAutofill():
            templ_form = Form(self.env['product.template'])
            templ_form.barcode = "710535977349"
            product = templ_form.save()
            self._verify_product_data(product, variant_rights=self.env.user.has_group('product.group_product_variant'))

    def test_02_product_variant_creation_follows_rights(self):
        env = self.env(user=self.env.ref('base.user_admin'))
        with self.mockBarcodelookupAutofill():
            if self.env.user.has_group('product.group_product_variant'):
                new_product = Form(env['product.template'])
                new_product.barcode = "321535977349"
                variant_product = new_product.save()
                self._verify_product_data(variant_product)

                # check after removing group
                group_product_variant = env.ref('product.group_product_variant', False)
                group_product_variant.write({'users': [(3, env.user.id)]})

            new_form = Form(env['product.template'])  # new form
            new_form.barcode = "497105359773"  # can't create 2 product with same barcode
            product_wo_variant = new_form.save()
            self._verify_product_data(product_wo_variant, variant_rights=False)

    def test_copy_product_template_defaults_to_unpublished(self):
        if 'public_categ_ids' in self.env['product.template']:
            public_category = self.env['product.template'].public_categ_ids.create({'name': 'Website Category'})
            original_product = self.env['product.template'].create({
                'name': 'Test Product',
                'public_categ_ids': [Command.link(public_category.id)],
            })
            self.assertTrue(original_product.is_published, "Created product with category should be published by default")
            copied_product = original_product.copy()
            self.assertFalse(copied_product.is_published, "Copied product should not be published by default")
