# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import HttpCase

from odoo.addons.website_sale.controllers.cart import Cart
from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged("post_install", "-at_install")
class TestWebsiteSaleStockProductCombo(HttpCase, WebsiteSaleStockCommon):
    _test_user_groups = (
        "base.group_user",
        "product.group_product_manager",
        "sales_team.group_sale_manager",  # FIXME: use sales_team.group_sale_salesman
    )

    _test_user_name = "Test Sales & Product Manager"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cart_controller = Cart()

    def _create_multiplier_combo(self, burger_stock=100, drink_stock=100, drink_included_qty=2):
        """Create a combo with two choices:
        - "Burger" (`included_qty=1`): one unit of `burger` is consumed per combo.
        - "Drink" (`included_qty=drink_included_qty`): `drink_included_qty` units of `drink` are
          consumed per combo (i.e. `selected_combo_item_qty` > 1 when fully selected).
        """
        burger = self._create_product(name="Test Burger")
        self.env["stock.quant"]._update_available_quantity(
            burger, self.warehouse.lot_stock_id, burger_stock
        )
        drink = self._create_product(name="Test Drink")
        self.env["stock.quant"]._update_available_quantity(
            drink, self.warehouse.lot_stock_id, drink_stock
        )
        burger_combo = self.env["product.combo"].create({
            "name": "Test Burger Combo",
            "included_qty": 1,
            "combo_item_ids": [Command.create({"product_id": burger.id})],
        })
        if "qty_max" in self.env["product.combo"]._fields:
            drink_combo = self.env["product.combo"].create({
                "name": "Test Drink Combo",
                "included_qty": drink_included_qty,
                "combo_item_ids": [Command.create({"product_id": drink.id})],
                "qty_max": drink_included_qty,
            })
        else:
            drink_combo = self.env["product.combo"].create({
                "name": "Test Drink Combo",
                "included_qty": drink_included_qty,
                "combo_item_ids": [Command.create({"product_id": drink.id})],
            })

        combo_product = self._create_product(
            name="Test Menu Combo",
            type="combo",
            combo_ids=[Command.set([burger_combo.id, drink_combo.id])],
        )
        return burger, drink, burger_combo, drink_combo, combo_product

    def _combo_item_payload(self, combo, quantity, selected_combo_item_qty, parent_template_id):
        combo_item = combo.combo_item_ids
        return {
            "product_id": combo_item.product_id.id,
            "product_template_id": combo_item.product_id.product_tmpl_id.id,
            "parent_product_template_id": parent_template_id,
            "combo_item_id": combo_item.id,
            "quantity": quantity,
            "selected_combo_item_qty": selected_combo_item_qty,
            "no_variant_attribute_value_ids": [],
            "product_custom_attribute_values": [],
        }

    def test_combo_add_to_cart_blocks_when_multiplier_exceeds_stock(self):
        """A combo item consuming more than 1 unit per combo (`selected_combo_item_qty`) must be
        verified against the real consumed quantity, not the raw combo count.
        """
        burger, drink, burger_combo, drink_combo, combo_product = self._create_multiplier_combo(
            drink_stock=1, drink_included_qty=2
        )
        tmpl_id = combo_product.product_tmpl_id.id
        with self.mock_request(sale_order_id=self.cart.id):
            result = self.cart_controller.add_to_cart(
                product_template_id=tmpl_id,
                product_id=combo_product.id,
                quantity=1,
                linked_products=[
                    self._combo_item_payload(burger_combo, 1, 1, tmpl_id),
                    self._combo_item_payload(drink_combo, 1, 2, tmpl_id),
                ],
            )

        self.assertEqual(result["quantity"], 0)
        self.assertFalse(
            self.cart.order_line.filtered(
                lambda line: line.product_id in (burger, drink, combo_product)
            )
        )

    def test_combo_add_to_cart_allows_when_stock_covers_multiplier(self):
        _burger, drink, burger_combo, drink_combo, combo_product = self._create_multiplier_combo(
            drink_stock=2, drink_included_qty=2
        )
        tmpl_id = combo_product.product_tmpl_id.id
        with self.mock_request(sale_order_id=self.cart.id):
            result = self.cart_controller.add_to_cart(
                product_template_id=tmpl_id,
                product_id=combo_product.id,
                quantity=1,
                linked_products=[
                    self._combo_item_payload(burger_combo, 1, 1, tmpl_id),
                    self._combo_item_payload(drink_combo, 1, 2, tmpl_id),
                ],
            )

        self.assertEqual(result["quantity"], 1)
        drink_line = self.cart.order_line.filtered(lambda line: line.product_id == drink)
        self.assertEqual(drink_line.product_uom_qty, 2)

    def test_combo_check_combo_quantities_reconciles_multiplier_lines(self):
        """When stock forces a reduction, every combo item line (parent included) must be
        reconciled to the *same* combo count, each multiplied by its own
        `selected_combo_item_qty`, not to a shared raw quantity.
        """
        burger, drink, burger_combo, drink_combo, combo_product = self._create_multiplier_combo(
            drink_stock=3, drink_included_qty=2
        )
        tmpl_id = combo_product.product_tmpl_id.id
        with self.mock_request(sale_order_id=self.cart.id):
            result = self.cart_controller.add_to_cart(
                product_template_id=tmpl_id,
                product_id=combo_product.id,
                quantity=2,
                linked_products=[
                    self._combo_item_payload(burger_combo, 2, 1, tmpl_id),
                    self._combo_item_payload(drink_combo, 2, 2, tmpl_id),
                ],
            )

        parent_line = self.cart.order_line.filtered(lambda line: line.product_id == combo_product)
        burger_line = self.cart.order_line.filtered(lambda line: line.product_id == burger)
        drink_line = self.cart.order_line.filtered(lambda line: line.product_id == drink)

        # Only 3 drinks are available (2 needed per combo): only 1 combo can be fulfilled, and
        # every line must be brought back to that same combo count.
        self.assertEqual(result["quantity"], 1)
        self.assertEqual(parent_line.product_uom_qty, 1)
        self.assertEqual(burger_line.product_uom_qty, 1)
        self.assertEqual(drink_line.product_uom_qty, 2)

        self.assertTrue(
            any(notification["type"] == "warning" for notification in result["notifications"])
        )
        item_added = next(
            notification
            for notification in result["notifications"]
            if notification["type"] == "item_added"
        )
        quantity_by_line_id = {line["id"]: line["quantity"] for line in item_added["data"]["lines"]}
        # The notification badge must reflect each line's real quantity, not the combo count.
        self.assertEqual(quantity_by_line_id[burger_line.id], 1)
        self.assertEqual(quantity_by_line_id[drink_line.id], 2)

    def test_combo_cart_update_line_quantity_propagates_warning_and_resyncs_quantity(self):
        _burger, _drink, burger_combo, drink_combo, combo_product = self._create_multiplier_combo(
            drink_stock=2, drink_included_qty=2
        )
        tmpl_id = combo_product.product_tmpl_id.id
        with self.mock_request(sale_order_id=self.cart.id):
            self.cart_controller.add_to_cart(
                product_template_id=tmpl_id,
                product_id=combo_product.id,
                quantity=1,
                linked_products=[
                    self._combo_item_payload(burger_combo, 1, 1, tmpl_id),
                    self._combo_item_payload(drink_combo, 1, 2, tmpl_id),
                ],
            )
        parent_line = self.cart.order_line.filtered(lambda line: line.product_id == combo_product)
        self.assertEqual(parent_line.product_uom_qty, 1)

        # Both available drinks are already reserved by this combo; bumping the combo count to 2
        # (needing 2 more drinks) must be rejected with a warning, and the reported/stored
        # quantity must reflect what was actually kept, not the unavailable requested value.
        with self.mock_request(sale_order_id=self.cart.id):
            result = self.cart._cart_update_line_quantity(line_id=parent_line.id, quantity=2)

        self.assertTrue(result["warning"])
        self.assertEqual(result["quantity"], 1)
        self.assertEqual(parent_line.product_uom_qty, 1)

    def test_combo_get_max_quantity_respects_included_qty(self):
        drink = self._create_product(
            name="Test Drink", is_storable=True, allow_out_of_stock_order=False
        )
        self.env["stock.quant"]._update_available_quantity(drink, self.warehouse.lot_stock_id, 5)
        if "qty_max" in self.env["product.combo"]._fields:
            combo = self.env["product.combo"].create({
                "name": "Drink",
                "included_qty": 2,
                "combo_item_ids": [Command.create({"product_id": drink.id})],
                "qty_max": 2,
            })
        else:
            combo = self.env["product.combo"].create({
                "name": "Drink",
                "included_qty": 2,
                "combo_item_ids": [Command.create({"product_id": drink.id})],
            })

        with self.mock_request(sale_order_id=self.cart.id):
            # 5 drinks available, 2 needed per combo -> at most 2 full combos, not 5.
            self.assertEqual(combo._get_max_quantity(self.website, self.cart), 2)

    def test_combo_check_validity_rejects_selected_qty_mismatch(self):
        burger, drink, burger_combo, drink_combo, combo_product = self._create_multiplier_combo()
        parent_line = self.env["sale.order.line"].create({
            "order_id": self.cart.id,
            "product_id": combo_product.id,
            "product_uom_qty": 1,
        })
        self.env["sale.order.line"].create({
            "order_id": self.cart.id,
            "product_id": burger.id,
            "product_uom_qty": 1,
            "linked_line_id": parent_line.id,
            "combo_item_id": burger_combo.combo_item_ids.id,
            "selected_combo_item_qty": 1,
        })
        drink_line = self.env["sale.order.line"].create({
            "order_id": self.cart.id,
            "product_id": drink.id,
            "product_uom_qty": 10,
            "linked_line_id": parent_line.id,
            "combo_item_id": drink_combo.combo_item_ids.id,
            "selected_combo_item_qty": 10,  # Should be 2, per `drink_combo.included_qty`.
        })

        with self.assertRaises(UserError):
            parent_line._check_validity()

        # Bringing the quantity back in line with `included_qty` must clear the error.
        drink_line.write({"product_uom_qty": 2, "selected_combo_item_qty": 2})
        parent_line._check_validity()

    def test_get_max_quantity_with_max(self):
        product_a = self._create_product(is_storable=True, allow_out_of_stock_order=False)
        product_b = self._create_product(is_storable=True, allow_out_of_stock_order=False)
        self.env["stock.quant"].sudo().create([
            {
                "product_id": product_a.id,
                "location_id": self.warehouse.lot_stock_id.id,
                "quantity": 5,
            },
            {
                "product_id": product_b.id,
                "location_id": self.warehouse.lot_stock_id.id,
                "quantity": 10,
            },
        ])
        combo = self.env["product.combo"].create({
            "name": "Test combo",
            "combo_item_ids": [
                Command.create({"product_id": product_a.id}),
                Command.create({"product_id": product_b.id}),
            ],
        })
        self.cart.order_line = [Command.create({"product_id": product_b.id, "product_uom_qty": 3})]

        with self.mock_request(sale_order_id=self.cart.id):
            self.assertEqual(combo._get_max_quantity(self.website, self.cart), 7)

    def test_get_max_quantity_without_max(self):
        product_a = self._create_product(is_storable=True, allow_out_of_stock_order=False)
        product_b = self._create_product(is_storable=True, allow_out_of_stock_order=True)
        self.env["stock.quant"].sudo().create({
            "product_id": product_a.id,
            "location_id": self.warehouse.lot_stock_id.id,
            "quantity": 5,
        })
        combo = self.env["product.combo"].create({
            "name": "Test combo",
            "combo_item_ids": [
                Command.create({"product_id": product_a.id}),
                Command.create({"product_id": product_b.id}),
            ],
        })

        self.assertIsNone(combo._get_max_quantity(self.website, self.cart))

    def test_website_sale_stock_max_combo(self):
        """
        Ensure we cannot add to the cart more units of a combo product than what is available in
        stock (the maximum quantity of its combo items).
        """
        product1 = self._create_product(name="Test product1")
        self.env["stock.quant"]._update_available_quantity(product1, self.warehouse.lot_stock_id, 2)
        product2 = self._create_product(name="Test product2")
        self.env["stock.quant"]._update_available_quantity(product2, self.warehouse.lot_stock_id, 1)
        self._create_product(
            name="ComboProduct",
            type="combo",
            combo_ids=[
                Command.create({
                    "name": "Test combo",
                    "combo_item_ids": [
                        Command.create({"product_id": product1.id}),
                        Command.create({"product_id": product2.id}),
                    ],
                })
            ],
        )
        self.start_tour("/shop?search=ComboProduct", "test_website_sale_stock_max_combo")
