from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestSaleOrderDiscountLimit(SaleCommon):

    def _create_order_with_discount(self, discount, **values):
        return self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 100,
                    'price_unit': 10,
                    'discount': discount,
                }),
            ],
            **values,
        })

    def test_default_discount_limit_is_15_percent(self):
        order = self._create_order_with_discount(0)

        self.assertEqual(order.descuento_maximo_permitido, 15.0)

    def test_confirm_order_with_discount_below_limit(self):
        order = self._create_order_with_discount(10)

        order.action_confirm()

        self.assertEqual(order.state, 'sale')

    def test_confirm_order_without_discount(self):
        order = self._create_order_with_discount(0)

        order.action_confirm()

        self.assertEqual(order.state, 'sale')

    def test_confirm_order_with_discount_equal_to_limit(self):
        order = self._create_order_with_discount(15)

        order.action_confirm()

        self.assertEqual(order.state, 'sale')

    def test_confirm_order_with_discount_above_limit_is_blocked(self):
        order = self._create_order_with_discount(10)
        order.order_line.with_context(skip_discount_limit_validation=True).discount = 16

        with self.assertRaisesRegex(UserError, 'supera el 15% de descuento permitido'):
            order.action_confirm()

        self.assertEqual(order.state, 'requires_review')

    def test_confirm_order_with_decimal_discount_above_limit_is_blocked(self):
        order = self._create_order_with_discount(10)
        order.order_line.with_context(skip_discount_limit_validation=True).discount = 15.1

        with self.assertRaisesRegex(UserError, 'supera el 15% de descuento permitido'):
            order.action_confirm()

        self.assertEqual(order.state, 'requires_review')

    def test_confirm_order_with_multiple_lines_blocks_when_one_line_exceeds_limit(self):
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 100,
                    'price_unit': 10,
                    'discount': 10,
                }),
                Command.create({
                    'product_id': self.service_product.id,
                    'product_uom_qty': 1,
                    'price_unit': 50,
                    'discount': 15,
                }),
            ],
        })
        order.order_line[1].with_context(skip_discount_limit_validation=True).discount = 16

        with self.assertRaisesRegex(UserError, 'supera el 15% de descuento permitido'):
            order.action_confirm()

        self.assertEqual(order.state, 'requires_review')

    def test_custom_discount_limit_allows_higher_discount(self):
        order = self._create_order_with_discount(16, descuento_maximo_permitido=20)

        order.action_confirm()

        self.assertEqual(order.state, 'sale')

    def test_custom_lower_discount_limit_blocks_regular_discount(self):
        order = self._create_order_with_discount(0, descuento_maximo_permitido=5)
        order.order_line.with_context(skip_discount_limit_validation=True).discount = 10

        with self.assertRaisesRegex(UserError, 'supera el 15% de descuento permitido'):
            order.action_confirm()

        self.assertEqual(order.state, 'requires_review')

    def test_create_order_with_discount_above_limit_is_blocked(self):
        with self.assertRaisesRegex(UserError, 'supera el 15% de descuento permitido'):
            self._create_order_with_discount(16)

    def test_create_new_line_with_discount_above_limit_is_blocked(self):
        order = self._create_order_with_discount(10)

        with self.assertRaisesRegex(UserError, 'supera el 15% de descuento permitido'):
            self.env['sale.order.line'].create({
                'order_id': order.id,
                'product_id': self.service_product.id,
                'product_uom_qty': 1,
                'price_unit': 50,
                'discount': 16,
            })

        self.assertEqual(order.state, 'requires_review')

    def test_section_line_discount_is_ignored(self):
        order = self._create_order_with_discount(10)
        self.env['sale.order.line'].with_context(skip_discount_limit_validation=True).create({
            'order_id': order.id,
            'display_type': 'line_section',
            'name': 'Sección comercial',
            'discount': 99,
        })

        order.action_confirm()

        self.assertEqual(order.state, 'sale')

    def test_saving_order_line_with_discount_above_limit_is_blocked(self):
        order = self._create_order_with_discount(10)

        with self.assertRaisesRegex(UserError, 'supera el 15% de descuento permitido'):
            order.write({
                'order_line': [
                    Command.update(order.order_line.id, {'discount': 16}),
                ],
            })

        self.assertEqual(order.state, 'requires_review')

    def test_direct_line_write_with_discount_above_limit_is_blocked(self):
        order = self._create_order_with_discount(10)

        with self.assertRaisesRegex(UserError, 'supera el 15% de descuento permitido'):
            order.order_line.discount = 16

        self.assertEqual(order.state, 'requires_review')

    def test_write_unrelated_sale_order_field_keeps_valid_order_confirmable(self):
        order = self._create_order_with_discount(10)

        order.write({'client_order_ref': 'QA-BACKEND-001'})
        order.action_confirm()

        self.assertEqual(order.client_order_ref, 'QA-BACKEND-001')
        self.assertEqual(order.state, 'sale')
