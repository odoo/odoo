# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo.addons.point_of_sale.tests.common_setup_methods import setup_product_combo_items
from odoo.fields import Command
from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController


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

    def test_self_order_combo_compute_backend(self):
        """
        Verify that the total is computed correctly when we have a combo
        and the _verify_line_price is called. This function is called to
        make sure the backend and frontend prices are in sync.
        """
        setup_product_combo_items(self)
        self.pos_config.with_user(self.pos_user).open_ui()
        order = self.env['pos.order'].create({
            'config_id': self.pos_config.id,
            'session_id': self.pos_config.current_session_id.id,
            'amount_paid': 0.0,
            'amount_total': 0.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
        })
        product_1, product_2 = self.env["product.product"].create([
            {
                "name": "Combo Product",
                "is_storable": True,
                "available_in_pos": True,
                "list_price": 20,
            }, {
                "name": "Combo Product 2",
                "is_storable": True,
                "available_in_pos": True,
                "list_price": 30,
            },
        ])
        combo = self.env["product.combo"].create(
            {
                "name": "Desks Combo",
                "qty_free": 2,
                "qty_max": 3,
                "combo_item_ids": [
                    Command.create({
                        "product_id": product_1.id,
                        "extra_price": 0,
                    }),
                    Command.create({
                        "product_id": product_2.id,
                        "extra_price": 2,
                    }),
                ],
            }
        )
        combo_product = self.env["product.product"].create(
            {
                "available_in_pos": True,
                "list_price": 30,
                "name": "Combo",
                "type": "combo",
                "uom_id": self.env.ref("uom.product_uom_unit").id,
                "combo_ids": [
                    Command.set([combo.id])
                ],
            }
        )
        desk_combo_line = self.env['pos.order.line'].create({
            'order_id': order.id,
            'product_id': combo_product.id,
            'qty': 1,
            'price_unit': 30.0,
            'price_subtotal': 0,
            'price_subtotal_incl': 0,
            'combo_line_ids': [
                Command.create({
                    'order_id': order.id,
                    'product_id': product_1.id,
                    'qty': 2,
                    'price_unit': 20.0,
                    'price_subtotal': 0,
                    'price_subtotal_incl': 0,
                    'combo_id': combo.id,
                    'combo_item_id': combo.combo_item_ids[0].id,
                }),
                Command.create({
                    'order_id': order.id,
                    'product_id': product_2.id,
                    'qty': 1,
                    'price_unit': 30.0,
                    'price_subtotal': 0,
                    'price_subtotal_incl': 0,
                    'combo_id': combo.id,
                    'combo_item_id': combo.combo_item_ids[1].id,
                }),
            ]
        })
        preset_eat_in = self.env['pos.preset'].create({
            'name': 'Eat in',
        })

        controller = PosSelfOrderController()
        controller._verify_line_price(
            desk_combo_line, self.pos_config, preset_eat_in
        )
        total = desk_combo_line.combo_line_ids[0].price_unit * desk_combo_line.combo_line_ids[0].qty + desk_combo_line.combo_line_ids[1].price_unit
        self.assertEqual(total, 52)
        self.assertEqual(desk_combo_line.combo_line_ids[0].price_unit, 15)
        self.assertEqual(desk_combo_line.combo_line_ids[1].price_unit, 22)
