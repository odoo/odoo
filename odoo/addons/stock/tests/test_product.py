# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Author: Leonardo Pistone
# Copyright 2015 Camptocamp SA

from odoo.addons.stock.tests.common2 import TestStockCommon
from odoo.exceptions import UserError
from odoo.tests.common import Form


class TestVirtualAvailable(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Make `product3` a storable product for this test. Indeed, creating quants
        # and playing with owners is not possible for consumables.
        cls.product_3.type = 'product'
        cls.env['stock.picking.type'].browse(cls.env.ref('stock.picking_type_out').id).reservation_method = 'manual'

        cls.env['stock.quant'].create({
            'product_id': cls.product_3.id,
            'location_id': cls.env.ref('stock.stock_location_stock').id,
            'quantity': 30.0})

        cls.env['stock.quant'].create({
            'product_id': cls.product_3.id,
            'location_id': cls.env.ref('stock.stock_location_stock').id,
            'quantity': 10.0,
            'owner_id': cls.user_stock_user.partner_id.id})

        cls.picking_out = cls.env['stock.picking'].create({
            'state': 'draft',
            'picking_type_id': cls.env.ref('stock.picking_type_out').id
        })
        cls.env['stock.move'].create({
            'name': 'a move',
            'product_id': cls.product_3.id,
            'product_uom_qty': 3.0,
            'product_uom': cls.product_3.uom_id.id,
            'picking_id': cls.picking_out.id,
            'location_id': cls.env.ref('stock.stock_location_stock').id,
            'location_dest_id': cls.env.ref('stock.stock_location_customers').id})

        cls.picking_out_2 = cls.env['stock.picking'].create({
            'state': 'draft',
            'picking_type_id': cls.env.ref('stock.picking_type_out').id})
        cls.env['stock.move'].create({
            'restrict_partner_id': cls.user_stock_user.partner_id.id,
            'name': 'another move',
            'product_id': cls.product_3.id,
            'product_uom_qty': 5.0,
            'product_uom': cls.product_3.uom_id.id,
            'picking_id': cls.picking_out_2.id,
            'location_id': cls.env.ref('stock.stock_location_stock').id,
            'location_dest_id': cls.env.ref('stock.stock_location_customers').id})

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

    def test_change_product_company(self):
        """ Checks we can't change the product's company if this product has
        quant in another company. """
        company1 = self.env.ref('base.main_company')
        company2 = self.env['res.company'].create({'name': 'Second Company'})
        product = self.env['product.product'].create({
            'name': 'Product [TEST - Change Company]',
            'type': 'product',
        })
        # Creates a quant for productA in the first company.
        self.env['stock.quant'].create({
            'product_id': product.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.location_1.id,
            'quantity': 7,
            'reserved_quantity': 0,
        })
        # Assigns a company: should be OK for company1 but should raise an error for company2.
        product.company_id = company1.id
        with self.assertRaises(UserError):
            product.company_id = company2.id
        # Checks we can assing company2 for the product once there is no more quant for it.
        quant = self.env['stock.quant'].search([('product_id', '=', product.id)])
        quant.quantity = 0
        self.env['stock.quant']._unlink_zero_quants()
        product.company_id = company2.id  # Should work this time.

    def test_change_product_company_02(self):
        """ Checks we can't change the product's company if this product has
        stock move line in another company. """
        company1 = self.env.ref('base.main_company')
        company2 = self.env['res.company'].create({'name': 'Second Company'})
        product = self.env['product.product'].create({
            'name': 'Product [TEST - Change Company]',
            'type': 'consu',
        })
        picking = self.env['stock.picking'].create({
            'location_id': self.env.ref('stock.stock_location_customers').id,
            'location_dest_id': self.env.ref('stock.stock_location_stock').id,
            'picking_type_id': self.ref('stock.picking_type_in'),
            'state': 'draft',
        })
        self.env['stock.move'].create({
            'name': 'test',
            'location_id': self.env.ref('stock.stock_location_customers').id,
            'location_dest_id': self.env.ref('stock.stock_location_stock').id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 1,
            'picking_id': picking.id,
        })
        picking.action_confirm()
        picking.button_validate()

        product.company_id = company1.id
        with self.assertRaises(UserError):
            product.company_id = company2.id

    def test_change_product_company_exclude_vendor_and_customer_location(self):
        """ Checks we can change product company where only exist single company
        and exist quant in vendor/customer location"""
        company1 = self.env.ref('base.main_company')
        customer_location = self.env.ref('stock.stock_location_customers')
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        product = self.env['product.product'].create({
            'name': 'Product Single Company',
            'type': 'product',
        })
        # Creates a quant for company 1.
        self.env['stock.quant'].create({
            'product_id': product.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.location_1.id,
            'quantity': 5,
        })
        # Creates a quant for vendor location.
        self.env['stock.quant'].create({
            'product_id': product.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': supplier_location.id,
            'quantity': -15,
        })
        # Creates a quant for customer location.
        self.env['stock.quant'].create({
            'product_id': product.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': customer_location.id,
            'quantity': 10,
        })
        # Assigns a company: should be ok because only exist one company (exclude vendor and customer location)
        product.company_id = company1.id

        # Reset product company to empty
        product.company_id = False
        company2 = self.env['res.company'].create({'name': 'Second Company'})
        # Assigns to another company: should be not okay because exist quants in defferent company (exclude vendor and customer location)
        with self.assertRaises(UserError):
            product.company_id = company2.id

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
        self.env.ref('base.group_user').write({'implied_ids': [(4, self.env.ref('product.group_product_variant').id)]})
        template = self.env['product.template'].create({
            'name': 'Super Product',
        })
        product01 = template.product_variant_id

        self.env['stock.lot'].create({
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

    def test_product_qty_field_and_context(self):
        main_warehouse = self.warehouse_1
        other_warehouse = self.env['stock.warehouse'].search([('id', '!=', main_warehouse.id)], limit=1)
        warehouses = main_warehouse | other_warehouse
        main_loc = main_warehouse.lot_stock_id
        other_loc = other_warehouse.lot_stock_id
        self.assertTrue(other_warehouse, 'The test needs another warehouse')

        (main_loc | other_loc).name = 'Stock'
        sub_loc01, sub_loc02, sub_loc03 = self.env['stock.location'].create([{
            'name': 'Sub0%s' % (i + 1),
            'location_id': main_loc.id,
        } for i in range(3)])

        self.env['stock.quant'].search([('product_id', '=', self.product_3.id)]).unlink()
        self.env['stock.quant']._update_available_quantity(self.product_3, other_loc, 1000)
        self.env['stock.quant']._update_available_quantity(self.product_3, main_loc, 100)
        self.env['stock.quant']._update_available_quantity(self.product_3, sub_loc01, 10)
        self.env['stock.quant']._update_available_quantity(self.product_3, sub_loc02, 1)

        for wh, loc, expected in [
            (False, False, 1111.0),
            (False, other_loc.id, 1000.0),
            (False, main_loc.id, 111.0),
            (False, sub_loc01.id, 10.0),
            (False, sub_loc01.name, 10.0),
            (False, 'sub', 11.0),
            (False, main_loc.name, 1111.0),
            (False, (sub_loc01 | sub_loc02 | sub_loc03).ids, 11.0),
            (main_warehouse.id, main_loc.name, 111.0),
            (main_warehouse.id, main_loc.id, 111.0),
            (main_warehouse.id, (main_loc | other_loc).ids, 111.0),
            (main_warehouse.id, sub_loc01.id, 10.0),
            (main_warehouse.id, (sub_loc01 | sub_loc02).ids, 11.0),
            (other_warehouse.id, main_loc.name, 1000.0),
            (other_warehouse.id, main_loc.id, 0.0),
            (main_warehouse.name, False, 111.0),
            (main_warehouse.id, False, 111.0),
            (warehouses.ids, False, 1111.0),
            (warehouses.ids, (other_loc | sub_loc02).ids, 1001),
        ]:
            product_qty = self.product_3.with_context(warehouse=wh, location=loc).qty_available
            self.assertEqual(product_qty, expected)

    def test_change_type_tracked_product(self):
        product = self.env['product.template'].create({
            'name': 'Brand new product',
            'type': 'product',
            'tracking': 'serial',
        })
        product_form = Form(product)
        product_form.detailed_type = 'service'
        product = product_form.save()
        self.assertEqual(product.tracking, 'none')

        product.detailed_type = 'product'
        product.tracking = 'serial'
        self.assertEqual(product.tracking, 'serial')
        # change the type from "product.product" form
        product_form = Form(product.product_variant_id)
        product_form.detailed_type = 'service'
        product = product_form.save()
        self.assertEqual(product.tracking, 'none')

    def test_domain_locations_only_considers_selected_companies(self):
        product = self.env['product.product'].create({'name': 'Product', 'type': 'product'})
        company_a = self.env['res.company'].create({'name': 'Company A'})
        company_b = self.env['res.company'].create({'name': 'Company B'})
        warehouse_a = self.env['stock.warehouse'].create({
            'code': 'WHA', 'company_id': company_a.id
        })
        warehouse_b = self.env['stock.warehouse'].create({
            'code': 'WHB', 'company_id': company_b.id
        })
        self.env['stock.quant'].create([
            {'product_id': product.id, 'location_id': warehouse_a.lot_stock_id.id, 'quantity': 1},
            {'product_id': product.id, 'location_id': warehouse_b.lot_stock_id.id, 'quantity': 2},
        ])

        self.assertEqual(product.sudo().with_context(
            allowed_company_ids=[company_a.id]
        ).qty_available, 1)
        self.assertEqual(product.sudo().with_context(
            allowed_company_ids=[company_b.id]
        ).qty_available, 2)
        self.assertEqual(product.sudo().with_context(
            allowed_company_ids=[company_a.id, company_b.id]
        ).qty_available, 3)

    def test_change_product_type_archived_product(self):
        self.picking_out.action_confirm()
        self.picking_out.action_assign()
        # At this point product_3 should have the quantity reserved
        self.product_3.active = False

        # Should not be possible to change the product type when quantities are reserved
        with self.assertRaises(UserError):
            self.product_3.write({'type': 'consu'})

        # Should not be possible to change the product type when moves are done.
        self.picking_out.button_validate()
        with self.assertRaises(UserError):
            self.product_3.write({'type': 'consu'})
