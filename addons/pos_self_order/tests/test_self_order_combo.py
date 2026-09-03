# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from uuid import uuid4

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo.addons.point_of_sale.tests.common_setup_methods import setup_product_combo_items
from odoo.fields import Command
from odoo.tools import mute_logger


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderCombo(SelfOrderCommonTest):
    def test_self_order_combo(self):
        setup_product_combo_items(self)
        self.env["product.combo.item"].create(
            {
                "product_id": self.desk_organizer.id,
                "extra_price": 0,
                "combo_id": self.desk_accessories_combo.id,
            }
        )
        self.pos_config.write({
            'self_ordering_default_user_id': self.pos_admin.id,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
            'available_preset_ids': [(5, 0)],
        })
        self.pos_admin.group_ids += self.env.ref('account.group_account_invoice')
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()

        self.start_tour(self_route, "self_combo_selector")
        order = self.env['pos.order'].search([], order='id desc', limit=1)
        self.assertEqual(len(order.lines), 4, "There should be 4 order lines - 1 combo parent and 3 combo lines")
        # check that the combo lines are correctly linked to each other
        parent_line_id = self.env['pos.order.line'].search([('product_id.name', '=', 'Office Combo'), ('order_id', '=', order.id)])
        combo_line_ids = self.env['pos.order.line'].search([('product_id.name', '!=', 'Office Combo'), ('order_id', '=', order.id)])
        self.assertEqual(parent_line_id.combo_line_ids, combo_line_ids, "The combo parent should have 3 combo lines")
        self.assertEqual(parent_line_id.qty, 2, "There should be 2 combo products")
        self.assertEqual(parent_line_id.qty, combo_line_ids[0].qty, "The quantities should match with the parent")

    def test_self_order_combo_categories(self):
        setup_product_combo_items(self)
        category = self.env['pos.category'].create({'name': 'Test Category'})
        self.env["product.product"].create(
            {
                "available_in_pos": True,
                "list_price": 10,
                "name": "Test Combo",
                "type": "combo",
                'pos_categ_ids': category.ids,
                "combo_ids": self.desks_combo,
            }
        )

        self.pos_config.write({
            'self_ordering_default_user_id': self.pos_admin.id,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
            'available_preset_ids': [(5, 0)],
            'iface_available_categ_ids': category.ids,
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()

        self.start_tour(self_route, "self_combo_selector_category")

    def test_combo_price_no_free_items(self):
        """
        Regression test: when all combo sub-combos have qty_free=0, remaining_total
        (= parent list price) must be distributed proportionally to the extra lines,
        not silently dropped.
        """
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        # Sub-combo with qty_free=0 (no free items) and qty_max=1
        no_free_combo = self.env['product.combo'].create({
            'name': 'No Free Combo',
            'qty_free': 0,
            'qty_max': 1,
            'combo_item_ids': [
                Command.create({'product_id': self.cola.id, 'extra_price': 0}),
                Command.create({'product_id': self.fanta.id, 'extra_price': 0}),
            ],
        })
        combo_product = self.env['product.product'].create({
            'available_in_pos': True,
            'list_price': 10.0,
            'name': 'No Free Combo Product',
            'type': 'combo',
            'combo_ids': [Command.set([no_free_combo.id])],
            'taxes_id': False,
        })

        cola_item = no_free_combo.combo_item_ids.filtered(
            lambda i: i.product_id == self.cola
        )

        order = self.env['pos.order'].create({
            'amount_total': 0,
            'amount_paid': 0,
            'amount_tax': 0,
            'amount_return': 0,
            'company_id': self.env.company.id,
            'session_id': self.pos_config.current_session_id.id,
            'lines': [
                Command.create({
                    'product_id': combo_product.id,
                    'qty': 1,
                    'price_unit': combo_product.lst_price,
                    'price_subtotal': combo_product.lst_price,
                    'price_subtotal_incl': combo_product.lst_price,
                    'tax_ids': False,
                }),
            ],
        })

        parent_line = order.lines
        child_line = self.env['pos.order.line'].create({
            'order_id': order.id,
            'product_id': self.cola.id,
            'qty': 1,
            'price_unit': 0,
            'price_subtotal': 0,
            'price_subtotal_incl': 0,
            'tax_ids': False,
            'combo_parent_id': parent_line.id,
            'combo_item_id': cola_item.id,
        })

        order.recompute_prices()

        # base_price of the combo = min lst_price among items = min(cola.lst_price, fanta.lst_price) = 2.2
        # With qty_free=0, remaining_total = parent lst_price = 10.0 must flow into the child
        # price_unit should be: base_price + proportional_share_of_parent_price
        # = base_price + round(base_price * 10 / (base_price * 1)) = base_price + 10.0
        expected_price = no_free_combo.base_price + combo_product.lst_price
        self.assertAlmostEqual(
            child_line.price_unit, expected_price, places=2,
            msg="When qty_free=0, remaining_total must be proportionally distributed to extra lines",
        )

    def test_combo_price_free_items_multi_qty(self):
        """
        Regression test: when buying qty > 1 of a combo, free child line prices must
        equal the same per-unit amount as buying qty=1.  The parent_coef factor
        (parent_line.qty) must be applied so that original_total (which uses full qty)
        and parent_lst_price (per-unit) are on the same scale.
        """
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        free_combo = self.env['product.combo'].create({
            'name': 'Free Combo',
            'qty_free': 1,
            'qty_max': 1,
            'combo_item_ids': [
                Command.create({'product_id': self.cola.id, 'extra_price': 0}),
                Command.create({'product_id': self.fanta.id, 'extra_price': 0}),
            ],
        })
        combo_product = self.env['product.product'].create({
            'available_in_pos': True,
            'list_price': 10.0,
            'name': 'Free Combo Product',
            'type': 'combo',
            'combo_ids': [Command.set([free_combo.id])],
            'taxes_id': False,
        })

        cola_item = free_combo.combo_item_ids.filtered(
            lambda i: i.product_id == self.cola
        )

        price_unit_by_qty = {}
        for parent_qty in (1, 2):
            order = self.env['pos.order'].create({
                'amount_total': 0,
                'amount_paid': 0,
                'amount_tax': 0,
                'amount_return': 0,
                'company_id': self.env.company.id,
                'session_id': self.pos_config.current_session_id.id,
                'lines': [
                    Command.create({
                        'product_id': combo_product.id,
                        'qty': parent_qty,
                        'price_unit': combo_product.lst_price,
                        'price_subtotal': combo_product.lst_price * parent_qty,
                        'price_subtotal_incl': combo_product.lst_price * parent_qty,
                        'tax_ids': False,
                    }),
                ],
            })

            parent_line = order.lines
            child_line = self.env['pos.order.line'].create({
                'order_id': order.id,
                'product_id': self.cola.id,
                'qty': parent_qty,
                'price_unit': 0,
                'price_subtotal': 0,
                'price_subtotal_incl': 0,
                'tax_ids': False,
                'combo_parent_id': parent_line.id,
                'combo_item_id': cola_item.id,
            })

            order.recompute_prices()
            price_unit_by_qty[parent_qty] = child_line.price_unit

        self.assertAlmostEqual(
            price_unit_by_qty[1], price_unit_by_qty[2], places=2,
            msg="Child line price_unit must be the same whether buying 1 or 2 parent combos",
        )

    def test_product_dont_display_all_variants(self):
        """
        Tests that when a variant is in a combo, clicking the variant
        will only select it and not display every variant available
        for that product. It still displays them if the template is given.
        """
        size_attribute, color_attribute = self.env['product.attribute'].create([
            {
                'name': 'Size',
                'display_type': 'radio',
                'create_variant': 'always',
            },
            {
                'name': 'Color',
                'display_type': 'radio',
                'create_variant': 'no_variant',
            },
        ])
        attribute_values = self.env['product.attribute.value'].create([
            {
                'name': 'M',
                'attribute_id': size_attribute.id,
            },
            {
                'name': 'L',
                'attribute_id': size_attribute.id,
            },
            {
                'name': 'Red',
                'attribute_id': color_attribute.id,
            },
            {
                'name': 'Blue',
                'attribute_id': color_attribute.id,
            },
        ])
        # With an never and always attribute
        coke_template_never_always, coke_template_always, coke_template_never = self.env['product.template'].create([
            {
                'name': 'Coke always never',
                'available_in_pos': True,
                'list_price': 3.0,
                'attribute_line_ids': [
                    Command.create({
                        'attribute_id': size_attribute.id,
                        'value_ids': [Command.set([attribute_values[0].id, attribute_values[1].id])],
                    }),
                    Command.create({
                        'attribute_id': color_attribute.id,
                        'value_ids': [Command.set([attribute_values[2].id, attribute_values[3].id])],
                    })
                ],
            }, {
                'name': 'Coke always only',
                'available_in_pos': True,
                'list_price': 3.0,
                'attribute_line_ids': [
                    Command.create({
                        'attribute_id': size_attribute.id,
                        'value_ids': [Command.set([attribute_values[0].id, attribute_values[1].id])],
                    }),
                ],
            }, {
                'name': 'Coke never only',
                'available_in_pos': True,
                'list_price': 3.0,
                'attribute_line_ids': [
                    Command.create({
                        'attribute_id': color_attribute.id,
                        'value_ids': [Command.set([attribute_values[2].id, attribute_values[3].id])],
                    })
                ],
            },
        ])
        coke_large_always_never = coke_template_never_always.product_variant_ids[1]
        coke_large_always = coke_template_always.product_variant_ids[1]
        coke_large_never = coke_template_never.product_variant_ids[0]

        combo = self.env['product.combo'].create([{
                'name': 'Drink Combo Both',
                'combo_item_ids': [
                    Command.create({
                        'product_id': coke_large_always_never.id,
                        'extra_price': 0,
                    }),
                    Command.create({
                        'product_id': coke_large_always.id,
                        'extra_price': 0,
                    }),
                    Command.create({
                        'product_id': coke_large_never.id,
                        'extra_price': 0,
                    }),
                ],
            }
        ])

        self.env['product.product'].create({
            'available_in_pos': True,
            'list_price': 10.0,
            'name': 'Meal Combo',
            'type': 'combo',
            'combo_ids': [
                Command.set([combo.id])
            ],
        })

        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "test_product_dont_display_all_variants")

    def test_self_combo_extra_price_selection_and_confirmation(self):
        """
        Test extra price display in combo selection and confirmation.
        - Combo with qty_free=0: All items show "+ €X" price badge
        - Combo with qty_free>0: Free items have no extra badge, paid items show "Extra: €X"
        - Confirmation page displays extra prices correctly
        """

        setup_product_combo_items(self)
        self.desks_combo.qty_free = 0
        self.desks_combo.qty_max = 3

        self.desk_accessories_combo.qty_free = 1
        self.desk_accessories_combo.qty_max = 3

        self.pos_config.write({
            'self_ordering_default_user_id': self.pos_admin.id,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
            'available_preset_ids': [(5, 0)],
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()

        self.start_tour(self_route, "test_self_combo_extra_price_selection_and_confirmation")

    def test_combo_price_unit_mulitple_qty(self):
        """
        Tests that the unit price of combos ordered multiple times through the self
        order is correct. The unit prices should match for different free items, like
        it is done in the regular PoS.
        """
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        combo = self.env['product.combo'].create({
            'name': 'Combo',
            'qty_free': 2,
            'qty_max': 4,
            'combo_item_ids': [
                Command.create({'product_id': self.cola.id, 'extra_price': 0}),
                Command.create({'product_id': self.fanta.id, 'extra_price': 0}),
            ],
        })
        combo_product = self.env['product.product'].create({
            'available_in_pos': True,
            'list_price': 10.0,
            'name': 'Combo Product',
            'type': 'combo',
            'combo_ids': [Command.set([combo.id])],
            'taxes_id': False,
        })
        cola_item = combo.combo_item_ids.filtered(
            lambda i: i.product_id == self.cola
        )
        fanta_item = combo.combo_item_ids.filtered(
            lambda i: i.product_id == self.fanta
        )

        order = self.env['pos.order'].create({
            'amount_total': 0,
            'amount_paid': 0,
            'amount_tax': 0,
            'amount_return': 0,
            'company_id': self.env.company.id,
            'session_id': self.pos_config.current_session_id.id,
            'lines': [
                Command.create({
                    'product_id': combo_product.id,
                    'qty': 3,
                    'price_unit': 0,
                    'price_subtotal': 0,
                    'price_subtotal_incl': 0,
                    'tax_ids': False,
                }),
            ],
        })

        parent_line = order.lines
        child_lines = self.env['pos.order.line'].create([
            {
                'order_id': order.id,
                'product_id': self.cola.id,
                'qty': 3,
                'price_unit': 0,
                'price_subtotal': 0,
                'price_subtotal_incl': 0,
                'tax_ids': False,
                'combo_parent_id': parent_line.id,
                'combo_item_id': cola_item.id,
            },
            {
                'order_id': order.id,
                'product_id': self.fanta.id,
                'qty': 3,
                'price_unit': 0,
                'price_subtotal': 0,
                'price_subtotal_incl': 0,
                'tax_ids': False,
                'combo_parent_id': parent_line.id,
                'combo_item_id': fanta_item.id,
            },
            {
                'order_id': order.id,
                'product_id': self.fanta.id,
                'qty': 3,
                'price_unit': 0,
                'price_subtotal': 0,
                'price_subtotal_incl': 0,
                'tax_ids': False,
                'combo_parent_id': parent_line.id,
                'combo_item_id': fanta_item.id,
            }
        ])

        order.recompute_prices()
        self.assertAlmostEqual(order.amount_total, (combo.base_price + combo_product.lst_price) * order.lines[0].qty)
        self.assertEqual(child_lines[0].price_unit, child_lines[1].price_unit)

    def _process_zeroed_combo_order(self, combo_product, combo_item):
        """Send a combo order on the public self-order endpoint with every client-controlled
        price zeroed, and return the resulting order."""
        parent_uuid, child_uuid = str(uuid4()), str(uuid4())
        response = self.url_open(
            "/pos-self-order/process-order/kiosk",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "call",
                "id": str(uuid4()),
                "params": {
                    "access_token": self.pos_config.access_token,
                    "table_identifier": None,
                    "order": {
                        "id": None,
                        "session_id": self.pos_config.current_session_id.id,
                        "state": "draft",
                        "preset_id": False,
                        "amount_total": 0,
                        "amount_tax": 0,
                        "amount_paid": 0,
                        "amount_return": 0,
                        "uuid": str(uuid4()),
                        "lines": [
                            [0, 0, {
                                "uuid": parent_uuid,
                                "product_id": combo_product.id,
                                "qty": 1,
                                "price_unit": 0,
                                "price_subtotal": 0,
                                "price_subtotal_incl": 0,
                            }],
                            [0, 0, {
                                "uuid": child_uuid,
                                "product_id": combo_item.product_id.id,
                                "combo_item_id": combo_item.id,
                                "qty": 1,
                                "price_unit": 0,
                                "price_subtotal": 0,
                                "price_subtotal_incl": 0,
                            }],
                        ],
                        "relations_uuid_mapping": {
                            "pos.order.line": {
                                child_uuid: {"combo_parent_id": parent_uuid},
                            },
                        },
                    },
                },
            }),
        )
        order_id = response.json()['result']['pos.order'][0]['id']
        return self.env['pos.order'].browse(order_id)

    def test_combo_line_subtotals_are_not_trusted_from_the_frontend(self):
        """
        The self-order endpoint is public: the line subtotals it receives must never be used
        to compute the order total, otherwise a combo order can be sent with zeroed subtotals
        and get accepted as fully paid for free.
        """
        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'available_preset_ids': [(5, 0)],
            'use_presets': False,
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        # setUp puts a 15% tax on every product, so the untaxed case needs the tax removed.
        # The whole combo price is carried by the single free child line, hence an untaxed
        # total equal to the combo list price.
        for child_taxes, expected_untaxed, expected_tax in [
            (self.env['account.tax'], 10.0, 0.0),
            (self.default_tax15, 10.0, 1.5),
        ]:
            with self.subTest(taxes=child_taxes.name or 'no tax'):
                child_product = self.env['product.product'].create({
                    'available_in_pos': True,
                    'list_price': 2.2,
                    'name': 'Combo Child',
                    'taxes_id': [Command.set(child_taxes.ids)],
                })
                combo = self.env['product.combo'].create({
                    'name': 'Combo',
                    'qty_free': 1,
                    'qty_max': 1,
                    'combo_item_ids': [
                        Command.create({'product_id': child_product.id, 'extra_price': 0}),
                    ],
                })
                combo_product = self.env['product.product'].create({
                    'available_in_pos': True,
                    'list_price': 10.0,
                    'name': 'Combo Product',
                    'type': 'combo',
                    'combo_ids': [Command.set([combo.id])],
                    'taxes_id': False,
                })

                order = self._process_zeroed_combo_order(combo_product, combo.combo_item_ids)
                expected_total = expected_untaxed + expected_tax

                child_line = order.lines.filtered(lambda line: line.combo_parent_id)
                self.assertAlmostEqual(child_line.price_subtotal, expected_untaxed,
                    msg="The combo child subtotal must be recomputed server-side, not taken from the payload")
                self.assertAlmostEqual(child_line.price_subtotal_incl, expected_total,
                    msg="The combo child tax-included subtotal must be recomputed server-side")
                self.assertAlmostEqual(order.amount_total, expected_total,
                    msg="The order total must be recomputed from server-side prices")
                self.assertAlmostEqual(order.amount_tax, expected_tax,
                    msg="The order tax must be recomputed from server-side prices")
                self.assertNotEqual(order.state, 'paid',
                    msg="An unpaid combo order must not be accepted as paid")
                self.assertFalse(order.payment_ids)

    def test_combo_extra_price_is_not_trusted_from_the_frontend(self):
        """
        The extra price of a combo item is part of the child line price. It must be added back
        server-side, otherwise a zeroed payload lets the customer get the paid option for free.
        """
        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'available_preset_ids': [(5, 0)],
            'use_presets': False,
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        extra_price = 3.0
        # The child line carries the combo list price plus the extra price of the chosen item.
        # extra_price is not part of combo.base_price (which only relates to the product's
        # lst_price), so it is added on top of the prorated combo price.
        for child_taxes, tax_rate in [
            (self.env['account.tax'], 0.0),
            (self.default_tax15, 0.15),
        ]:
            with self.subTest(taxes=child_taxes.name or 'no tax'):
                child_product = self.env['product.product'].create({
                    'available_in_pos': True,
                    'list_price': 2.2,
                    'name': 'Combo Child With Extra',
                    'taxes_id': [Command.set(child_taxes.ids)],
                })
                combo = self.env['product.combo'].create({
                    'name': 'Combo With Extra',
                    'qty_free': 1,
                    'qty_max': 1,
                    'combo_item_ids': [
                        Command.create({'product_id': child_product.id, 'extra_price': extra_price}),
                    ],
                })
                combo_product = self.env['product.product'].create({
                    'available_in_pos': True,
                    'list_price': 10.0,
                    'name': 'Combo Product With Extra',
                    'type': 'combo',
                    'combo_ids': [Command.set([combo.id])],
                    'taxes_id': False,
                })

                order = self._process_zeroed_combo_order(combo_product, combo.combo_item_ids)
                expected_untaxed = combo_product.lst_price + extra_price
                expected_total = expected_untaxed * (1 + tax_rate)

                child_line = order.lines.filtered(lambda line: line.combo_parent_id)
                self.assertAlmostEqual(child_line.price_unit, expected_untaxed,
                    msg="The combo item extra price must be included in the recomputed unit price")
                self.assertAlmostEqual(child_line.price_subtotal, expected_untaxed,
                    msg="The combo item extra price must be included in the recomputed subtotal")
                self.assertAlmostEqual(child_line.price_subtotal_incl, expected_total,
                    msg="The combo item extra price must be taxed like the rest of the line")
                self.assertAlmostEqual(order.amount_total, expected_total,
                    msg="The order total must include the combo item extra price")
                self.assertNotEqual(order.state, 'paid',
                    msg="An unpaid combo order must not be accepted as paid")
                self.assertFalse(order.payment_ids)

    def _setup_kiosk_session(self):
        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'available_preset_ids': [(5, 0)],
            'use_presets': False,
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

    def _post_self_order(self, lines, relations_uuid_mapping=None):
        """Send a raw order payload on the public self-order endpoint."""
        order_uuid = str(uuid4())
        response = self.url_open(
            "/pos-self-order/process-order/kiosk",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "call",
                "id": str(uuid4()),
                "params": {
                    "access_token": self.pos_config.access_token,
                    "table_identifier": None,
                    "order": {
                        "id": None,
                        "session_id": self.pos_config.current_session_id.id,
                        "state": "draft",
                        "preset_id": False,
                        "amount_total": 0,
                        "amount_tax": 0,
                        "amount_paid": 0,
                        "amount_return": 0,
                        "uuid": order_uuid,
                        "lines": lines,
                        "relations_uuid_mapping": relations_uuid_mapping or {},
                    },
                },
            }),
        )
        return response.json(), order_uuid

    def _make_expensive_combo(self):
        expensive_product = self.env['product.product'].create({
            'available_in_pos': True,
            'list_price': 100.0,
            'name': 'Expensive Product',
            'taxes_id': False,
        })
        combo = self.env['product.combo'].create({
            'name': 'Expensive Combo',
            'qty_free': 1,
            'qty_max': 1,
            'combo_item_ids': [
                Command.create({'product_id': expensive_product.id, 'extra_price': 0}),
            ],
        })
        combo_product = self.env['product.product'].create({
            'available_in_pos': True,
            'list_price': 1.0,
            'name': 'Cheap Combo Product',
            'type': 'combo',
            'combo_ids': [Command.set([combo.id])],
            'taxes_id': False,
        })
        return expensive_product, combo, combo_product

    @mute_logger('odoo.http')
    def test_combo_parent_from_another_order_is_refused(self):
        """
        A combo child is priced from its parent line. If the parent belongs to another order it
        is never repriced with the child, so the child would keep the zero price of the payload:
        such an order must be refused.
        """
        self._setup_kiosk_session()
        expensive_product, combo, _ = self._make_expensive_combo()

        result, _ = self._post_self_order([[0, 0, {
            "uuid": str(uuid4()), "product_id": self.cola.id, "qty": 1,
            "price_unit": 0, "price_subtotal": 0, "price_subtotal_incl": 0,
        }]])
        first_order = self.env['pos.order'].browse(result['result']['pos.order'][0]['id'])
        parent_line_id = result['result']['pos.order.line'][0]['id']

        result, order_uuid = self._post_self_order([[0, 0, {
            "uuid": str(uuid4()), "product_id": expensive_product.id, "qty": 1,
            "combo_parent_id": parent_line_id,
            "combo_item_id": combo.combo_item_ids.id,
            "price_unit": 0, "price_subtotal": 0, "price_subtotal_incl": 0,
        }]])

        self.assertIn('error', result, "An order whose combo parent belongs to another order must be refused")
        self.assertFalse(self.env['pos.order'].search([('uuid', '=', order_uuid)]),
            msg="The refused order must not be created")
        self.assertFalse(first_order.lines.combo_line_ids,
            msg="No combo relation must be created towards the line of another order")

    @mute_logger('odoo.http')
    def test_forged_combo_composition_is_refused(self):
        """
        A single order made of a cheap non-combo parent and a child selling an expensive product
        through an unrelated combo item would have the child priced from the parent instead of
        from its own product: such an order must be refused.
        """
        self._setup_kiosk_session()
        expensive_product, combo, _ = self._make_expensive_combo()
        parent_uuid, child_uuid = str(uuid4()), str(uuid4())

        result, order_uuid = self._post_self_order([
            [0, 0, {
                "uuid": parent_uuid, "product_id": self.free.id, "qty": 1,
                "price_unit": 0, "price_subtotal": 0, "price_subtotal_incl": 0,
            }],
            [0, 0, {
                "uuid": child_uuid, "product_id": expensive_product.id, "qty": 1,
                "combo_item_id": combo.combo_item_ids.id,
                "price_unit": 0, "price_subtotal": 0, "price_subtotal_incl": 0,
            }],
        ], {"pos.order.line": {child_uuid: {"combo_parent_id": parent_uuid}}})

        self.assertIn('error', result, "An order with a forged combo composition must be refused")
        self.assertFalse(self.env['pos.order'].search([('uuid', '=', order_uuid)]),
            msg="The refused order must not be created")

    def test_valid_combo_order_is_still_accepted(self):
        """The check on the combo hierarchy must leave a legitimate combo order untouched."""
        self._setup_kiosk_session()
        _, combo, combo_product = self._make_expensive_combo()
        order = self._process_zeroed_combo_order(combo_product, combo.combo_item_ids)
        self.assertAlmostEqual(order.amount_total, combo_product.lst_price,
            msg="A valid combo order must be priced from the combo product")
        self.assertEqual(order.lines.filtered(lambda line: line.combo_parent_id).combo_parent_id.product_id,
            combo_product, msg="The combo child must stay linked to its parent line")

    def _create_external_combo_child(self, combo_product, combo_item):
        """Create a legitimate combo (parent + child) in its own order and return the child
        line together with the uuid it was created with, so another request can try to steal it."""
        parent_uuid, child_uuid = str(uuid4()), str(uuid4())
        result, _ = self._post_self_order([
            [0, 0, {
                "uuid": parent_uuid, "product_id": combo_product.id, "qty": 1,
                "price_unit": 0, "price_subtotal": 0, "price_subtotal_incl": 0,
            }],
            [0, 0, {
                "uuid": child_uuid, "product_id": combo_item.product_id.id,
                "combo_item_id": combo_item.id, "qty": 1,
                "price_unit": 0, "price_subtotal": 0, "price_subtotal_incl": 0,
            }],
        ], {"pos.order.line": {child_uuid: {"combo_parent_id": parent_uuid}}})
        order = self.env['pos.order'].browse(result['result']['pos.order'][0]['id'])
        child_line = order.lines.filtered(lambda line: line.combo_parent_id)
        return order, child_uuid, child_line

    @mute_logger('odoo.http')
    def test_foreign_negative_attribute_on_combo_child_is_refused(self):
        """
        Attribute extras are summed into the combo child price server-side. An attribute that
        belongs to an unrelated product (e.g. a negative-price one) must not be accepted on the
        child line, otherwise it can zero an otherwise valid combo child.
        """
        self._setup_kiosk_session()
        expensive_product, combo, combo_product = self._make_expensive_combo()

        # A negative-price attribute value that belongs to a *different* product.
        discount_attribute = self.env['product.attribute'].create({
            'name': 'Rogue Discount',
            'create_variant': 'no_variant',
            'value_ids': [Command.create({'name': 'Minus'})],
        })
        foreign_template = self.env['product.template'].create({
            'name': 'Foreign Product',
            'available_in_pos': True,
            'list_price': 0.0,
            'attribute_line_ids': [Command.create({
                'attribute_id': discount_attribute.id,
                'value_ids': [Command.set(discount_attribute.value_ids.ids)],
            })],
        })
        foreign_ptav = foreign_template.attribute_line_ids.product_template_value_ids
        foreign_ptav.price_extra = -100.0

        parent_uuid, child_uuid = str(uuid4()), str(uuid4())
        result, order_uuid = self._post_self_order([
            [0, 0, {
                "uuid": parent_uuid, "product_id": combo_product.id, "qty": 1,
                "price_unit": 0, "price_subtotal": 0, "price_subtotal_incl": 0,
            }],
            [0, 0, {
                "uuid": child_uuid, "product_id": expensive_product.id,
                "combo_item_id": combo.combo_item_ids.id, "qty": 1,
                "attribute_value_ids": [foreign_ptav.id],
                "price_unit": 0, "price_subtotal": 0, "price_subtotal_incl": 0,
            }],
        ], {"pos.order.line": {child_uuid: {"combo_parent_id": parent_uuid}}})

        self.assertIn('error', result,
            "A combo child carrying an attribute of an unrelated product must be refused")
        self.assertFalse(self.env['pos.order'].search([('uuid', '=', order_uuid)]),
            msg="The refused order must not be created")

    @mute_logger('odoo.http')
    def test_negative_combo_parent_quantity_is_refused(self):
        """A negative (or non-finite) quantity on the combo parent zeroes the combo total and
        must be refused: public self-order quantities have to be finite and strictly positive."""
        self._setup_kiosk_session()
        expensive_product, combo, combo_product = self._make_expensive_combo()
        parent_uuid, child_uuid = str(uuid4()), str(uuid4())

        result, order_uuid = self._post_self_order([
            [0, 0, {
                "uuid": parent_uuid, "product_id": combo_product.id, "qty": -1,
                "price_unit": 0, "price_subtotal": 0, "price_subtotal_incl": 0,
            }],
            [0, 0, {
                "uuid": child_uuid, "product_id": expensive_product.id,
                "combo_item_id": combo.combo_item_ids.id, "qty": 1,
                "price_unit": 0, "price_subtotal": 0, "price_subtotal_incl": 0,
            }],
        ], {"pos.order.line": {child_uuid: {"combo_parent_id": parent_uuid}}})

        self.assertIn('error', result, "A combo order with a negative parent quantity must be refused")
        self.assertFalse(self.env['pos.order'].search([('uuid', '=', order_uuid)]),
            msg="The refused order must not be created")

    @mute_logger('odoo.http')
    def test_zero_and_fractional_quantities_are_refused(self):
        """Zero, and non-finite quantities must be rejected on the public route."""
        self._setup_kiosk_session()
        for bad_qty in (0, "1", None):
            with self.subTest(qty=bad_qty):
                result, order_uuid = self._post_self_order([[0, 0, {
                    "uuid": str(uuid4()), "product_id": self.cola.id, "qty": bad_qty,
                    "price_unit": 0, "price_subtotal": 0, "price_subtotal_incl": 0,
                }]])
                self.assertIn('error', result, "A non-positive/invalid quantity must be refused")
                self.assertFalse(self.env['pos.order'].search([('uuid', '=', order_uuid)]),
                    msg="The refused order must not be created")

    @mute_logger('odoo.http')
    def test_external_child_stolen_through_relations_uuid_mapping_is_refused(self):
        """
        relations_uuid_mapping is applied generically under sudo() by the base sync_from_ui. A
        public payload that uses it to re-parent a combo child of another order onto a line of
        its own puts a foreign line in the new parent's inverse collection: _check_combo_lines
        validates that downward edge and must refuse the whole request.
        """
        self._setup_kiosk_session()
        _, combo, combo_product = self._make_expensive_combo()

        first_order, external_child_uuid, external_child = self._create_external_combo_child(
            combo_product, combo.combo_item_ids)
        original_parent = external_child.combo_parent_id

        new_parent_uuid = str(uuid4())
        result, order_uuid = self._post_self_order(
            [[0, 0, {
                "uuid": new_parent_uuid, "product_id": combo_product.id, "qty": 1,
                "price_unit": 0, "price_subtotal": 0, "price_subtotal_incl": 0,
            }]],
            {"pos.order.line": {external_child_uuid: {"combo_parent_id": new_parent_uuid}}},
        )

        self.assertIn('error', result,
            "Re-parenting a foreign combo child through relations_uuid_mapping must be refused")
        self.assertFalse(self.env['pos.order'].search([('uuid', '=', order_uuid)]),
            msg="The refused order must not be created")
        external_child.invalidate_recordset()
        self.assertEqual(external_child.combo_parent_id, original_parent,
            msg="The rolled-back request must leave the external combo child untouched")
        self.assertEqual(external_child.order_id, first_order,
            msg="The external combo child must stay on its original order")

    @mute_logger('odoo.http')
    def test_external_child_stolen_through_combo_line_ids_is_refused(self):
        """
        A raw integer combo_line_ids referencing an existing child line of another order puts
        that foreign line in the new parent's inverse collection. _check_combo_lines validates
        that downward edge and must refuse the whole request.
        """
        self._setup_kiosk_session()
        _, combo, combo_product = self._make_expensive_combo()

        first_order, _, external_child = self._create_external_combo_child(
            combo_product, combo.combo_item_ids)
        original_parent = external_child.combo_parent_id

        result, order_uuid = self._post_self_order([[0, 0, {
            "uuid": str(uuid4()), "product_id": combo_product.id, "qty": 1,
            "combo_line_ids": [external_child.id],
            "price_unit": 0, "price_subtotal": 0, "price_subtotal_incl": 0,
        }]])

        self.assertIn('error', result,
            "Re-parenting a foreign combo child through raw combo_line_ids must be refused")
        self.assertFalse(self.env['pos.order'].search([('uuid', '=', order_uuid)]),
            msg="The refused order must not be created")
        external_child.invalidate_recordset()
        self.assertEqual(external_child.combo_parent_id, original_parent,
            msg="The rolled-back request must leave the external combo child untouched")
        self.assertEqual(external_child.order_id, first_order,
            msg="The external combo child must stay on its original order")
