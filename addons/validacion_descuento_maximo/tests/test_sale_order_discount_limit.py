from odoo.exceptions import UserError, ValidationError
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

    def _grant_discount_supervisor_group(self, user):
        user.group_ids += self.env.ref('validacion_descuento_maximo.group_discount_supervisor')

    def _revoke_discount_supervisor_group(self, user):
        user.group_ids -= self.env.ref('validacion_descuento_maximo.group_discount_supervisor')

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

    def test_confirm_order_with_discount_above_limit_requires_review(self):
        order = self._create_order_with_discount(10)
        order.order_line.with_context(skip_discount_limit_validation=True).discount = 16

        order.action_confirm()

        self.assertEqual(order.state, 'requires_review')

    def test_confirm_order_with_decimal_discount_above_limit_requires_review(self):
        order = self._create_order_with_discount(10)
        order.order_line.with_context(skip_discount_limit_validation=True).discount = 15.1

        order.action_confirm()

        self.assertEqual(order.state, 'requires_review')

    def test_confirm_order_with_multiple_lines_requires_review_when_one_line_exceeds_limit(self):
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

        order.action_confirm()

        self.assertEqual(order.state, 'requires_review')

    def test_confirm_mixed_orders_confirms_valid_and_reviews_excessive_discount(self):
        valid_order = self._create_order_with_discount(10)
        order_to_review = self._create_order_with_discount(16)

        (valid_order | order_to_review).action_confirm()

        self.assertEqual(valid_order.state, 'sale')
        self.assertEqual(order_to_review.state, 'requires_review')

    def test_reviewed_order_can_be_confirmed_after_discount_is_fixed(self):
        order = self._create_order_with_discount(16)
        self.assertEqual(order.state, 'requires_review')
        self.assertTrue(order.discount_exceeds_limit)

        order.order_line.discount = 10
        self.assertFalse(order.discount_exceeds_limit)
        order.action_confirm()

        self.assertEqual(order.state, 'sale')

    def test_supervisor_approves_discount_and_order_is_confirmed(self):
        order = self._create_order_with_discount(16)
        self.assertEqual(order.state, 'requires_review')

        self._grant_discount_supervisor_group(self.sale_manager)

        result = order.with_user(self.sale_manager).action_approve_discount()

        self.assertTrue(result)
        self.assertEqual(order.state, 'sale')

    def test_approve_discount_requires_supervisor_group(self):
        order = self._create_order_with_discount(16)
        self._revoke_discount_supervisor_group(self.sale_manager)

        self.assertEqual(order.state, 'requires_review')

        with self.assertRaisesRegex(UserError, 'permiso'):
            order.with_user(self.sale_manager).action_approve_discount()

        self.assertEqual(order.state, 'requires_review')

    def test_approve_discount_only_applies_to_reviewed_orders(self):
        order = self._create_order_with_discount(10)
        self._grant_discount_supervisor_group(self.sale_manager)

        with self.assertRaisesRegex(UserError, 'Requiere Revisión'):
            order.with_user(self.sale_manager).action_approve_discount()

    def test_discount_supervisor_group_implies_sales_manager_access(self):
        supervisor_group = self.env.ref('validacion_descuento_maximo.group_discount_supervisor')

        self.assertIn(self.env.ref('sales_team.group_sale_manager'), supervisor_group.implied_ids)

    def test_regular_sales_user_cannot_change_discount_limit(self):
        order = self._create_order_with_discount(10)
        self._revoke_discount_supervisor_group(self.sale_manager)

        with self.assertRaisesRegex(UserError, 'supervisor'):
            order.with_user(self.sale_manager).write({'descuento_maximo_permitido': 20})

        self.assertEqual(order.descuento_maximo_permitido, 15.0)

    def test_discount_supervisor_can_change_discount_limit(self):
        order = self._create_order_with_discount(10)
        self._grant_discount_supervisor_group(self.sale_manager)

        order.with_user(self.sale_manager).write({'descuento_maximo_permitido': 20})

        self.assertEqual(order.descuento_maximo_permitido, 20)

    def test_custom_discount_limit_allows_higher_discount(self):
        order = self._create_order_with_discount(16, descuento_maximo_permitido=20)

        order.action_confirm()

        self.assertEqual(order.state, 'sale')

    def test_custom_lower_discount_limit_requires_review_for_regular_discount(self):
        order = self._create_order_with_discount(0, descuento_maximo_permitido=5)
        order.order_line.with_context(skip_discount_limit_validation=True).discount = 10

        order.action_confirm()

        self.assertEqual(order.state, 'requires_review')

    def test_discount_limit_cannot_be_negative(self):
        with self.assertRaisesRegex(ValidationError, 'entre 0% y 100%'):
            self._create_order_with_discount(0, descuento_maximo_permitido=-1)

    def test_discount_limit_cannot_exceed_100_percent(self):
        with self.assertRaisesRegex(ValidationError, 'entre 0% y 100%'):
            self._create_order_with_discount(0, descuento_maximo_permitido=101)

    def test_create_order_with_discount_above_limit_requires_review(self):
        order = self._create_order_with_discount(16)

        self.assertEqual(order.state, 'requires_review')

    def test_create_new_line_with_discount_above_limit_requires_review(self):
        order = self._create_order_with_discount(10)

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

    def test_saving_order_line_with_discount_above_limit_requires_review(self):
        order = self._create_order_with_discount(10)

        order.write({
            'order_line': [
                Command.update(order.order_line.id, {'discount': 16}),
            ],
        })

        self.assertEqual(order.state, 'requires_review')

    def test_direct_line_write_with_discount_above_limit_requires_review(self):
        order = self._create_order_with_discount(10)

        order.order_line.discount = 16

        self.assertEqual(order.state, 'requires_review')

    def test_write_unrelated_sale_order_field_keeps_valid_order_confirmable(self):
        order = self._create_order_with_discount(10)

        order.write({'client_order_ref': 'QA-BACKEND-001'})
        order.action_confirm()

        self.assertEqual(order.client_order_ref, 'QA-BACKEND-001')
        self.assertEqual(order.state, 'sale')
