# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Author: Leonardo Pistone
# Copyright 2015 Camptocamp SA

from odoo.addons.stock.tests.common2 import TestStockCommon
from odoo.tests.common import Form


class TestVirtualAvailable(TestStockCommon):
    def setUp(self):
        super(TestVirtualAvailable, self).setUp()

        # Make `product3` a storable product for this test. Indeed, creating quants
        # and playing with owners is not possible for consumables.
        self.product_3.type = 'product'
        self.env['stock.picking.type'].browse(self.ref('stock.picking_type_out')).reservation_method = 'manual'

        self.env['stock.quant'].create({
            'product_id': self.product_3.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 30.0})

        self.env['stock.quant'].create({
            'product_id': self.product_3.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 10.0,
            'owner_id': self.user_stock_user.partner_id.id})

        self.picking_out = self.env['stock.picking'].create({
            'picking_type_id': self.ref('stock.picking_type_out'),
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id})
        self.env['stock.move'].create({
            'name': 'a move',
            'product_id': self.product_3.id,
            'product_uom_qty': 3.0,
            'product_uom': self.product_3.uom_id.id,
            'picking_id': self.picking_out.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id})

        self.picking_out_2 = self.env['stock.picking'].create({
            'picking_type_id': self.ref('stock.picking_type_out'),
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id})
        self.env['stock.move'].create({
            'restrict_partner_id': self.user_stock_user.partner_id.id,
            'name': 'another move',
            'product_id': self.product_3.id,
            'product_uom_qty': 5.0,
            'product_uom': self.product_3.uom_id.id,
            'picking_id': self.picking_out_2.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id})

    def test_without_owner(self):
        self.assertAlmostEqual(40.0, self.product_3.virtual_available)
        self.picking_out.action_assign()
        self.picking_out_2.action_assign()
        self.assertAlmostEqual(32.0, self.product_3.virtual_available)

    def test_with_owner(self):
        prod_context = self.product_3.with_context(owner_id=self.user_stock_user.partner_id.id)
        self.assertAlmostEqual(10.0, prod_context.virtual_available)
        self.picking_out.action_assign()
        self.picking_out_2.action_assign()
        self.assertAlmostEqual(5.0, prod_context.virtual_available)

    def test_free_quantity(self):
        """ Test the value of product.free_qty. Free_qty = qty_on_hand - qty_reserved"""
        self.assertAlmostEqual(40.0, self.product_3.free_qty)
        self.picking_out.action_confirm()
        self.picking_out_2.action_confirm()
        # No reservation so free_qty is unchanged
        self.assertAlmostEqual(40.0, self.product_3.free_qty)
        self.picking_out.action_assign()
        self.picking_out_2.action_assign()
        # 8 units are now reserved
        self.assertAlmostEqual(32.0, self.product_3.free_qty)
        self.picking_out.do_unreserve()
        self.picking_out_2.do_unreserve()
        # 8 units are available again
        self.assertAlmostEqual(40.0, self.product_3.free_qty)

    def test_archive_product_1(self):
        """`qty_available` and `virtual_available` are computed on archived products"""
        self.assertTrue(self.product_3.active)
        self.assertAlmostEqual(40.0, self.product_3.qty_available)
        self.assertAlmostEqual(40.0, self.product_3.virtual_available)
        self.product_3.active = False
        self.assertAlmostEqual(40.0, self.product_3.qty_available)
        self.assertAlmostEqual(40.0, self.product_3.virtual_available)

    def test_archive_product_2(self):
        """Archiving a product should archive its reordering rules"""
        self.assertTrue(self.product_3.active)
        orderpoint_form = Form(self.env['stock.warehouse.orderpoint'])
        orderpoint_form.product_id = self.product_3
        orderpoint_form.location_id = self.env.ref('stock.stock_location_stock')
        orderpoint_form.product_min_qty = 0.0
        orderpoint_form.product_max_qty = 5.0
        orderpoint = orderpoint_form.save()
        self.assertTrue(orderpoint.active)
        self.product_3.active = False
        self.assertFalse(orderpoint.active)

    def test_search_qty_available(self):
        product = self.env['product.product'].create({
            'name': 'Brand new product',
            'type': 'product',
        })
        result = self.env['product.product'].search([
            ('qty_available', '=', 0),
            ('id', 'in', product.ids),
        ])
        self.assertEqual(product, result)

    def test_search_product_template(self):
        """
        Suppose a variant V01 that can not be deleted because it is used by a
        lot [1]. Then, the variant's template T is changed: we add a dynamic
        attribute. Because of [1], V01 is archived. This test ensures that
        `name_search` still finds T.
        Then, we create a new variant V02 of T. This test also ensures that
        calling `name_search` with a negative operator will exclude T from the
        result.
        """
        template = self.env['product.template'].create({
            'name': 'Super Product',
        })
        product01 = template.product_variant_id

        self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': product01.id,
            'company_id': self.env.company.id,
        })

        product_attribute = self.env['product.attribute'].create({
            'name': 'PA',
            'create_variant': 'dynamic'
        })

        self.env['product.attribute.value'].create([{
            'name': 'PAV' + str(i),
            'attribute_id': product_attribute.id
        } for i in range(2)])

        tmpl_attr_lines = self.env['product.template.attribute.line'].create({
            'attribute_id': product_attribute.id,
            'product_tmpl_id': product01.product_tmpl_id.id,
            'value_ids': [(6, 0, product_attribute.value_ids.ids)],
        })

        self.assertFalse(product01.active)
        self.assertTrue(template.active)
        self.assertFalse(template.product_variant_ids)

        res = self.env['product.template'].name_search(name='super', operator='ilike')
        res_ids = [r[0] for r in res]
        self.assertIn(template.id, res_ids)

        product02 = self.env['product.product'].create({
            'default_code': '123',
            'product_tmpl_id': template.id,
            'product_template_attribute_value_ids': [(6, 0, tmpl_attr_lines.product_template_value_ids[0].ids)]
        })

        self.assertFalse(product01.active)
        self.assertTrue(product02.active)
        self.assertTrue(template)
        self.assertEqual(template.product_variant_ids, product02)

        res = self.env['product.template'].name_search(name='123', operator='not ilike')
        res_ids = [r[0] for r in res]
        self.assertNotIn(template.id, res_ids)
