from odoo.tests.common import TransactionCase
from odoo.addons.website_sale_combo_suggestions.controllers.main import ComboController


class TestComboSuggestion(TransactionCase):
    """
    Test cases for combo suggestion discount logic.
    """

    def setUp(self):
        super().setUp()
        self.controller = ComboController()

        # Create products
        Product = self.env['product.product']
        self.prod_a = Product.create({'name': 'Product A', 'list_price': 10.0})
        self.prod_b = Product.create({'name': 'Product B', 'list_price': 15.0})

        # Create combo
        Combo = self.env['product.combo']
        ComboItem = self.env['product.combo.item']
        self.combo = Combo.create({'name': 'Combo A+B'})
        ComboItem.create({'combo_id': self.combo.id, 'product_id': self.prod_a.id})
        ComboItem.create({'combo_id': self.combo.id, 'product_id': self.prod_b.id})

        # Create sale order
        self.order = self.env['sale.order'].create({
            'partner_id': self.env.ref('base.res_partner_1').id,
        })

    def _add_order_line(self, product, qty=1, price=None, discount=0.0):
        """
        Helper to add a sale order line.
        """
        line = self.env['sale.order.line'].create({
            'order_id': self.order.id,
            'product_id': product.id,
            'product_uom_qty': qty,
            'price_unit': price if price is not None else product.list_price,
            'discount': discount,
            'name': product.name,
        })
        return line

    def test_combo_applied_successfully(self):
        """
        Applying combo discount when all combo items are present.
        """
        self._add_order_line(self.prod_a)
        self._add_order_line(self.prod_b)

        response = self.controller._apply_discount(self.order, self.combo)
        self.assertTrue(response['success'])

        discounted_lines = self.order.order_line.filtered(lambda l: l.discount > 0)
        self.assertEqual(len(discounted_lines), 2, "There should be 2 lines with discount")
        total_discount = sum(
            l.price_unit * l.product_uom_qty * (l.discount / 100) for l in discounted_lines
        )
        self.assertEqual(total_discount, self.prod_b.list_price)

    def test_combo_not_applicable_after_removal(self):
        """
        Combo discount should not apply if a combo item is removed.
        """
        self._add_order_line(self.prod_a)
        self._add_order_line(self.prod_b)

        self.controller._apply_discount(self.order, self.combo)

        # Remove one combo item
        self.order.order_line.filtered(lambda l: l.product_id == self.prod_b).unlink()

        response = self.controller._apply_discount(self.order, self.combo)

        self.assertFalse(response['success'])

    def test_multiple_combo_applicable(self):
        """
        Combo discount applies multiple times if quantities allow.
        """
        quantity = 2
        self._add_order_line(self.prod_a, qty=quantity)
        self._add_order_line(self.prod_b, qty=quantity)

        response = self.controller._apply_discount(self.order, self.combo)
        self.assertTrue(response['success'])

        discounted_lines = self.order.order_line.filtered(lambda l: l.discount > 0)
        self.assertEqual(len(discounted_lines), 2)
        total_discount = sum(
            l.price_unit * l.product_uom_qty * (l.discount / 100) for l in discounted_lines
        )
        self.assertEqual(total_discount, self.prod_b.list_price * quantity)

    def test_clear_discounts(self):
        """
        Clear all discounts from order lines.
        """
        self._add_order_line(self.prod_a, discount=30.0)
        self._add_order_line(self.prod_b, discount=30.0)

        self.controller._clear_discounts(self.order)

        self.assertTrue(all(line.discount == 0.0 for line in self.order.order_line))

    def test_consolidate_duplicate_lines(self):
        """
        Consolidate duplicate order lines into a single line.
        """
        self._add_order_line(self.prod_a)
        self._add_order_line(self.prod_a)

        before_count = len(self.order.order_line)
        self.controller._consolidate_duplicate_lines(self.order)
        after_count = len(self.order.order_line)

        self.assertLess(after_count, before_count)
