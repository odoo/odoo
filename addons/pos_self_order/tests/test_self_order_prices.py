import odoo.tests
from odoo import Command
from uuid import uuid4

from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged('post_install', '-at_install')
class TestSelfOrderPrice(SelfOrderCommonTest):
    def setUp(self):
        super().setUp()

        self.tax_6 = self.env['account.tax'].create({
            'name': 'Test 6%',
            'amount': 6,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })
        self.tax_12 = self.env['account.tax'].create({
            'name': 'Test 12%',
            'amount': 12,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'price_include_override': 'tax_included',
        })
        self.tax_21 = self.env['account.tax'].create({
            'name': 'Test 21%',
            'amount': 21,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'price_include_override': 'tax_excluded',
        })

        self.combo_category = self.env['pos.category'].create({'name': 'Combo Category'})
        self.combo_no_price = self.combo_generator('No Price', [20.0, 30.0, 40.0], [0.0, 0.0, 0.0], 1, 1)
        self.combo1 = self.combo_generator('Green', [0.0, 5.0, 10.0], [50.0, 70.0, 90.0], 2, 1)
        self.combo2 = self.combo_generator('Red', [0.0, 0.0, 0.0], [40.0, 60.0, 80.0], 5, 0)
        self.combo3 = self.combo_generator('Purple', [10.0, 20.0, 30.0], [0, 0, 0], 10, 0)
        self.big_combo = self.env['product.product'].create({
            'name': 'Big Combo',
            'type': 'combo',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'combo_ids': [(6, 0, [self.combo1.id, self.combo2.id, self.combo3.id])],
            'pos_categ_ids': [(6, 0, [self.combo_category.id])],
            'available_in_pos': True,
        })

        self.small_combo = self.env['product.product'].create({
            'name': 'Small Combo',
            'type': 'combo',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'combo_ids': [(6, 0, [self.combo_no_price.id, self.combo3.id])],
            'pos_categ_ids': [(6, 0, [self.combo_category.id])],
            'available_in_pos': True,
        })

        self.combo_no_free1 = self.combo_generator('First no Free', [20.0, 30.0, 40.0], [0.0, 5.0, 10.0], 2, 0)
        self.combo_no_free2 = self.combo_generator('Second no Free', [10.0, 15.0, 3.0], [1.0, 3.0, 2.3], 3, 0)
        self.combo_no_free3 = self.combo_generator('Third no Free', [1.3, 2.88, 9.43], [10.0, 20.0, 30.0], 4, 0)
        self.no_free_combo = self.env['product.product'].create({
            'name': 'No Free Combo',
            'type': 'combo',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'combo_ids': [(6, 0, [self.combo_no_free1.id, self.combo_no_free2.id, self.combo_no_free3.id])],
            'pos_categ_ids': [(6, 0, [self.combo_category.id])],
            'available_in_pos': True,
        })

        self.env['product.product'].create({
            'name': 'Random Product 1',
            'type': 'consu',
            'lst_price': 15.0,
            'taxes_id': [(6, 0, [self.tax_21.id])],
            'pos_categ_ids': [(6, 0, [self.combo_category.id])],
            'available_in_pos': True,
        })
        self.env['product.product'].create({
            'name': 'Random Product 2',
            'type': 'consu',
            'lst_price': 25.0,
            'taxes_id': [(6, 0, [self.tax_12.id])],
            'pos_categ_ids': [(6, 0, [self.combo_category.id])],
            'available_in_pos': True,
        })
        self.env['product.product'].create({
            'name': 'Random Product 3',
            'type': 'consu',
            'lst_price': 35.0,
            'taxes_id': [(6, 0, [self.tax_6.id])],
            'pos_categ_ids': [(6, 0, [self.combo_category.id])],
            'available_in_pos': True,
        })

        self.price_extra_product = self.env['product.product'].create({
            'name': 'Product with attributes',
            'is_storable': True,
            'available_in_pos': True,
            'lst_price': 100.95,
            'pos_categ_ids': [(6, 0, [self.combo_category.id])],
            'taxes_id': [(6, 0, [self.tax_21.id])],
        })
        price_extra, no_price_extra = self.env['product.attribute'].create([{
            'name': 'Price Extra',
            'display_type': 'radio',
            'create_variant': 'no_variant',
        }, {
            'name': 'No Price Extra',
            'display_type': 'radio',
            'create_variant': 'no_variant',
        }])
        price_extra_values = self.env['product.attribute.value'].create([{
            'name': 'Small',
            'attribute_id': price_extra.id,
            'default_extra_price': 1.99,
        }, {
            'name': 'Big',
            'attribute_id': price_extra.id,
            'default_extra_price': 5.49,
        }])
        no_price_extra_values = self.env['product.attribute.value'].create([{
            'name': 'One',
            'attribute_id': no_price_extra.id,
        }, {
            'name': 'Two',
            'attribute_id': no_price_extra.id,
        }])
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.price_extra_product.product_tmpl_id.id,
            'attribute_id': price_extra.id,
            'value_ids': [(6, 0, price_extra_values.ids)],
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.price_extra_product.product_tmpl_id.id,
            'attribute_id': no_price_extra.id,
            'value_ids': [(6, 0, no_price_extra_values.ids)],
        })

        self.original_presets = self.pos_config.available_preset_ids
        self.pos_config.write({
            'self_ordering_default_user_id': self.pos_admin.id,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
            'available_preset_ids': [(5, 0)],
            'iface_available_categ_ids': self.combo_category.ids,
            'limit_categories': True,
        })

    def combo_generator(self, name, extra_price, lst_price, qty_max=1, qty_free=1):
        product1 = self.env['product.product'].create({
            'name': f'{name} 1',
            'is_storable': True,
            'available_in_pos': True,
            'lst_price': lst_price[0],
            'taxes_id': [(6, 0, [self.tax_6.id])],
        })
        product2 = self.env['product.product'].create({
            'name': f'{name} 2',
            'is_storable': True,
            'available_in_pos': True,
            'lst_price': lst_price[1],
            'taxes_id': [(6, 0, [self.tax_12.id])],
        })
        product3 = self.env['product.product'].create({
            'name': f'{name} 3',
            'is_storable': True,
            'available_in_pos': True,
            'lst_price': lst_price[2],
            'taxes_id': [(6, 0, [self.tax_21.id])],
        })
        size_attribute, color_attribute = self.env['product.attribute'].create([{
            'name': 'Size',
            'display_type': 'radio',
            'create_variant': 'no_variant',
        }, {
            'name': 'Color',
            'display_type': 'radio',
            'create_variant': 'no_variant',
        }])
        size_attribute_values = self.env['product.attribute.value'].create([{
            'name': 'Small',
            'attribute_id': size_attribute.id,
        }, {
            'name': 'Big',
            'attribute_id': size_attribute.id,
            'default_extra_price': 5.0,
        }])
        color_attribute_values = self.env['product.attribute.value'].create([{
            'name': 'Red',
            'attribute_id': color_attribute.id,
        }, {
            'name': 'Blue',
            'attribute_id': color_attribute.id,
            'default_extra_price': 10.0,
        }])
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product3.product_tmpl_id.id,
            'attribute_id': size_attribute.id,
            'value_ids': [(6, 0, size_attribute_values.ids)],
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product3.product_tmpl_id.id,
            'attribute_id': color_attribute.id,
            'value_ids': [(6, 0, color_attribute_values.ids)],
        })

        combo = self.env['product.combo'].create({
            'name': f'Test Combo {name}',
            'qty_max': qty_max,
            'is_upsell': qty_free == 0,
            'qty_free': qty_free,
        })
        self.env['product.combo.item'].create({
            'product_id': product1.id,
            'extra_price': extra_price[0],
            'combo_id': combo.id,
        })
        self.env['product.combo.item'].create({
            'product_id': product2.id,
            'extra_price': extra_price[1],
            'combo_id': combo.id,
        })
        self.env['product.combo.item'].create({
            'product_id': product3.id,
            'extra_price': extra_price[2],
            'combo_id': combo.id,
        })
        return combo

    def setup_preset_and_pricelist(self):
        self.pos_config.write({
            'available_preset_ids': [(6, 0, self.original_presets.ids)],
            'default_preset_id': self.original_presets[0].id,
        })
        self.pricelist_percent = self.env['product.pricelist'].create({
            'name': "10% Pricelist",
            'company_id': self.env.company.id,
            'item_ids': [
                Command.create({
                    'compute_price': 'percentage',
                    'percent_price': 10.0,
                    'applied_on': '3_global',
                }),
            ],
        })
        self.pricelist_free = self.env['product.pricelist'].create({
            'name': "Free Pricelist",
            'company_id': self.env.company.id,
            'item_ids': [
                Command.create({
                    'compute_price': 'fixed',
                    'fixed_price': 0,
                    'applied_on': '3_global',
                }),
            ],
        })
        self.original_presets[1].write({'pricelist_id': self.pricelist_percent.id})
        self.original_presets[2].write({'pricelist_id': self.pricelist_free.id})

    def _create_self_order(self, lines_vals, pricelist=None, fiscal_position=None):
        session = self.pos_config.current_session_id
        if not session:
            self.pos_config.with_user(self.pos_admin).open_ui()
            session = self.pos_config.current_session_id
            session.set_opening_control(0, "")
        reference, tracking_number = self.pos_config._get_next_order_refs()
        return self.env['pos.order'].create({
            'pos_reference': reference,
            'tracking_number': tracking_number,
            'session_id': session.id,
            'config_id': self.pos_config.id,
            'company_id': self.env.company.id,
            'currency_id': self.pos_config.currency_id.id,
            'pricelist_id': (pricelist or self.pos_config.pricelist_id).id,
            'fiscal_position_id': (fiscal_position or self.pos_config.default_fiscal_position_id).id,
            'state': 'draft',
            'access_token': uuid4().hex,
            'amount_total': 0,
            'amount_paid': 0,
            'amount_tax': 0,
            'amount_return': 0,
            'lines': lines_vals,
        })

    def _order_line_vals(self, product, qty=1.0, price_unit=0.0, attribute_values=None, **extra):
        vals = {
            'product_id': product.id,
            'qty': qty,
            'price_unit': price_unit,
            'tax_ids': [Command.set(product.taxes_id.ids)],
            'price_subtotal': 0,
            'price_subtotal_incl': 0,
            'price_type': 'original',
        }
        if attribute_values:
            vals['attribute_value_ids'] = [Command.set(attribute_values)]
        vals.update(extra)
        return Command.create(vals)

    def test_recompute_prices_between_frontend_and_backend(self):
        product = self.env['product.product'].search([('name', '=', 'Random Product 1')], limit=1)
        order = self._create_self_order([
            self._order_line_vals(product, qty=2.0, price_unit=1.0),
        ])

        order.recompute_prices()

        expected_price = order.pricelist_id._get_product_price(product, 1.0, currency=order.currency_id)
        self.assertAlmostEqual(order.lines[0].price_unit, expected_price, places=2)
        self.assertGreater(order.amount_total, 0)

    def test_recompute_prices_are_immutable_from_frontend(self):
        product = self.price_extra_product
        ptav = self.price_extra_product.attribute_line_ids.product_template_value_ids

        order = self._create_self_order([
            self._order_line_vals(product, qty=2.0, price_unit=0.0, attribute_values=[ptav.ids[1], ptav.ids[3]]),
        ])

        order.recompute_prices()
        combination = ptav[1] | ptav[3]

        product_ctx = product.with_context(product._get_product_price_context(combination))
        expected_price = order.pricelist_id._get_product_price(product_ctx, 1.0, currency=order.currency_id)
        self.assertAlmostEqual(order.lines[0].price_unit, expected_price, places=2)
        self.assertGreater(order.lines[0].price_subtotal_incl, order.lines[0].price_subtotal)

    def test_recompute_prices_with_pricelist_percent(self):
        self.setup_preset_and_pricelist()
        product = self.env['product.product'].search([('name', '=', 'Random Product 1')], limit=1)
        order = self._create_self_order(
            [self._order_line_vals(product, qty=1.0, price_unit=999.0)],
            pricelist=self.pricelist_percent,
        )

        order.recompute_prices()

        expected_price = self.pricelist_percent._get_product_price(product, 1.0, currency=order.currency_id)
        self.assertAlmostEqual(order.lines[0].price_unit, expected_price, places=2)

    def test_recompute_prices_with_pricelist_min_quantity_rule(self):
        product = self.cola
        pricelist = self.env['product.pricelist'].create({
            'name': 'Qty3 Fixed 1',
            'company_id': self.env.company.id,
            'item_ids': [
                Command.create({
                    'compute_price': 'fixed',
                    'fixed_price': 1.0,
                    'min_quantity': 3,
                    'applied_on': '1_product',
                    'product_tmpl_id': product.product_tmpl_id.id,
                }),
            ],
        })
        order = self._create_self_order(
            [self._order_line_vals(product, qty=3.0, price_unit=100.0)],
            pricelist=pricelist,
        )
        order.recompute_prices()
        self.assertAlmostEqual(order.lines[0].price_unit, 2.2, places=2)
        self.assertAlmostEqual(order.amount_total, 7.59, places=2)

    def test_recompute_prices_with_fiscal_position_mapping(self):
        product = self.env['product.product'].search([('name', '=', 'Random Product 1')], limit=1)
        fp = self.env['account.fiscal.position'].create({'name': 'Take out'})
        self.tax_6.copy({
            'name': f"{self.tax_6.name} Take out",
            'fiscal_position_ids': [Command.set(fp.ids)],
            'original_tax_ids': [Command.set(self.tax_21.ids)],
        })

        order = self._create_self_order(
            [self._order_line_vals(product, qty=1.0, price_unit=0.0)],
            fiscal_position=fp,
        )

        order.recompute_prices()

        expected_price = order.pricelist_id._get_product_price(product, 1.0, currency=order.currency_id)
        self.assertAlmostEqual(order.lines[0].price_unit, expected_price, places=2)
        self.assertAlmostEqual(order.lines[0].price_subtotal_incl, expected_price * 1.06, places=2)

    def test_recompute_prices_combo_prices(self):
        parent_product = self.big_combo
        combo_item1 = self.combo1.combo_item_ids[0]
        combo_item2 = self.combo1.combo_item_ids[1]

        order = self._create_self_order([
            self._order_line_vals(parent_product, combo_id=self.combo1.id)
        ])
        child_lines = self.env['pos.order.line'].create([
            {
                'product_id': combo_item1.product_id.id,
                'qty': 1.0,
                'price_unit': 0.0,
                'tax_ids': [Command.set(combo_item1.product_id.taxes_id.ids)],
                'price_subtotal': 0,
                'price_subtotal_incl': 0,
                'price_type': 'original',
                'combo_item_id': combo_item1.id,
                'combo_parent_id': order.lines[0].id,
                'order_id': order.id,
            },
            {
                'product_id': combo_item2.product_id.id,
                'qty': 1.0,
                'price_unit': 0.0,
                'tax_ids': [Command.set(combo_item2.product_id.taxes_id.ids)],
                'price_subtotal': 0,
                'price_subtotal_incl': 0,
                'price_type': 'original',
                'combo_item_id': combo_item2.id,
                'combo_parent_id': order.lines[0].id,
                'order_id': order.id,
            }
        ])

        order.recompute_prices()

        parent_line = order.lines.filtered(lambda l: l.product_id.id == parent_product.id)
        self.assertEqual(len(child_lines), 2)
        self.assertTrue(all(line.price_unit > 0 for line in child_lines))
        self.assertAlmostEqual(parent_line.price_subtotal, 0.0, places=2)
        self.assertGreater(order.amount_total, 0)
