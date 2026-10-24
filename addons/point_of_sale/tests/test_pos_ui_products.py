# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import PosHttpCommon


@tagged('post_install', '-at_install')
class TestPoSProductVariants(PosHttpCommon):

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        def create_attribute(name, values, **kwargs):
            return cls.env['product.attribute'].create({
                'name': name,
                'value_ids': [Command.create({'name': value}) for value in values],
                **kwargs,
            })

        cls.dynamic_attribute = create_attribute('Dynamic', ['dyn1', 'dyn2', 'dyn3'], create_variant='dynamic')
        cls.size_attribute = create_attribute('Size', ['S', 'M'])
        cls.size_attribute_s, cls.size_attribute_m = cls.size_attribute.value_ids
        cls.no_variant_attribute = create_attribute('No variant', ['extra', 'second'], create_variant='no_variant')
        cls.no_variant_attribute_extra, cls.no_variant_attribute_second = cls.no_variant_attribute.value_ids
        cls.variant_color_attribute = create_attribute('Color', ['blue'])
        cls.image_attribute = create_attribute('Images', ['First Image', 'Second Image'], display_type='image')
        cls.image_attribute.value_ids[1].default_extra_price = 20

    def _setup_variant_product(self, name, *attribute_values):
        product = self.wall_shelf
        product.write({
            'name': name,
            'list_price': 1,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': values.attribute_id.id,
                    'value_ids': [Command.set(values.ids)],
                }) for values in attribute_values
            ],
        })
        if product.has_dynamic_attributes():
            # Start with dyn2 so the tour also exercises creating the dyn1 variant.
            dynamic_value = product.attribute_line_ids.product_template_value_ids.filtered(
                lambda value: value.product_attribute_value_id == self.dynamic_attribute.value_ids[1]
            )
            combination = product._get_first_possible_combination(necessary_values=dynamic_value)
            product._create_product_variant(combination)
        return product

    def test_integration_dynamic_variant_price(self):
        """Tests the price of products with dynamic variants when added to cart."""
        self.dynamic_attribute.value_ids[1].default_extra_price = 5
        self.dynamic_attribute.value_ids[2].default_extra_price = 10
        self._setup_variant_product('A dynamic product', self.dynamic_attribute.value_ids)
        self.start_pos_tour('test_integration_dynamic_variant_price')

    def test_integration_always_variant_price(self):
        """Tests the price of products with always variants when added to cart."""
        self.size_attribute_m.default_extra_price = 5
        self._setup_variant_product('A always product', self.size_attribute.value_ids)
        self.start_pos_tour('test_integration_always_variant_price')

    def test_integration_never_variant_price(self):
        """Tests the price of products with no-variant attributes when added to cart."""
        self.no_variant_attribute_second.default_extra_price = 5
        self._setup_variant_product('A never product', self.no_variant_attribute.value_ids)
        self.start_pos_tour('test_integration_never_variant_price')

    def test_integration_dynamic_always_variant_price(self):
        """Tests the price of products with dynamic and always variants when added to cart."""
        self.dynamic_attribute.value_ids[1].default_extra_price = 10
        self.dynamic_attribute.value_ids[2].default_extra_price = 20
        self.size_attribute_m.default_extra_price = 5
        self._setup_variant_product(
            'A dyn/alw product', self.dynamic_attribute.value_ids, self.size_attribute.value_ids,
        )
        self.start_pos_tour('test_integration_dynamic_always_variant_price')

    def test_integration_dynamic_never_variant_price(self):
        """Tests the price of products with dynamic and never variants when added to cart."""
        self.dynamic_attribute.value_ids[1].default_extra_price = 10
        self.dynamic_attribute.value_ids[2].default_extra_price = 20
        self.no_variant_attribute_second.default_extra_price = 5
        self._setup_variant_product(
            'A dyn/nev product', self.dynamic_attribute.value_ids, self.no_variant_attribute.value_ids,
        )
        self.start_pos_tour('test_integration_dynamic_never_variant_price')

    def test_integration_always_never_variant_price(self):
        """Tests the price of products with always and never variants when added to cart."""
        self.no_variant_attribute_second.default_extra_price = 5
        self.size_attribute_m.default_extra_price = 10
        self._setup_variant_product(
            'A alw/nev product', self.no_variant_attribute.value_ids, self.size_attribute.value_ids,
        )
        self.start_pos_tour('test_integration_always_never_variant_price')

    def test_integration_dynamic_always_never_variant_price(self):
        """Tests the price of products with all types of variants when added to cart."""
        self.dynamic_attribute.value_ids[1].default_extra_price = 10
        self.size_attribute_m.default_extra_price = 5
        self.no_variant_attribute_second.default_extra_price = 0.5
        self._setup_variant_product(
            'A dyn/alw/nev product',
            self.dynamic_attribute.value_ids[:2],
            self.no_variant_attribute.value_ids,
            self.size_attribute.value_ids,
        )
        self.start_pos_tour('test_integration_dynamic_always_never_variant_price')

    def test_image_variants_displayed(self):
        """Variants with the image display type can be selected in the configurator."""
        self._setup_variant_product('Image Product', self.image_attribute.value_ids)
        self.start_pos_tour('test_image_variants_displayed')

    def test_variants_merge_line_barcode(self):
        """Scanning a variant merges it with the matching configured order line."""
        product_template = self._setup_variant_product(
            'A variant product', self.size_attribute.value_ids, self.variant_color_attribute.value_ids,
        )
        product_s_blue = product_template.product_variant_ids.filtered(
            lambda product: self.size_attribute_s in product.product_template_attribute_value_ids.product_attribute_value_id
        )
        self.assertEqual(len(product_s_blue.product_template_variant_value_ids), 1)  # Only size varies.
        self.assertEqual(len(product_s_blue.product_template_attribute_value_ids), 2)  # S and blue.
        product_s_blue.barcode = 'TEST123'
        self.start_pos_tour('test_variants_merge_line_barcode')

    def test_archived_product_removed_and_order_is_refunded(self):
        """An archived product is hidden from the catalog but its order can still be refunded."""
        self.pos_admin.write({
            'group_ids': [
                Command.link(self.env.ref('product.group_product_manager').id),
                Command.link(self.env.ref('account.group_account_manager').id),
            ],
        })
        product = self._setup_variant_product('A Test Product')
        self.start_pos_tour('test_archived_product_removed_and_order_is_refunded_1', login='pos_admin')

        self.close_pos_session()
        product.action_archive()

        self.start_pos_tour('test_archived_product_removed_and_order_is_refunded_2', login='pos_admin')
