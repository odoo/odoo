import odoo.tests

from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged('post_install', '-at_install')
class TestSelfOrderCombo(SelfOrderCommonTest):
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
        self.combo1 = self.combo_generator('Green', [0.0, 5.0, 10.0], [50.0, 70.0, 90.0], 2, 1)
        self.combo2 = self.combo_generator('Red', [0.0, 0.0, 0.0], [40.0, 60.0, 80.0], 5, 0)
        self.combo3 = self.combo_generator('Purple', [10.0, 20.0, 30.0], [0, 0, 0], 10, 0)
        self.big_combo = self.env['product.product'].create({
            'name': 'Big Combo',
            'type': 'combo',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'combo_ids': [(6, 0, [self.combo1.id, self.combo2.id, self.combo3.id])],
            'pos_categ_ids': [(6, 0, [self.combo_category.id])],
        })

        self.env['product.product'].create({
            'name': 'Random Product 1',
            'type': 'consu',
            'lst_price': 15.0,
            'taxes_id': [(6, 0, [self.tax_21.id])],
            'pos_categ_ids': [(6, 0, [self.combo_category.id])],
        })
        self.env['product.product'].create({
            'name': 'Random Product 2',
            'type': 'consu',
            'lst_price': 25.0,
            'taxes_id': [(6, 0, [self.tax_12.id])],
            'pos_categ_ids': [(6, 0, [self.combo_category.id])],
        })
        self.env['product.product'].create({
            'name': 'Random Product 3',
            'type': 'consu',
            'lst_price': 35.0,
            'taxes_id': [(6, 0, [self.tax_6.id])],
            'pos_categ_ids': [(6, 0, [self.combo_category.id])],
        })

        self.pos_config.write({
            'self_ordering_default_user_id': self.pos_admin.id,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
            'available_preset_ids': [(5, 0)],
            'iface_available_categ_ids': self.combo_category.ids,
            'limit_categories': True,
        })

    def combo_generator(self, name, extra_price, lst_price, max=1, free=1):
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
            'qty_max': max,
            'qty_free': free,
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

    def test_combo_prices(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, 'test_combo_prices')
