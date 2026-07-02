# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.fields import Command
from odoo.tests import Form, tagged

from odoo.addons.sale.tests.common import SaleCommon

DISCOUNT = 50
NO_TAX_INCL_VALUES = [
    {"margin": 16.67, "margin_percent": 0.25, "price_unit": 66.67},
    {"margin": 25.0, "margin_percent": 1 / 3, "price_unit": 75},
    {"margin": 50.0, "margin_percent": 0.5, "price_unit": 100},
    {"margin": 75.0, "margin_percent": 0.6, "price_unit": 125},
    {"margin": 150.0, "margin_percent": 0.75, "price_unit": 200},
]
NO_TAX_INCL_DISCOUNT_VALUES = [
    {**values, "price_unit": values["price_unit"] / (1 - DISCOUNT / 100)}
    for values in NO_TAX_INCL_VALUES
]

TAX_INCL_VALUES = [
    {"margin": -16.67, "margin_percent": -0.50, "price_unit": 50, "purchase_price": 50},
    {"margin": 16.67, "margin_percent": 0.25, "price_unit": 100, "purchase_price": 50},
    {"margin": 33.33, "margin_percent": 0.4, "price_unit": 125, "purchase_price": 50},
    {"margin": 50.0, "margin_percent": 0.5, "price_unit": 150, "purchase_price": 50},
    {"margin": 83.33, "margin_percent": 0.625, "price_unit": 200, "purchase_price": 50},
    {"margin": 283.33, "margin_percent": 0.85, "price_unit": 500, "purchase_price": 50},
]
TAX_INCL_DISCOUNT_VALUES = [
    {**values, "price_unit": values["price_unit"] / (1 - DISCOUNT / 100)}
    for values in TAX_INCL_VALUES
]


