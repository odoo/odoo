# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged

from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestPoSProductVariants(ProductVariantsCommon, TestPointOfSaleHttpCommon):

    def test_integration_dynamic_variant_price(self):
        """Tests the price of products with dynamic variant when added to cart"""
        self.env['product.attribute.value'].create({
            'name': 'dyn3',
            'attribute_id': self.dynamic_attribute.id,
            'default_extra_price': 10,
        })
        (dyn1, dyn2, dyn3) = self.dynamic_attribute.value_ids
        dyn2.default_extra_price = 5

        product_template = self.env['product.template'].create({
            'name': 'A dynamic product',
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_template.id,
            'attribute_id': self.dynamic_attribute.id,
            'value_ids': [Command.set([dyn1.id, dyn2.id, dyn3.id])],
        })

        # Create a variant (because of dynamic attribute)
        ptav_dyn2 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids.id),
            ('product_attribute_value_id', '=', dyn2.id)
        ])

        self.env['product.product'].create({
            'available_in_pos': True,
            'product_tmpl_id': product_template.id,
            'product_template_attribute_value_ids': [(6, 0, [ptav_dyn2.id])],
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_integration_dynamic_variant_price', login="pos_user")

    def test_integration_always_variant_price(self):
        """Tests the price of products with always variant when added to cart"""
        self.size_attribute_m.default_extra_price = 5

        product_template = self.env['product.template'].create({
            'name': 'A always product',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'is_storable': True,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_template.id,
            'attribute_id': self.size_attribute.id,
            'value_ids': [Command.set([self.size_attribute_s.id, self.size_attribute_m.id])],
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_integration_always_variant_price', login="pos_user")

    def test_integration_never_variant_price(self):
        """Tests the price of products with no variant(never) variant when added to cart"""
        self.no_variant_attribute_second.default_extra_price = 5

        product_template = self.env['product.template'].create({
            'name': 'A never product',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'is_storable': True,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_template.id,
            'attribute_id': self.no_variant_attribute.id,
            'value_ids': [Command.set([self.no_variant_attribute_extra.id, self.no_variant_attribute_second.id])],
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_integration_never_variant_price', login="pos_user")

    def test_integration_dynamic_always_variant_price(self):
        """Tests the price of products with dynamic and always variants when added to cart"""
        self.env['product.attribute.value'].create({
            'name': 'dyn3',
            'attribute_id': self.dynamic_attribute.id,
            'default_extra_price': 20,
        })
        (dyn1, dyn2, dyn3) = self.dynamic_attribute.value_ids
        dyn2.default_extra_price = 10
        self.size_attribute_m.default_extra_price = 5

        product_template = self.env['product.template'].create({
            'name': 'A dyn/alw product',
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create([{
            'product_tmpl_id': product_template.id,
            'attribute_id': self.dynamic_attribute.id,
            'value_ids': [Command.set([dyn1.id, dyn2.id, dyn3.id])],
        }, {
            'product_tmpl_id': product_template.id,
            'attribute_id': self.size_attribute.id,
            'value_ids': [Command.set([self.size_attribute_s.id, self.size_attribute_m.id])],
        }])

        # Create a variant (because of dynamic attribute)
        ptav_dyn2 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids[0].id),
            ('product_attribute_value_id', '=', dyn2.id)
        ])
        ptav_always1 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids[1].id),
            ('product_attribute_value_id', '=', self.size_attribute_s.id)
        ])

        self.env['product.product'].create({
            'available_in_pos': True,
            'product_tmpl_id': product_template.id,
            'product_template_attribute_value_ids': [(6, 0, (ptav_dyn2 + ptav_always1).ids)],
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_integration_dynamic_always_variant_price', login="pos_user")

    def test_integration_dynamic_never_variant_price(self):
        """Tests the price of products with dynamic and never variants when added to cart"""
        self.env['product.attribute.value'].create({
            'name': 'dyn3',
            'attribute_id': self.dynamic_attribute.id,
            'default_extra_price': 20,
        })
        (dyn1, dyn2, dyn3) = self.dynamic_attribute.value_ids
        dyn2.default_extra_price = 10
        self.no_variant_attribute_second.default_extra_price = 5

        product_template = self.env['product.template'].create({
            'name': 'A dyn/nev product',
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create([{
            'product_tmpl_id': product_template.id,
            'attribute_id': self.dynamic_attribute.id,
            'value_ids': [Command.set([dyn1.id, dyn2.id, dyn3.id])],
        }, {
            'product_tmpl_id': product_template.id,
            'attribute_id': self.no_variant_attribute.id,
            'value_ids': [Command.set([self.no_variant_attribute_extra.id, self.no_variant_attribute_second.id])],
        }])

        # Create a variant (because of dynamic attribute)
        ptav_dyn2 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids[0].id),
            ('product_attribute_value_id', '=', dyn2.id)
        ])
        ptav_never1 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids[1].id),
            ('product_attribute_value_id', '=', self.no_variant_attribute_extra.id)
        ])

        self.env['product.product'].create({
            'available_in_pos': True,
            'product_tmpl_id': product_template.id,
            'product_template_attribute_value_ids': [(6, 0, (ptav_dyn2 + ptav_never1).ids)],
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_integration_dynamic_never_variant_price', login="pos_user")

    def test_integration_always_never_variant_price(self):
        """Tests the price of products with always and never variants when added to cart"""
        self.no_variant_attribute_second.default_extra_price = 5
        self.size_attribute_m.default_extra_price = 10

        product_template = self.env['product.template'].create({
            'name': 'A alw/nev product',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'is_storable': True,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create([{
            'product_tmpl_id': product_template.id,
            'attribute_id': self.no_variant_attribute.id,
            'value_ids': [Command.set([self.no_variant_attribute_extra.id, self.no_variant_attribute_second.id])],
        }, {
            'product_tmpl_id': product_template.id,
            'attribute_id': self.size_attribute.id,
            'value_ids': [Command.set([self.size_attribute_s.id, self.size_attribute_m.id])],
        }])

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_integration_always_never_variant_price', login="pos_user")

    def test_integration_dynamic_always_never_variant_price(self):
        """Tests the price of products with all types of variants when added to cart"""
        (dyn1, dyn2) = self.dynamic_attribute.value_ids
        dyn2.default_extra_price = 10
        self.size_attribute_m.default_extra_price = 5
        self.no_variant_attribute_second.default_extra_price = 0.5

        product_template = self.env['product.template'].create({
            'name': 'A dyn/alw/nev product',
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create([{
            'product_tmpl_id': product_template.id,
            'attribute_id': self.dynamic_attribute.id,
            'value_ids': [Command.set([dyn1.id, dyn2.id])],
        }, {
            'product_tmpl_id': product_template.id,
            'attribute_id': self.no_variant_attribute.id,
            'value_ids': [Command.set([self.no_variant_attribute_extra.id, self.no_variant_attribute_second.id])],
        }, {
            'product_tmpl_id': product_template.id,
            'attribute_id': self.size_attribute.id,
            'value_ids': [Command.set([self.size_attribute_s.id, self.size_attribute_m.id])],
        }])

        # Create a variant (because of dynamic attribute)
        ptav_dyn2 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids[0].id),
            ('product_attribute_value_id', '=', dyn2.id)
        ])
        ptav_never1 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids[1].id),
            ('product_attribute_value_id', '=', self.no_variant_attribute_extra.id)
        ])
        ptav_always1 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids[1].id),
            ('product_attribute_value_id', '=', self.size_attribute_s.id)
        ])

        self.env['product.product'].create({
            'available_in_pos': True,
            'product_tmpl_id': product_template.id,
            'product_template_attribute_value_ids': [(6, 0, (ptav_dyn2 + ptav_always1 + ptav_never1).ids)],
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_integration_dynamic_always_never_variant_price', login="pos_user")

    def test_image_variants_displayed(self):
        """
        Tests that the user can correctly chose variants in the product_configurator_popup
        if the variant was set as Image
        """
        image_attribute = self.env['product.attribute'].create({
            'name': 'Images',
            'display_type': 'image',
            'create_variant': 'always',
        })
        images = self.env['product.attribute.value'].create([{
            'name': 'First Image',
            'attribute_id': image_attribute.id,
        }, {
            'name': 'Second Image',
            'attribute_id': image_attribute.id,
            'default_extra_price': 20,
        }])
        product_template = self.env['product.template'].create({
            'name': 'Image Product',
            'is_storable': True,
            'taxes_id': False,
            'available_in_pos': True,
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_template.id,
            'attribute_id': image_attribute.id,
            'value_ids': [Command.set([images[0].id, images[1].id])],
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_image_variants_displayed', login="pos_user")

    def test_variants_merge_line_barcode(self):
        """Tests the price of products with always variant when added to cart"""
        product_template = self.env['product.template'].create({
            'name': 'A variant product',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'is_storable': True,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_template.id,
            'attribute_id': self.size_attribute.id,
            'value_ids': [Command.set([self.size_attribute_s.id, self.size_attribute_m.id])],
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_template.id,
            'attribute_id': self.color_attribute.id,
            'value_ids': [Command.set([self.color_attribute_blue.id])],
        })
        product_S_blue = self.env["product.product"].search([("product_tmpl_id", "=", product_template.id)])[0]
        self.assertEqual(len(product_S_blue.product_template_variant_value_ids), 1)  # Size S (only size varies)
        self.assertEqual(len(product_S_blue.product_template_attribute_value_ids), 2)  # Attributes: S, blue
        product_S_blue.barcode = "TEST123"

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_variants_merge_line_barcode', login="pos_user")

    def test_get_product_info_pos_uses_template_available_quantity_for_variant_product(self):
        """Units Available in product info popup must use template stock for variant products."""
        size_attribute = self.env['product.attribute'].create({'name': 'Size'})
        size_small = self.env['product.attribute.value'].create({'name': 'S', 'attribute_id': size_attribute.id})
        size_medium = self.env['product.attribute.value'].create({'name': 'M', 'attribute_id': size_attribute.id})

        product_template = self.env['product.template'].create({
            'name': 'Variant stock product',
            'available_in_pos': True,
            'is_storable': True,
            'taxes_id': False,
            'attribute_line_ids': [Command.create({
                'attribute_id': size_attribute.id,
                'value_ids': [Command.set([size_small.id, size_medium.id])],
            })],
        })
        variants = product_template.product_variant_ids.sorted('id')
        self.assertEqual(len(variants), 2)

        warehouse = self.main_pos_config.warehouse_id
        self.env['stock.quant']._update_available_quantity(variants[0], warehouse.lot_stock_id, 2.0)
        self.env['stock.quant']._update_available_quantity(variants[1], warehouse.lot_stock_id, 5.0)

        selected_variant = variants[1]
        info = product_template.get_product_info_pos(
            product_template.list_price,
            1,
            self.main_pos_config.id,
        )
        warehouse_info = next(w for w in info['warehouses'] if w['id'] == warehouse.id)

        template_available_qty = product_template.with_context(warehouse_id=warehouse.id).qty_available
        selected_variant_qty = selected_variant.with_context(warehouse_id=warehouse.id).qty_available

        self.assertNotEqual(template_available_qty, selected_variant_qty)
        self.assertEqual(warehouse_info['available_quantity'], template_available_qty)

    def test_load_product_from_pos_skips_exclusion_of_archived_value(self):
        """An exclusion must only be loaded together with its attribute value,
        otherwise the POS crashes when computing the attribute exclusions."""
        product_template = self.env['product.template'].create({
            'name': 'Excluded shirt',
            'available_in_pos': True,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': self.size_attribute.id,
                    'value_ids': [Command.set([self.size_attribute_s.id, self.size_attribute_m.id])],
                }),
                Command.create({
                    'attribute_id': self.color_attribute.id,
                    'value_ids': [Command.set([self.color_attribute_red.id, self.color_attribute_blue.id])],
                }),
            ],
        })
        size_line, color_line = product_template.attribute_line_ids
        ptav_s = size_line.product_template_value_ids.filtered(lambda v: v.product_attribute_value_id == self.size_attribute_s)
        ptav_red, ptav_blue = color_line.product_template_value_ids
        size_exclusion, color_exclusion = self.env['product.template.attribute.exclusion'].create([{
            'product_tmpl_id': product_template.id,
            'product_template_attribute_value_id': ptav_s.id,
            'value_ids': [Command.set(ptav_red.ids)],
        }, {
            'product_tmpl_id': product_template.id,
            'product_template_attribute_value_id': ptav_blue.id,
            'value_ids': [Command.set(ptav_red.ids)],
        }])

        # A sold variant blocks the deletion of the size line: it is archived with its values
        self.main_pos_config.with_user(self.pos_user).open_ui()
        variant = product_template.product_variant_ids.filtered(lambda p: ptav_s in p.product_template_attribute_value_ids)[:1]
        self.env['pos.order'].create({
            'session_id': self.main_pos_config.current_session_id.id,
            'amount_tax': 0,
            'amount_total': 10,
            'amount_paid': 0,
            'amount_return': 0,
            'lines': [Command.create({
                'product_id': variant.id,
                'qty': 1,
                'price_unit': 10,
                'price_subtotal': 10,
                'price_subtotal_incl': 10,
            })],
        })
        size_line.unlink()
        self.assertFalse(size_line.active)
        self.assertFalse(ptav_s.ptav_active)
        self.assertTrue(size_exclusion.exists())

        result = self.env['product.template'].load_product_from_pos(
            self.main_pos_config.id, [('id', '=', product_template.id)],
        )
        loaded_ptav_ids = {ptav['id'] for ptav in result['product.template.attribute.value']}
        loaded_exclusion_ids = {excl['id'] for excl in result['product.template.attribute.exclusion']}
        self.assertNotIn(ptav_s.id, loaded_ptav_ids)
        self.assertEqual(loaded_exclusion_ids, {color_exclusion.id})

    def test_load_product_from_pos_skips_exclusion_of_other_product_value(self):
        """An exclusion can target another product than the one of its value:
        it must not be loaded without that value."""
        excluded_template, other_template = self.env['product.template'].create([{
            'name': name,
            'available_in_pos': True,
            'attribute_line_ids': [Command.create({
                'attribute_id': self.size_attribute.id,
                'value_ids': [Command.set([self.size_attribute_s.id, self.size_attribute_m.id])],
            })],
        } for name in ('Excluded product', 'Other product')])
        other_ptav = other_template.attribute_line_ids.product_template_value_ids[0]
        own_ptav = excluded_template.attribute_line_ids.product_template_value_ids[0]
        other_exclusion, own_exclusion = self.env['product.template.attribute.exclusion'].create([{
            'product_tmpl_id': excluded_template.id,
            'product_template_attribute_value_id': other_ptav.id,
        }, {
            'product_tmpl_id': excluded_template.id,
            'product_template_attribute_value_id': own_ptav.id,
        }])
        other_template.action_archive()
        self.main_pos_config.with_user(self.pos_user).open_ui()

        for load_archived in (False, True):
            result = self.env['product.template'].with_context(load_archived=load_archived).load_product_from_pos(
                self.main_pos_config.id, [('id', '=', excluded_template.id)],
            )
            loaded_ptav_ids = {ptav['id'] for ptav in result['product.template.attribute.value']}
            loaded_exclusion_ids = {excl['id'] for excl in result['product.template.attribute.exclusion']}
            self.assertNotIn(other_ptav.id, loaded_ptav_ids)
            self.assertIn(own_ptav.id, loaded_ptav_ids)
            self.assertNotIn(other_exclusion.id, loaded_exclusion_ids, f"load_archived={load_archived}")
            self.assertIn(own_exclusion.id, loaded_exclusion_ids)

    def test_mo_custom_description_ship_later(self):
        """
        Tests that a custom attribute is shown on the MO when being
        processed through the PoS, in the custom description field
        """
        self.test_product_1 = self.env['product.template'].create({
            'name': 'Custom Product',
            'available_in_pos': True,
            'list_price': 10.0,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': self.custom_attribute.id,
                    'value_ids': [Command.set([self.custom_attribute_value.id])],
                }),
                Command.create({
                    'attribute_id': self.no_variant_attribute.id,
                    'value_ids': [Command.set([self.no_variant_attribute_extra.id])],
                }),
                Command.create({
                    'attribute_id': self.color_attribute.id,
                    'value_ids': [Command.set([self.color_attribute_red.id])],
                }),
            ],
        })
        product_variant = self.test_product_1.product_variant_id
        ptavs = self.test_product_1.attribute_line_ids.product_template_value_ids
        ptav_custom = ptavs.filtered(lambda p: p.attribute_id == self.custom_attribute)
        ptav_never = ptavs.filtered(lambda p: p.attribute_id == self.no_variant_attribute)
        ptav_always = ptavs.filtered(lambda p: p.attribute_id == self.color_attribute)
        self.main_pos_config.open_ui()

        order = self.env['pos.order'].create({
            'name': 'Order 12345-123-1234',
            'company_id': self.env.company.id,
            'session_id': self.main_pos_config.current_session_id.id,
            'partner_id': self.partner_test_1.id,
            'lines': [Command.create({
                'product_id': product_variant.id,
                'price_unit': 10.0,
                'qty': 1.0,
                'price_subtotal': 10.0,
                'price_subtotal_incl': 10.0,
                'attribute_value_ids': [Command.set([
                    ptav_custom.id,
                    ptav_never.id,
                    ptav_always.id
                ])],
                'custom_attribute_value_ids': [Command.create({
                    'custom_product_template_attribute_value_id': ptav_custom.id,
                    'custom_value': 'White',
                })],
            })],
            'amount_total': 10.0,
            'amount_tax': 0.0,
            'amount_paid': 10.0,
            'amount_return': 0.0,
        })
        order._create_order_picking()
        move = order.picking_ids.move_ids[0]
        self.env['stock.reference'].create({
            'name': order.name,
            'move_ids': [Command.link(move.id)],
            'pos_order_ids': [Command.link(order.id)],
        })

        move.invalidate_recordset(['description_picking'])
        self.assertEqual(order.picking_ids.move_ids.description_picking, 'No variant: extra\nCustom: Custom: White')
