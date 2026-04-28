# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo.addons.point_of_sale.tests.common_setup_methods import setup_product_combo_items
from odoo.fields import Command


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
