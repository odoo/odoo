# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestSaleOrderDiscount(SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wizard = cls.env['sale.order.discount'].create({
            'sale_order_id': cls.sale_order.id,
            'discount_type': 'amount',
        })

    def test_amount(self):
        self.wizard.write({
            'discount_amount': 55,
            'discount_type': 'amount',
        })
        self.wizard.action_apply_discount()

        discount_line = self.sale_order.order_line[-1]
        self.assertEqual(discount_line.price_unit, -55)
        self.assertEqual(discount_line.product_uom_qty, 1.0)
        self.assertFalse(discount_line.tax_id)

    def test_so_discount(self):
        solines = self.sale_order.order_line
        amount_before_discount = sum(line.price_unit for line in solines)
        self.assertEqual(len(solines), 2)

        # No taxes
        solines.tax_id = [Command.clear()]
        self.wizard.write({
            'discount_percentage': 0.5,  # 50%
            'discount_type': 'so_discount',
        })
        self.wizard.action_apply_discount()

        discount_line = self.sale_order.order_line[-1]
        self.assertAlmostEqual(discount_line.price_unit, -amount_before_discount * 0.5)
        self.assertFalse(discount_line.tax_id)
        self.assertEqual(discount_line.product_uom_qty, 1.0)

        # One tax group
        discount_line.unlink()
        dumb_tax = self.env['account.tax'].create({'name': 'test'})
        solines.tax_id = dumb_tax
        self.wizard.action_apply_discount()

        discount_line = self.sale_order.order_line - solines
        discount_line.ensure_one()
        self.assertAlmostEqual(discount_line.price_unit, -sum(line.price_unit for line in solines) * 0.5)
        self.assertEqual(discount_line.tax_id, dumb_tax)
        self.assertEqual(discount_line.product_uom_qty, 1.0)

        # Two tax groups
        discount_line.unlink()
        solines[0].tax_id = [Command.clear()]
        self.wizard.action_apply_discount()
        discount_lines = self.sale_order.order_line - solines
        self.assertEqual(len(discount_lines), 2)
        for soline, discount_line in zip(solines, discount_lines):
            self.assertEqual(discount_line.price_unit, -soline.price_unit * 0.5)
            self.assertEqual(discount_line.tax_id, soline.tax_id)
            self.assertEqual(discount_line.product_uom_qty, 1.0)

    def test_sol_discount(self):
        so_amount = self.sale_order.amount_untaxed
        self.wizard.write({
            'discount_percentage': 0.5,  # 50%
            'discount_type': 'sol_discount',
        })
        self.wizard.action_apply_discount()

        self.assertTrue(
            all(line.discount == 50 for line in self.sale_order.order_line)
        )
        self.assertAlmostEqual(self.sale_order.amount_untaxed, so_amount*0.5)

        self.wizard.write({'discount_percentage': -0.5})
        self.wizard.action_apply_discount()

        self.assertTrue(
            all(line.discount == -50 for line in self.sale_order.order_line)
        )
        self.assertAlmostEqual(self.sale_order.amount_untaxed, so_amount*1.5)

    def test_sol_discount_removal(self):
        so_amount = self.sale_order.amount_untaxed
        self.wizard.write({'discount_percentage': 0.5, 'discount_type': 'sol_discount'})
        self.wizard.action_apply_discount()

        self.wizard.write({'discount_percentage': 0})
        self.wizard.action_apply_discount()

        self.assertFalse(self.sale_order.order_line.filtered('discount'))
        self.assertAlmostEqual(self.sale_order.amount_untaxed, so_amount)

    def test_percent_discount_above_100(self):
        with self.assertRaises(ValidationError):
            self.wizard.write({'discount_percentage': 1.1, 'discount_type': 'sol_discount'})
