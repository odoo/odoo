# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import Form, tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestSaleOrderComboLinkedLines(SaleCommon):
    """Ensure the batched _get_linked_lines_by_line returns the expected
    linked lines for both the DB (linked_line_id) and the in-memory
    (linked_virtual_id) cases, and that the onchange consuming it still
    drops orphan combo item lines.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        combo_item_products = (
            cls._create_product(name="Combo item A")
            + cls._create_product(name="Combo item B")
        )
        cls.combos = cls.env['product.combo'].create([
            {'name': "Combo A", 'combo_item_ids': [Command.create({'product_id': combo_item_products[0].id})]},
            {'name': "Combo B", 'combo_item_ids': [Command.create({'product_id': combo_item_products[1].id})]},
        ])
        cls.combo_product = cls._create_product(
            name="Meal Menu",
            type='combo',
            combo_ids=[Command.set(cls.combos.ids)],
        )
        cls.regular_product = cls._create_product(name="Regular product")

    def _create_combo_line_with_items(self):
        order = self.empty_order
        combo_line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.combo_product.id,
        })
        item_lines = self.env['sale.order.line'].create([{
            'order_id': order.id,
            'product_id': combo.combo_item_ids.product_id.id,
            'combo_item_id': combo.combo_item_ids.id,
            'linked_line_id': combo_line.id,
        } for combo in self.combos])
        return order, combo_line, item_lines

    def test_get_linked_lines_via_linked_line_id(self):
        """Combo item lines saved in DB are linked through linked_line_id."""
        order, combo_line, item_lines = self._create_combo_line_with_items()

        self.assertEqual(order.order_line._get_linked_lines_by_line()[combo_line], item_lines)

    def test_get_linked_lines_via_linked_virtual_id(self):
        """Not-yet-saved combo item lines are linked through linked_virtual_id."""
        order = self.empty_order
        combo_line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.combo_product.id,
            'virtual_id': 'combo-line',
        })
        item_lines = self.env['sale.order.line'].create([{
            'order_id': order.id,
            'product_id': combo.combo_item_ids.product_id.id,
            'combo_item_id': combo.combo_item_ids.id,
            'linked_virtual_id': 'combo-line',
        } for combo in self.combos])

        self.assertEqual(order.order_line._get_linked_lines_by_line()[combo_line], item_lines)

    def test_combo_items_deleted_when_line_no_longer_combo(self):
        """The onchange drops orphan combo item lines through the batched lookup."""
        order, _combo_line, item_lines = self._create_combo_line_with_items()
        self.assertEqual(len(order.order_line), 3)

        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.product_template_id = self.regular_product.product_tmpl_id

        self.assertFalse(item_lines.exists(), "Orphan combo item lines must be deleted")