@tagged("at_install", "-post_install")  # LEGACY at_install
class TestSaleMargin(SaleCommon):
    _test_groups = (
        'base.group_user',
        'product.group_product_manager',  # FIXME: use base.group_user
        'sales_team.group_sale_manager',  # FIXME: use sales_team.group_sale_salesman
    )

    _test_user_name = 'Test Sales & Product Manager'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._enable_discounts()

        cls.product_50_margin = cls._create_product(
            list_price=100.0, standard_price=50.0, taxes_id=[Command.set([])]
        )
        tax_group = cls.env["account.tax.group"].sudo().create({"name": "Tax Group A"})
        cls.tax_included, cls.tax_excluded, cls.tax_default = cls.env["account.tax"].create([
            {
                "name": "Tax with price include",
                "amount": 50,
                "price_include_override": "tax_included",
                "tax_group_id": tax_group.id,
            },
            {
                "name": "Tax with price exclude",
                "amount": 50,
                "price_include_override": "tax_excluded",
                "tax_group_id": tax_group.id,
            },
            {"name": "Tax with default", "amount": 50, "tax_group_id": tax_group.id},
        ])

        cls.so = cls._create_so(
            order_line=[Command.create({"product_id": cls.product_50_margin.id})]
        )
        cls.sol = cls.so.order_line

    def test_sale_margin(self):
        """Test the sale_margin module in Odoo."""
        self.product.standard_price = 700.0
        order = self._create_so(
            order_line=[
                Command.create({
                    "price_unit": 1000.0,
                    "product_uom_qty": 10.0,
                    "product_id": self.product.id,
                })
            ]
        )
        # Confirm the sales order.
        order.action_confirm()
        # Verify that margin field gets bind with the value.
        self.assertEqual(order.margin, 3000.00, "Sales order profit should be 6000.00")
        self.assertEqual(order.margin_percent, 0.3, "Sales order margin should be 30%")

    def test_negative_margin(self):
        """Test the margin when sales price is less then cost."""
        self.service_product.standard_price = 40.0

        order = self._create_so(
            order_line=[
                Command.create({
                    "price_unit": 20.0,
                    "product_uom_qty": 1.0,
                    "state": "draft",
                    "product_id": self.service_product.id,
                }),
                Command.create({
                    "price_unit": -100.0,
                    "purchase_price": 0.0,
                    "product_uom_qty": 1.0,
                    "state": "draft",
                    "product_id": self.product.id,
                }),
            ]
        )
        # Confirm the sales order.
        order.action_confirm()
        # Verify that margin field of Sale Order Lines gets bind with the value.
        self.assertEqual(order.order_line[0].margin, -20.00, "Sales order profit should be -20.00")
        self.assertEqual(
            order.order_line[0].margin_percent, -1, "Sales order margin percentage should be -100%"
        )
        self.assertEqual(
            order.order_line[1].margin, -100.00, "Sales order profit should be -100.00"
        )
        self.assertEqual(
            order.order_line[1].margin_percent,
            1.00,
            "Sales order margin should be 100% when the cost is zero and price defined",
        )
        # Verify that margin field gets bind with the value.
        self.assertEqual(order.margin, -120.00, "Sales order margin should be -120.00")
        self.assertEqual(order.margin_percent, 1.5, "Sales order margin should be 150%")

    def test_margin_no_cost(self):
        """Test the margin when cost is 0 margin percentage should always be 100%."""
        order = self._create_so(
            order_line=[
                Command.create({
                    "product_id": self.product.id,
                    "price_unit": 70.0,
                    "product_uom_qty": 1.0,
                })
            ]
        )

        # Verify that margin field of Sale Order Lines gets bind with the value.
        self.assertEqual(order.order_line[0].margin, 70.00, "Sales order profit should be 70.00")
        self.assertEqual(
            order.order_line[0].margin_percent,
            1.0,
            "Sales order margin percentage should be 100.00",
        )
        # Verify that margin field gets bind with the value.
        self.assertEqual(order.margin, 70.00, "Sales order profit should be 70.00")
        self.assertEqual(
            order.margin_percent, 1.00, "Sales order margin percentage should be 100.00"
        )

    def test_margin_considering_product_qty(self):
        """Test the margin and margin percentage when product with multiple quantity."""
        self.service_product.standard_price = 50.0

        order = self._create_so(
            order_line=[
                Command.create({
                    "price_unit": 100.0,
                    "product_uom_qty": 3.0,
                    "product_id": self.service_product.id,
                }),
                Command.create({
                    "price_unit": -50.0,
                    "product_uom_qty": 1.0,
                    "product_id": self.product.id,
                }),
            ]
        )

        # Confirm the sales order.
        order.action_confirm()
        # Verify that margin field of Sale Order Lines gets bind with the value.
        self.assertEqual(order.order_line[0].margin, 150.00, "Sales order profit should be 150.00")
        self.assertEqual(
            order.order_line[0].margin_percent, 0.5, "Sales order margin should be 100%"
        )
        self.assertEqual(order.order_line[1].margin, -50.00, "Sales order profit should be -50.00")
        self.assertEqual(
            order.order_line[1].margin_percent, 1.0, "Sales order margin should be 100%"
        )
        # Verify that margin field gets bind with the value.
        self.assertEqual(order.margin, 100.00, "Sales order profit should be 100.00")
        self.assertEqual(order.margin_percent, 0.4, "Sales order margin should be 40%")

    def test_sale_margin_order_copy(self):
        """When we copy a sales order, its margins should be update to meet the current costs."""
        # We buy at a specific price today and our margins go according to that
        self.product.standard_price = 500.0
        order = self._create_so(
            order_line=[
                Command.create({
                    "price_unit": 1000.0,
                    "product_uom_qty": 10.0,
                    "product_id": self.product.id,
                })
            ]
        )
        self.assertAlmostEqual(500.0, order.order_line.purchase_price)
        self.assertAlmostEqual(5000.0, order.order_line.margin)
        self.assertAlmostEqual(0.5, order.order_line.margin_percent)
        # Later on, the cost of our product changes and so will the following sale
        # margins do.
        self.product.standard_price = 750.0
        following_sale = order.copy()
        self.assertAlmostEqual(750.0, following_sale.order_line.purchase_price)
        self.assertAlmostEqual(2500.0, following_sale.order_line.margin)
        self.assertAlmostEqual(0.25, following_sale.order_line.margin_percent)

    def test_margin_onchanges_no_tax(self):
        self.assertRecordValues(
            self.sol,
            [
                {
                    "price_unit": 100.0,
                    "purchase_price": 50,
                    "margin": 50,
                    "margin_percent": 0.5,
                    "tax_ids": [],
                }
            ],
        )
        self._test_margin_onchange("margin", NO_TAX_INCL_VALUES)
        self._test_margin_onchange("margin_percent", NO_TAX_INCL_VALUES)

        self.sol.discount = DISCOUNT
        self._test_margin_onchange("margin", NO_TAX_INCL_DISCOUNT_VALUES)
        self._test_margin_onchange("margin_percent", NO_TAX_INCL_DISCOUNT_VALUES)

    def test_margin_onchanges_tax_excl(self):
        self.product_50_margin.taxes_id = [Command.link(self.tax_excluded.id)]
        self.so._recompute_taxes()
        self.assertRecordValues(
            self.sol,
            [
                {
                    "price_unit": 100.0,
                    "purchase_price": 50.0,
                    "margin": 50,
                    "margin_percent": 0.5,
                    "tax_ids": [self.tax_excluded.id],
                }
            ],
        )
        # Price excluded taxes should not have any impact on the margin computation
        self._test_margin_onchange("margin", NO_TAX_INCL_VALUES)
        self._test_margin_onchange("margin_percent", NO_TAX_INCL_VALUES)

        self.sol.discount = DISCOUNT
        self._test_margin_onchange("margin", NO_TAX_INCL_DISCOUNT_VALUES)
        self._test_margin_onchange("margin_percent", NO_TAX_INCL_DISCOUNT_VALUES)

    def test_margin_onchanges_tax_incl(self):
        self.product_50_margin.taxes_id = [Command.link(self.tax_included.id)]
        self.so._recompute_taxes()
        self.assertRecordValues(
            self.sol,
            [
                {
                    "price_unit": 100.0,
                    "purchase_price": 50.0,
                    "margin": 16.67,
                    "margin_percent": 0.25,
                    "tax_ids": [self.tax_included.id],
                    "price_tax": 33.33,
                }
            ],
        )
        self._test_margin_onchange("margin", TAX_INCL_VALUES)
        self._test_margin_onchange("margin_percent", TAX_INCL_VALUES)
        self.sol.discount = 50
        self._test_margin_onchange("margin", TAX_INCL_DISCOUNT_VALUES)
        self._test_margin_onchange("margin_percent", TAX_INCL_DISCOUNT_VALUES)

    def test_margin_onchanges_tax_incl_excl(self):
        self.product_50_margin.taxes_id = [
            Command.link(self.tax_excluded.id),
            Command.link(self.tax_included.id),
        ]
        self.so._recompute_taxes()
        self.assertRecordValues(
            self.sol,
            [
                {
                    "price_unit": 100.0,
                    "purchase_price": 50.0,
                    "margin": 16.67,
                    "margin_percent": 0.25,
                    "tax_ids": [self.tax_excluded.id, self.tax_included.id],
                }
            ],
        )
        # Price excluded taxes should not have any impact on the margin computation
        self._test_margin_onchange("margin", TAX_INCL_VALUES[1:])
        self._test_margin_onchange("margin_percent", TAX_INCL_VALUES[1:])

    def test_margin_onchanges_document_tax_mode(self):
        self.product_50_margin.taxes_id = [Command.link(self.tax_default.id)]
        self.so._recompute_taxes()
        self.assertRecordValues(
            self.sol,
            [
                {
                    "price_unit": 100.0,
                    "purchase_price": 50.0,
                    "margin": 50,
                    "margin_percent": 0.5,
                    "tax_ids": [self.tax_default.id],
                    "document_tax_mode": "tax_excluded",
                }
            ],
        )
        # Price excluded taxes should not have any impact on the margin computation
        self._test_margin_onchange("margin", NO_TAX_INCL_VALUES)
        self._test_margin_onchange("margin_percent", NO_TAX_INCL_VALUES)

        # When price_include_override is not set, the tax policy depends on the document_tax_mode
        self.sol.order_id.document_tax_mode = "tax_included"
        self._test_margin_onchange("margin", TAX_INCL_VALUES)
        self._test_margin_onchange("margin_percent", TAX_INCL_VALUES)

    def _test_margin_onchange(self, fname, vals_list):
        with Form(self.so) as so_form, so_form.order_line.edit(0) as sol_form:
            for values in vals_list:
                sol_form[fname] = values[fname]
                for k, v in values.items():
                    delta = 0.02 if k != "margin_percent" else 0.01
                    self.assertAlmostEqual(
                        sol_form[k],
                        v,
                        msg=f"{k} doesn't match ({fname}: {values[fname]})",
                        delta=delta,
                    )
