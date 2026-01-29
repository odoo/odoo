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
        amount_before_discount = self.sale_order.amount_total
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
        self.assertAlmostEqual(discount_line.price_unit, -amount_before_discount * 0.5)
        self.assertEqual(discount_line.tax_id, dumb_tax)
        self.assertEqual(discount_line.product_uom_qty, 1.0)

        # Two tax groups
        discount_line.unlink()
        solines[0].tax_id = [Command.clear()]
        self.wizard.action_apply_discount()
        discount_lines = self.sale_order.order_line - solines
        self.assertEqual(len(discount_lines), 2)
        self.assertEqual(discount_lines[0].price_unit, -solines[0].price_subtotal * 0.5)
        self.assertEqual(discount_lines[1].price_unit, -solines[1].price_subtotal * 0.5)
        self.assertEqual(discount_lines[0].tax_id, solines[0].tax_id)
        self.assertEqual(discount_lines[1].tax_id, solines[1].tax_id)
        self.assertTrue(all(line.product_uom_qty == 1.0 for line in discount_lines))

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

    def test_discount_translation(self):
        self.env['res.lang']._activate_lang('es_AR')
        self.wizard.write({
            'discount_percentage': 0.1,
            'discount_type': 'so_discount',
        })
        self.wizard.sale_order_id.partner_id.lang = 'es_AR'
        self.wizard.action_apply_discount()
        discount_line = self.sale_order.order_line[-1]
        self.assertEqual(discount_line.name, "Descuento: 10.00%")

    def test_discount_translation_tax_groups(self):
        self.env['res.lang']._activate_lang('es_AR')
        self.wizard.write({
            'discount_percentage': 0.1,
            'discount_type': 'so_discount',
        })
        self.wizard.sale_order_id.partner_id.lang = 'es_AR'
        tax1, tax2 = self.env['account.tax'].create([{
            'name': f"{percentage}% VAT",
            'amount_type': 'percent',
            'amount': percentage,
        } for percentage in (10, 20)])
        self.wizard.sale_order_id.order_line[0].tax_id = tax1
        self.wizard.sale_order_id.order_line[1].tax_id = tax2
        self.wizard.action_apply_discount()
        self.assertEqual(
            self.sale_order.order_line[-2].name,
            "Descuento: 10.00%- En los productos con los siguientes impuestos 10% VAT",
        )
        self.assertEqual(
            self.sale_order.order_line[-1].name,
            "Descuento: 10.00%- En los productos con los siguientes impuestos 20% VAT",
        )

    def test_line_and_global_discount(self):
        solines = self.sale_order.order_line
        amount_before_discount = self.sale_order.amount_untaxed
        self.assertEqual(len(solines), 2)

        solines.discount = 10
        self.assertEqual(self.sale_order.amount_untaxed, amount_before_discount * 0.9)
        amount_with_line_discount = self.sale_order.amount_untaxed

        self.wizard.write({
            'discount_percentage': 0.1,  # 10%
            'discount_type': 'so_discount',
        })
        self.wizard.action_apply_discount()
        self.assertEqual(self.sale_order.amount_untaxed, amount_with_line_discount * 0.9)
        discount_line = self.sale_order.order_line.filtered(lambda ol: ol._is_discount_line())
        # Double the discount by changing the quantity instead of the value
        discount_line.product_uom_qty = 2
        self.assertEqual(self.sale_order.amount_untaxed, amount_with_line_discount * 0.8)
