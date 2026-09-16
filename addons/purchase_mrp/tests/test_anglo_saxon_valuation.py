from odoo.exceptions import UserError
from odoo.fields import Command, Date, Datetime
from odoo.tests import Form, tagged
from odoo.tools import float_is_zero, mute_logger

from odoo.addons.stock_account.tests.common import TestStockValuationCommon


@tagged("post_install", "-at_install")
class TestAngloSaxonValuationPurchaseMRP(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a, cls.vendor01 = cls.env["res.partner"].create(
            [{"name": "Vendor A"}, {"name": "Vendor 01"}]
        )
        cls.stock_input_account = cls.category_avco_auto.account_stock_variation_id
        cls.stock_valuation_account = (
            cls.category_avco_auto.property_stock_valuation_account_id
        )
        cls.product_a, cls.product_b = cls.env["product.product"].create(
            [
                {"name": "Product A", "is_storable": True},
                {"name": "Product B", "is_storable": True},
            ]
        )

    def _valued_moves(self, product):
        return (
            self.env["stock.move"]
            .search([("product_id", "=", product.id), ("state", "=", "done")])
            .sorted("id")
            .filtered("is_valued")
        )

    def _valued_amounts(self, product):
        return [
            -move.value if move.is_out else move.value
            for move in self._valued_moves(product)
        ]

    def test_kit_anglo_saxo_price_diff(self):
        kit, compo01, compo02 = self.env["product.product"].create(
            [
                {
                    "name": name,
                    "standard_price": price,
                    "is_storable": True,
                    "categ_id": self.category_avco_auto.id,
                }
                for name, price in [("Kit", 0), ("Compo 01", 10), ("Compo 02", 20)]
            ]
        )

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit.product_tmpl_id.id,
                "type": "phantom",
                "bom_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": p.id,
                            "product_qty": 1,
                        },
                    )
                    for p in [compo01, compo02]
                ],
            }
        )
        kit.button_bom_cost()

        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.vendor01
        with po_form.line_ids.new() as pol_form:
            pol_form.product_id = kit
            pol_form.price_unit = 100
        po = po_form.save()
        po.action_confirm()

        po.picking_ids.button_validate()

        invoice = po.create_invoice()
        invoice.invoice_date = Date.today()
        invoice.action_post()

        valued = po.line_ids.move_ids.filtered("is_valued")
        self.assertEqual(
            len(valued),
            2,
            "One valued move per kit component should carry the price difference",
        )
        self.assertEqual(
            sum(valued.mapped("value")),
            100,
            "Should be the standard price of both components",
        )

        input_amls = self.env["account.move.line"].search(
            [("account_id", "=", self.stock_input_account.id)]
        )
        self.assertEqual(sum(input_amls.mapped("balance")), 0)

    def test_buy_deliver_and_return_kit_with_auto_avco_components(self):
        stock_location = self.env["stock.location"].search(
            [
                ("company_id", "=", self.env.company.id),
                ("name", "=", "Stock"),
            ]
        )
        customer_location = self.env.ref("stock.stock_location_customers")
        type_out = self.env["stock.picking.type"].search(
            [("company_id", "=", self.env.company.id), ("name", "=", "Delivery Orders")]
        )
        uom_unit = self.env.ref("uom.product_uom_unit")
        uom_litre = self.env.ref("uom.product_uom_litre")

        component01, component02 = self.env["product.product"].create(
            [
                {
                    "name": "Component %s" % name,
                    "is_storable": True,
                    "categ_id": self.category_avco_auto.id,
                    "uom_id": uom_litre.id,
                }
                for name in ["01", "02"]
            ]
        )

        kit = self.env["product.product"].create(
            {
                "name": "Super Kit",
                "type": "consu",
                "uom_id": uom_unit.id,
            }
        )

        bom_kit = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit.product_tmpl_id.id,
                "type": "phantom",
                "bom_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": component01.id,
                            "product_qty": 1,
                            "cost_share": 25,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": component02.id,
                            "product_qty": 1,
                            "cost_share": 75,
                        },
                    ),
                ],
            }
        )

        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.vendor01
        with po_form.line_ids.new() as pol_form:
            pol_form.product_id = kit
            pol_form.price_unit = 100
            pol_form.tax_ids.clear()
        po = po_form.save()
        po.action_confirm()

        receipt = po.picking_ids
        receipt.move_line_ids.quantity = 1
        receipt.button_validate()

        self.assertEqual(receipt.state, "done")
        self.assertEqual(receipt.move_line_ids.product_id, component01 | component02)
        self.assertEqual(po.line_ids.qty_transferred, 1)
        self.assertEqual(self._valued_amounts(component01), [25])
        self.assertEqual(self._valued_amounts(component02), [75])

        delivery = self.env["stock.picking"].create(
            {
                "picking_type_id": type_out.id,
                "location_id": stock_location.id,
                "location_dest_id": customer_location.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": kit.id,
                            "product_uom_id": kit.uom_id.id,
                            "product_uom_qty": 1.0,
                            "location_id": stock_location.id,
                            "location_dest_id": customer_location.id,
                        },
                    )
                ],
            }
        )
        delivery.action_confirm()
        delivery.move_ids.move_line_ids.quantity = 1
        delivery.button_validate()

        self.assertEqual(self._valued_amounts(component01), [25, -25])
        self.assertEqual(self._valued_amounts(component02), [75, -75])

        with mute_logger("odoo.tests.form.onchange"):
            with Form(bom_kit) as kit_form:
                with kit_form.bom_line_ids.edit(0) as line:
                    line.cost_share = 30
                with kit_form.bom_line_ids.edit(1) as line:
                    line.cost_share = 70

        wizard_form = Form(
            self.env["stock.return.picking"].with_context(
                active_id=delivery.id, active_model="stock.picking"
            )
        )
        wizard = wizard_form.save()
        wizard.product_return_moves.quantity = 1
        action = wizard.action_create_returns()
        return_picking = self.env["stock.picking"].browse(action["res_id"])
        return_picking.move_ids.move_line_ids.quantity = 1
        return_picking.button_validate()

        self.assertEqual(self._valued_amounts(component01), [25, -25, 25])
        self.assertEqual(self._valued_amounts(component02), [75, -75, 75])

    def test_valuation_multicurrency_with_kits(self):
        kit, cmp = self.env["product.product"].create(
            [
                {
                    "name": name,
                    "standard_price": 0,
                    "is_storable": True,
                    "categ_id": self.category_avco_auto.id,
                }
                for name in ["Kit", "Cmp"]
            ]
        )

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit.product_tmpl_id.id,
                "type": "phantom",
                "bom_line_ids": [(0, 0, {"product_id": cmp.id, "product_qty": 5})],
            }
        )

        usd = self.env.ref("base.USD")
        eur = self.env.ref("base.EUR")
        eur.active = True
        self.env["res.currency.rate"].create(
            {"name": Datetime.today(), "currency_id": usd.id, "rate": 1}
        )
        self.env["res.currency.rate"].create(
            {"name": Datetime.today(), "currency_id": eur.id, "rate": 2}
        )

        self.vendor01.property_purchase_currency_id = eur
        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.vendor01
        self.assertEqual(po_form.currency_id, eur)
        with po_form.line_ids.new() as pol_form:
            pol_form.product_id = kit
            pol_form.price_unit = 100
        po = po_form.save()
        po.action_confirm()

        po.picking_ids.button_validate()

        bill = po.create_invoice()
        bill.invoice_date = Date.today()
        bill.action_post()

        valued_move = po.line_ids.move_ids.filtered("is_valued").check_singleton()
        self.assertEqual(valued_move.value, 50)

        valuation_aml = self.env["account.move.line"].search(
            [("account_id", "=", self.stock_valuation_account.id)]
        )
        self.assertEqual(valuation_aml.amount_currency, 100)
        self.assertEqual(valuation_aml.balance, 50)

    def test_multicurrency_kit_different_uom_categories(self):
        eur = self.env.ref("base.EUR")

        uom_unit = self.env.ref("uom.product_uom_unit")
        uom_meter = self.env.ref("uom.product_uom_meter")

        kit, component = self.env["product.product"].create(
            [
                {
                    "name": "Kit multi UoM",
                    "is_storable": True,
                    "uom_id": uom_unit.id,
                    "categ_id": self.category_avco_auto.id,
                },
                {
                    "name": "Component meter",
                    "is_storable": True,
                    "uom_id": uom_meter.id,
                    "categ_id": self.category_avco_auto.id,
                },
            ]
        )

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit.product_tmpl_id.id,
                "product_uom_id": uom_unit.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": component.id,
                            "product_qty": 1.0,
                            "product_uom_id": uom_meter.id,
                        }
                    )
                ],
            }
        )

        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "currency_id": eur.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": kit.id,
                            "product_qty": 1.0,
                            "product_uom_id": kit.uom_id.id,
                            "price_unit": 100.0,
                        }
                    )
                ],
            }
        )
        po.action_confirm()

        receipt = po.picking_ids
        receipt.button_validate()

        self.assertEqual(receipt.move_ids.state, "done")

    def test_fifo_cost_adjust_mo_quantity(self):
        self.product_a.categ_id = self.env["product.category"].create(
            {
                "name": "FIFO",
                "property_cost_method": "fifo",
                "property_valuation": "real_time",
            }
        )

        purchase_order = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 10,
                            "price_unit": 100,
                        },
                    )
                ],
            }
        )
        purchase_order.action_confirm()
        purchase_order.picking_ids[0].button_validate()

        manufacturing_order = self.env["mrp.production"].create(
            {
                "product_id": self.product_b.id,
                "product_qty": 1,
                "move_raw_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_a.id,
                            "product_uom_qty": 100,
                        },
                    )
                ],
            }
        )
        manufacturing_order.action_confirm()
        manufacturing_order.move_raw_ids.write(
            {
                "quantity": 100,
                "picked": True,
            }
        )
        manufacturing_order.button_mark_done()
        manufacturing_order.action_toggle_is_locked()
        manufacturing_order.move_raw_ids.quantity = 1

        self.assertEqual(self.product_a.standard_price, 100)

    def test_average_cost_unbuild_valuation(self):
        def make_purchase_and_production(product_ids, price_units):
            purchase_orders = self.env["purchase.order"].create(
                [
                    {
                        "partner_id": self.partner_a.id,
                        "line_ids": [
                            (
                                0,
                                0,
                                {
                                    "product_id": prod_id,
                                    "product_qty": 2,
                                    "price_unit": price_unit,
                                },
                            )
                        ],
                    }
                    for prod_id, price_unit in zip(
                        product_ids, price_units, strict=False
                    )
                ]
            )
            purchase_orders.action_confirm()
            purchase_orders.picking_ids.move_ids.quantity = 2
            purchase_orders.picking_ids.button_validate()
            production_form = Form(self.env["mrp.production"])
            production_form.product_id = final_product
            production_form.bom_id = final_product_bom
            production_form.product_qty = 1
            production = production_form.save()
            production.action_confirm()
            mo_form = Form(production)
            mo_form.qty_producing = 1
            production = mo_form.save()
            production._post_inventory()
            production.button_mark_done()
            return production

        cost_of_production_account = self.env["account.account"].search(
            [
                ("name", "=", "Cost of Production"),
                ("company_ids", "in", self.env.company.id),
            ],
            limit=1,
        )
        self.category_avco_auto.property_stock_account_production_cost_id = (
            cost_of_production_account.id
        )
        final_product = self.env["product.product"].create(
            {
                "name": "final product",
                "is_storable": True,
                "standard_price": 0,
                "categ_id": self.category_avco_auto.id,
                "route_ids": [
                    (
                        6,
                        0,
                        self.env["stock.route"]
                        .search([("name", "=", "Manufacture")], limit=1)
                        .ids,
                    )
                ],
            }
        )
        comp_1, comp_2 = self.env["product.product"].create(
            [
                {
                    "name": name,
                    "is_storable": True,
                    "standard_price": 0,
                    "categ_id": self.category_avco_auto.id,
                    "route_ids": [
                        (
                            4,
                            self.env["stock.route"]
                            .search([("name", "=", "Buy")], limit=1)
                            .id,
                        )
                    ],
                }
                for name in ("comp_1", "comp_2")
            ]
        )
        final_product_bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": final_product.product_tmpl_id.id,
                "type": "normal",
                "bom_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": comp_prod_id,
                            "product_qty": 2,
                        },
                    )
                    for comp_prod_id in (comp_1.id, comp_2.id)
                ],
            }
        )
        production_1 = make_purchase_and_production([comp_1.id, comp_2.id], [50, 40])
        make_purchase_and_production([comp_1.id, comp_2.id], [55, 45])
        action = production_1.button_unbuild()
        wizard = Form(self.env[action["res_model"]].with_context(action["context"]))
        wizard.product_qty = 1
        wizard = wizard.save()
        wizard.action_validate()
        self.assertTrue(
            float_is_zero(
                sum(
                    self.env["account.move.line"]
                    .search(
                        [
                            ("account_id", "=", cost_of_production_account.id),
                            (
                                "product_id",
                                "in",
                                (final_product.id, comp_1.id, comp_2.id),
                            ),
                        ]
                    )
                    .mapped("balance")
                ),
                precision_rounding=self.env.company.currency_id.rounding,
            )
        )

    def test_avco_purchase_nested_kit_explode_cost_share(self):
        avco_category = self.env["product.category"].create(
            {
                "name": "AVCO",
                "property_cost_method": "average",
                "property_valuation": "real_time",
            }
        )
        component01, component02, component03, component04, component05 = self.env[
            "product.product"
        ].create(
            [
                {
                    "name": "Component %s" % name,
                    "categ_id": avco_category.id,
                }
                for name in ("01", "02", "03", "04", "05")
            ]
        )

        giga_kit, super_kit, kit, sub_kit, phantom_kit, triple_kit = self.env[
            "product.product"
        ].create(
            [
                {
                    "name": name,
                }
                for name in (
                    "Giga Kit",
                    "Super Kit",
                    "Kit",
                    "Sub Kit",
                    "Phantom Kit",
                    "Triple Kit",
                )
            ]
        )

        self.env["mrp.bom"].create(
            [
                {
                    "product_tmpl_id": giga_kit.product_tmpl_id.id,
                    "type": "phantom",
                    "bom_line_ids": [
                        Command.create(
                            {
                                "product_id": component01.id,
                                "product_qty": 1,
                                "cost_share": 0,
                            }
                        ),
                        Command.create(
                            {
                                "product_id": super_kit.id,
                                "product_qty": 1,
                                "cost_share": 100,
                            }
                        ),
                    ],
                },
                {
                    "product_tmpl_id": super_kit.product_tmpl_id.id,
                    "type": "phantom",
                    "bom_line_ids": [
                        Command.create(
                            {
                                "product_id": component02.id,
                                "product_qty": 1,
                                "cost_share": 10,
                            }
                        ),
                        Command.create(
                            {"product_id": kit.id, "product_qty": 1, "cost_share": 60}
                        ),
                        Command.create(
                            {
                                "product_id": sub_kit.id,
                                "product_qty": 1,
                                "cost_share": 20,
                            }
                        ),
                        Command.create(
                            {
                                "product_id": phantom_kit.id,
                                "product_qty": 1,
                                "cost_share": 0,
                            }
                        ),
                        Command.create(
                            {
                                "product_id": triple_kit.id,
                                "product_qty": 2,
                                "cost_share": 10,
                            }
                        ),
                    ],
                },
                {
                    "product_tmpl_id": kit.product_tmpl_id.id,
                    "type": "phantom",
                    "bom_line_ids": [
                        Command.create(
                            {
                                "product_id": component02.id,
                                "product_qty": 1,
                                "cost_share": 25,
                            }
                        ),
                        Command.create(
                            {
                                "product_id": component03.id,
                                "product_qty": 1,
                                "cost_share": 25,
                            }
                        ),
                        Command.create(
                            {
                                "product_id": sub_kit.id,
                                "product_qty": 1,
                                "cost_share": 50,
                            }
                        ),
                    ],
                },
                {
                    "product_tmpl_id": sub_kit.product_tmpl_id.id,
                    "type": "phantom",
                    "bom_line_ids": [
                        Command.create(
                            {
                                "product_id": component04.id,
                                "product_qty": 1,
                                "cost_share": 0,
                            }
                        ),
                        Command.create(
                            {
                                "product_id": component05.id,
                                "product_qty": 1,
                                "cost_share": 0,
                            }
                        ),
                    ],
                },
                {
                    "product_tmpl_id": phantom_kit.product_tmpl_id.id,
                    "type": "phantom",
                    "bom_line_ids": [
                        Command.create(
                            {
                                "product_id": component05.id,
                                "product_qty": 1,
                                "cost_share": 100,
                            }
                        ),
                    ],
                },
                {
                    "product_tmpl_id": triple_kit.product_tmpl_id.id,
                    "type": "phantom",
                    "bom_line_ids": [
                        Command.create(
                            {
                                "product_id": component01.id,
                                "product_qty": 1,
                                "cost_share": 0,
                            }
                        ),
                        Command.create(
                            {
                                "product_id": component02.id,
                                "product_qty": 1,
                                "cost_share": 0,
                            }
                        ),
                        Command.create(
                            {
                                "product_id": component03.id,
                                "product_qty": 2,
                                "cost_share": 0,
                            }
                        ),
                    ],
                },
            ]
        )
        vendor = self.env["res.partner"].create({"name": "Super vendor"})
        purchase_orders = self.env["purchase.order"].create(
            [
                {
                    "partner_id": vendor.id,
                    "line_ids": [
                        Command.create(
                            {
                                "product_id": super_kit.id,
                                "product_qty": qty,
                                "price_unit": 1000,
                            }
                        ),
                    ],
                }
                for qty in [1, 3]
            ]
        )
        purchase_orders.action_confirm()

        self.assertEqual(
            [
                sum(moves.mapped("cost_share"))
                for moves in purchase_orders.line_ids.move_ids.grouped(
                    "picking_id"
                ).values()
            ],
            [100, 100],
        )
        receipts = purchase_orders.picking_ids
        # Name the receipts by the order they belong to, not by position:
        # `picking_ids` gains the backorder in the middle of its own ordering,
        # so `receipts[2]` was the second order's receipt -- already done -- and
        # the backorder was left `assigned`, valued at 0.
        purchase_orders[1].picking_ids.move_line_ids.filtered(
            lambda ml: ml.product_id.id == component01.id
        ).quantity = 3
        res = receipts.button_validate()
        self.env[res["res_model"]].with_context(res["context"]).create({}).process()
        receipts = purchase_orders.picking_ids
        receipts.filtered(
            lambda picking: picking.state not in ("done", "cancel")
        ).button_validate()

        self.assertEqual(
            sum(purchase_orders[0].line_ids.move_ids.mapped("cost_share")), 100.0
        )
        moves = purchase_orders.line_ids.move_ids.sorted(
            lambda m: (m.picking_id.id, m.cost_share)
        )
        cost_share_values = moves.mapped("cost_share")
        expected_cost_share = [
            0.0,
            3.3333333333333,
            3.3333333333333,
            3.3333333333333,
            10.0,
            10.0,
            10.0,
            15.0,
            15.0,
            15.0,
            15.0,
            0.0,
            3.3333333333333,
            3.3333333333333,
            3.3333333333333,
            10.0,
            10.0,
            10.0,
            15.0,
            15.0,
            15.0,
            15.0,
            3.3333333333333,
        ]
        for actual, expected in zip(
            cost_share_values, expected_cost_share, strict=True
        ):
            self.assertAlmostEqual(actual, expected)

        expected_values = [
            {"product_id": component01.id, "value": 33.33},
            {"product_id": component02.id, "value": 33.33},
            {"product_id": component02.id, "value": 100.0},
            {"product_id": component02.id, "value": 150.0},
            {"product_id": component03.id, "value": 33.33},
            {"product_id": component03.id, "value": 150.0},
            {"product_id": component04.id, "value": 100.0},
            {"product_id": component04.id, "value": 150.0},
            {"product_id": component05.id, "value": 0.0},
            {"product_id": component05.id, "value": 100.0},
            {"product_id": component05.id, "value": 150.0},
            {"product_id": component01.id, "value": 50.0},
            {"product_id": component02.id, "value": 100.0},
            {"product_id": component02.id, "value": 300.0},
            {"product_id": component02.id, "value": 450.0},
            {"product_id": component03.id, "value": 100.0},
            {"product_id": component03.id, "value": 450.0},
            {"product_id": component04.id, "value": 300.0},
            {"product_id": component04.id, "value": 450.0},
            {"product_id": component05.id, "value": 0.0},
            {"product_id": component05.id, "value": 300.0},
            {"product_id": component05.id, "value": 450.0},
            {"product_id": component01.id, "value": 50.0},
        ]

        self.assertRecordValues(
            # `m.picking_id.id`, not `m.picking_id`: `BaseModel.__lt__` is strict
            # subset, so two distinct singletons are incomparable and `sorted`
            # silently keeps the input order. The sort twenty lines above already
            # spells it with `.id`.
            receipts.move_ids.sorted(
                lambda m: (m.picking_id.id, m.product_id.id, m.cost_share)
            ),
            expected_values,
        )

        move_form = Form(
            self.env["account.move"].with_context(default_move_type="in_invoice")
        )
        move_form.purchase_vendor_bill_id = self.env["purchase.bill.match"].browse(
            -purchase_orders[0].id
        )
        move_form.invoice_date = Datetime.today()
        move = move_form.save()
        move.action_post()
        self.assertRecordValues(
            receipts.move_ids.sorted(
                lambda m: (m.picking_id.id, m.product_id.id, m.cost_share)
            ),
            expected_values,
        )

    def test_kit_bom_cost_share_constraint_with_variants(self):
        avco_category = self.env["product.category"].create(
            {
                "name": "AVCO",
                "property_cost_method": "average",
                "property_valuation": "real_time",
            }
        )
        attributes = self.env["product.attribute"].create(
            [{"name": name} for name in ("Size", "Color")]
        )
        attributes_values = (
            (attributes[0], ("S", "M")),
            (attributes[1], ("Blue", "Red")),
        )
        self.env["product.attribute.value"].create(
            [
                {"name": name, "attribute_id": attribute.id}
                for attribute, names in attributes_values
                for name in names
            ]
        )
        product_template = self.env["product.template"].create(
            {
                "name": "lovely product",
                "is_storable": True,
            }
        )
        size_attribute_lines, color_attribute_lines = self.env[
            "product.template.attribute.line"
        ].create(
            [
                {
                    "product_tmpl_id": product_template.id,
                    "attribute_id": attribute.id,
                    "value_ids": [Command.set(attribute.value_ids.ids)],
                }
                for attribute in attributes
            ]
        )
        self.assertEqual(product_template.product_variant_count, 4)
        c1, c2, c3 = self.env["product.product"].create(
            [{"name": f"Comp {i + 1}", "categ_id": avco_category.id} for i in range(3)]
        )

        with self.assertRaises(UserError):
            self.env["mrp.bom"].create(
                {
                    "product_tmpl_id": product_template.id,
                    "product_uom_id": product_template.uom_id.id,
                    "product_qty": 1.0,
                    "type": "phantom",
                    "bom_line_ids": [
                        Command.create(
                            {
                                "product_id": c1.id,
                                "product_qty": 1,
                                "cost_share": 25,
                                "bom_product_template_attribute_value_ids": [
                                    Command.link(
                                        size_attribute_lines.product_template_value_ids[
                                            0
                                        ].id
                                    )
                                ],
                            }
                        ),
                        Command.create(
                            {
                                "product_id": c2.id,
                                "product_qty": 1,
                                "cost_share": 75,
                                "bom_product_template_attribute_value_ids": [
                                    Command.link(
                                        size_attribute_lines.product_template_value_ids[
                                            1
                                        ].id
                                    )
                                ],
                            }
                        ),
                    ],
                }
            )

        with self.assertRaises(UserError):
            self.env["mrp.bom"].create(
                {
                    "product_tmpl_id": product_template.id,
                    "product_uom_id": product_template.uom_id.id,
                    "product_qty": 1.0,
                    "type": "phantom",
                    "bom_line_ids": [
                        Command.create(
                            {
                                "product_id": c1.id,
                                "product_qty": 1,
                                "cost_share": 25,
                                "bom_product_template_attribute_value_ids": [
                                    Command.link(
                                        color_attribute_lines.product_template_value_ids[
                                            0
                                        ].id
                                    )
                                ],
                            }
                        ),
                        Command.create(
                            {
                                "product_id": c2.id,
                                "product_qty": 1,
                                "cost_share": 30,
                                "bom_product_template_attribute_value_ids": [
                                    Command.link(
                                        color_attribute_lines.product_template_value_ids[
                                            1
                                        ].id
                                    )
                                ],
                            }
                        ),
                        Command.create(
                            {"product_id": c3.id, "product_qty": 1, "cost_share": 75}
                        ),
                    ],
                }
            )

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product_template.id,
                "product_uom_id": product_template.uom_id.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create(
                        {"product_id": c1.id, "product_qty": 1, "cost_share": 100}
                    ),
                    Command.create(
                        {"product_id": c2.id, "product_qty": 0, "cost_share": 100}
                    ),
                ],
            }
        )

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product_template.id,
                "product_uom_id": product_template.uom_id.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": c1.id,
                            "product_qty": 1,
                            "cost_share": 35,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    size_attribute_lines.product_template_value_ids[
                                        0
                                    ].id
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": c1.id,
                            "product_qty": 1,
                            "cost_share": 65,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    size_attribute_lines.product_template_value_ids[
                                        0
                                    ].id
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {"product_id": c2.id, "product_qty": 1, "cost_share": 0}
                    ),
                ],
            }
        )

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product_template.id,
                "product_uom_id": product_template.uom_id.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": c1.id,
                            "product_qty": 1,
                            "cost_share": 30,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    size_attribute_lines.product_template_value_ids[
                                        0
                                    ].id
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": c1.id,
                            "product_qty": 1,
                            "cost_share": 15,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    size_attribute_lines.product_template_value_ids[
                                        1
                                    ].id
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": c2.id,
                            "product_qty": 1,
                            "cost_share": 15,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    size_attribute_lines.product_template_value_ids[
                                        1
                                    ].id
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {"product_id": c2.id, "product_qty": 1, "cost_share": 70}
                    ),
                ],
            }
        )

        product_template.product_variant_ids[1:3].action_archive()
        self.assertEqual(product_template.product_variant_count, 2)

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product_template.id,
                "product_uom_id": product_template.uom_id.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": c1.id,
                            "product_qty": 1,
                            "cost_share": 30,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    size_attribute_lines.product_template_value_ids[
                                        0
                                    ].id
                                ),
                                Command.link(
                                    color_attribute_lines.product_template_value_ids[
                                        0
                                    ].id
                                ),
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": c2.id,
                            "product_qty": 1,
                            "cost_share": 30,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    size_attribute_lines.product_template_value_ids[
                                        1
                                    ].id
                                ),
                                Command.link(
                                    color_attribute_lines.product_template_value_ids[
                                        1
                                    ].id
                                ),
                            ],
                        }
                    ),
                    Command.create(
                        {"product_id": c3.id, "product_qty": 1, "cost_share": 70}
                    ),
                ],
            }
        )

    def test_kit_cost_share_variant_and_optional_lines(self):
        avco_category = self.env["product.category"].create(
            {
                "name": "AVCO",
                "property_cost_method": "average",
                "property_valuation": "real_time",
            }
        )
        size_attribute = self.env["product.attribute"].create({"name": "Size"})
        self.env["product.attribute.value"].create(
            [
                {"name": name, "attribute_id": size_attribute.id}
                for name in ("S", "M", "L")
            ]
        )
        product_template = self.env["product.template"].create(
            {
                "name": "Lovely product",
                "is_storable": True,
            }
        )
        attribute_lines = self.env["product.template.attribute.line"].create(
            {
                "product_tmpl_id": product_template.id,
                "attribute_id": size_attribute.id,
                "value_ids": [Command.set(size_attribute.value_ids.ids)],
            }
        )
        self.assertEqual(product_template.product_variant_count, 3)
        c1, c2, c3, c4, c5, c6 = self.env["product.product"].create(
            [
                {
                    "name": f"Comp {i + 1}",
                    "categ_id": avco_category.id,
                }
                for i in range(6)
            ]
        )
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product_template.id,
                "product_uom_id": product_template.uom_id.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": c1.id,
                            "product_qty": 1,
                            "cost_share": 25,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    attribute_lines[0].product_template_value_ids[0].id
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": c2.id,
                            "product_qty": 1,
                            "cost_share": 75,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    attribute_lines[0].product_template_value_ids[0].id
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": c3.id,
                            "product_qty": 1,
                            "cost_share": 100,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    attribute_lines[0].product_template_value_ids[1].id
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": c4.id,
                            "product_qty": 1,
                            "cost_share": 0,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    attribute_lines[0].product_template_value_ids[2].id
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {"product_id": c5.id, "product_qty": 1, "cost_share": 0}
                    ),
                    Command.create(
                        {"product_id": c6.id, "product_qty": 0, "cost_share": 100}
                    ),
                ],
            }
        )
        vendor = self.env["res.partner"].create({"name": "Super vendor"})
        purchase_order = self.env["purchase.order"].create(
            {
                "partner_id": vendor.id,
                "line_ids": [
                    Command.create(
                        {"product_id": variant.id, "product_qty": 1, "price_unit": 1000}
                    )
                    for variant in product_template.product_variant_ids
                ],
            }
        )
        purchase_order.action_confirm()

        self.assertEqual(
            sum(purchase_order.line_ids.move_ids.mapped("cost_share")),
            300.0,
            "There are 3 lines and each line should be associated with a total cost_share of 100%",
        )
        self.assertRecordValues(
            purchase_order.line_ids.move_ids.sorted(lambda m: m.product_id.id),
            [
                {"product_id": c1.id, "cost_share": 25.0},
                {"product_id": c2.id, "cost_share": 75.0},
                {"product_id": c3.id, "cost_share": 100.0},
                {"product_id": c4.id, "cost_share": 50.0},
                {"product_id": c5.id, "cost_share": 0.0},
                {"product_id": c5.id, "cost_share": 0.0},
                {"product_id": c5.id, "cost_share": 50.0},
                {"product_id": c6.id, "cost_share": 0.0},
                {"product_id": c6.id, "cost_share": 0.0},
                {"product_id": c6.id, "cost_share": 0.0},
            ],
        )

        receipt = purchase_order.picking_ids
        receipt.button_validate()

        self.assertRecordValues(
            receipt.move_ids.sorted(
                lambda m: (m.purchase_line_id.product_id.id, m.product_id.id)
            ),
            [
                {"product_id": c1.id, "value": 250.0},
                {"product_id": c2.id, "value": 750.0},
                {"product_id": c5.id, "value": 0.0},
                {"product_id": c6.id, "value": 0.0},
                {"product_id": c3.id, "value": 1000.0},
                {"product_id": c5.id, "value": 0.0},
                {"product_id": c6.id, "value": 0.0},
                {"product_id": c4.id, "value": 500.0},
                {"product_id": c5.id, "value": 500.0},
                {"product_id": c6.id, "value": 0.0},
            ],
        )

    def test_kit_components_cost_distribution(self):
        kit, *components = self.env["product.product"].create(
            [
                {
                    "name": "Product %s" % i,
                    "is_storable": True,
                    "categ_id": self.category_avco_auto.id,
                }
                for i in range(7)
            ]
        )
        self.env["mrp.bom"].create(
            [
                {
                    "product_tmpl_id": kit.product_tmpl_id.id,
                    "type": "phantom",
                    "bom_line_ids": [
                        *[Command.create({"product_id": p.id}) for p in components],
                    ],
                }
            ]
        )

        kit_price = 100
        purchase_order = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": kit.id,
                            "product_qty": 1,
                            "price_unit": kit_price,
                        }
                    )
                ],
            }
        )
        purchase_order.action_confirm()
        receipt = purchase_order.picking_ids
        receipt.button_validate()
        self.assertRecordValues(
            receipt.move_ids,
            [{"value": val} for val in (16.67, 16.67, 16.67, 16.67, 16.67, 16.67)],
        )

        self._create_bill(kit, 1, 100)
        correction_data = receipt.move_ids.company_id.action_close_stock_valuation()
        closing_move = self.env["account.move"].browse(correction_data["res_id"])
        valuation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_valuation
        )
        variation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_variation
        )
        self.assertRecordValues(
            valuation_aml | variation_aml,
            [
                {
                    "account_id": self.account_stock_valuation.id,
                    "debit": 0.02,
                    "credit": 0,
                },
                {
                    "account_id": self.account_stock_variation.id,
                    "debit": 0,
                    "credit": 0.02,
                },
            ],
        )
