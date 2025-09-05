# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo.addons.stock.tests.common import TestStockCommon

from odoo import fields
from odoo.fields import Command
from odoo.tests import Form


class TestReplenishWizard(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env['res.partner'].create(dict(name='The Replenisher'))
        cls.product1_price = 500

        # Create a supplier info witch the previous vendor
        cls.supplierinfo = cls.env['product.supplierinfo'].create({
            'partner_id': cls.vendor.id,
            'price': cls.product1_price,
        })

        # Create a product with the 'buy' route and
        # the 'supplierinfo' prevously created
        cls.product1 = cls.env['product.product'].create({
            'name': 'product a',
            'is_storable': True,
            'categ_id': cls.env.ref('product.product_category_all').id,
            'seller_ids': [(4, cls.supplierinfo.id, 0)],
            'route_ids': [(4, cls.env.ref('purchase_stock.route_warehouse0_buy').id, 0)],
        })

        # Additional Values required by the replenish wizard
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.wh = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.user.id)], limit=1)

    def test_replenish_buy_1(self):
        """ Set a quantity to replenish via the "Buy" route and check if
        a purchase order is created with the correct values
        """
        self.product_uom_qty = 42

        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=self.product1.product_tmpl_id.id).create({
            'product_id': self.product1.id,
            'product_tmpl_id': self.product1.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'quantity': self.product_uom_qty,
            'warehouse_id': self.wh.id,
        })
        genrated_picking = replenish_wizard.launch_replenishment()
        links = genrated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        purchase_order_id, model_name = self.url_extract_rec_id_and_model(url)

        last_po_id = False
        if purchase_order_id and model_name:
            last_po_id = self.env[model_name].browse(int(purchase_order_id))
        self.assertTrue(last_po_id, 'Purchase Order not found')
        order_line = last_po_id.order_line.search([('product_id', '=', self.product1.id)])
        self.assertTrue(order_line, 'The product is not in the Purchase Order')
        self.assertEqual(order_line.product_qty, self.product_uom_qty, 'Quantities does not match')
        self.assertEqual(order_line.price_unit, self.product1_price, 'Prices does not match')

    def test_chose_supplier_1(self):
        """ Choose supplier based on the ordered quantity and minimum price

        replenish 10

        1)seq1 vendor1 140 min qty 1
        2)seq2 vendor1 100  min qty 10
        -> 2) should be chosen
        """
        product_to_buy = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'route_ids': [(4, self.env.ref('purchase_stock.route_warehouse0_buy').id, 0)],
        })
        vendor1 = self.env['res.partner'].create({'name': 'vendor1', 'email': 'from.test@example.com'})

        supplierinfo1 = self.env['product.supplierinfo'].create({
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'partner_id': vendor1.id,
            'min_qty': 1,
            'price': 140,
            'sequence': 1,
        })
        supplierinfo2 = self.env['product.supplierinfo'].create({
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'partner_id': vendor1.id,
            'min_qty': 10,
            'price': 100,
            'sequence': 2,
        })

        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=product_to_buy.product_tmpl_id.id).create({
            'product_id': product_to_buy.id,
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'quantity': 10,
            'warehouse_id': self.wh.id,
        })
        genrated_picking = replenish_wizard.launch_replenishment()
        links = genrated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        purchase_order_id, model_name = self.url_extract_rec_id_and_model(url)

        last_po_id = False
        if purchase_order_id and model_name:
            last_po_id = self.env[model_name].browse(int(purchase_order_id))
        self.assertEqual(last_po_id.partner_id, vendor1)
        self.assertEqual(last_po_id.order_line.price_unit, 100)

    def test_chose_supplier_2(self):
        """ Choose supplier based on the ordered quantity and minimum price

        replenish 10

        1)seq1 vendor1 140 min qty 1
        2)seq2 vendor2 90  min qty 10
        3)seq3 vendor1 100 min qty 10
        -> 3) should be chosen
        """
        product_to_buy = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'route_ids': [(4, self.env.ref('purchase_stock.route_warehouse0_buy').id, 0)],
        })
        vendor1 = self.env['res.partner'].create({'name': 'vendor1', 'email': 'from.test@example.com'})
        vendor2 = self.env['res.partner'].create({'name': 'vendor2', 'email': 'from.test2@example.com'})

        supplierinfo1 = self.env['product.supplierinfo'].create({
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'partner_id': vendor1.id,
            'min_qty': 1,
            'price': 140,
            'sequence': 1,
        })
        supplierinfo2 = self.env['product.supplierinfo'].create({
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'partner_id': vendor2.id,
            'min_qty': 10,
            'price': 90,
            'sequence': 2,
        })
        supplierinfo3 = self.env['product.supplierinfo'].create({
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'partner_id': vendor1.id,
            'min_qty': 10,
            'price': 100,
            'sequence': 3,
        })

        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=product_to_buy.product_tmpl_id.id).create({
            'product_id': product_to_buy.id,
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'quantity': 10,
            'warehouse_id': self.wh.id,
        })
        genrated_picking = replenish_wizard.launch_replenishment()
        links = genrated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        purchase_order_id, model_name = self.url_extract_rec_id_and_model(url)

        last_po_id = False
        if purchase_order_id and model_name:
            last_po_id = self.env[model_name].browse(int(purchase_order_id))
        self.assertEqual(last_po_id.partner_id, vendor1)
        self.assertEqual(last_po_id.order_line.price_unit, 100)

    def test_chose_supplier_3(self):
        """ Choose supplier based on the ordered quantity and minimum price

        replenish 10

        1)seq2 vendor1 50
        2)seq1 vendor2 50
        -> 2) should be chosen
        """
        product_to_buy = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'route_ids': [(4, self.env.ref('purchase_stock.route_warehouse0_buy').id, 0)],
        })
        vendor1 = self.env['res.partner'].create({'name': 'vendor1', 'email': 'from.test@example.com'})
        vendor2 = self.env['res.partner'].create({'name': 'vendor2', 'email': 'from.test2@example.com'})

        supplierinfo1 = self.env['product.supplierinfo'].create({
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'partner_id': vendor1.id,
            'price': 50,
            'sequence': 2,
        })
        supplierinfo2 = self.env['product.supplierinfo'].create({
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'partner_id': vendor2.id,
            'price': 50,
            'sequence': 1,
        })

        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=product_to_buy.product_tmpl_id.id).create({
            'product_id': product_to_buy.id,
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'quantity': 10,
            'warehouse_id': self.wh.id,
        })
        genrated_picking = replenish_wizard.launch_replenishment()
        links = genrated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        purchase_order_id, model_name = self.url_extract_rec_id_and_model(url)

        last_po_id = False
        if purchase_order_id and model_name:
            last_po_id = self.env[model_name].browse(int(purchase_order_id))

        self.assertEqual(last_po_id.partner_id, vendor2)

    def test_chose_supplier_4(self):
        """ Choose supplier based on the ordered quantity and minimum price

        replenish 10

        1)seq1 vendor1 100 min qty 2
        2)seq2 vendor1 60 min qty 10
        2)seq3 vendor1 80 min qty 5
        -> 2) should be chosen
        """
        product_to_buy = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'route_ids': [(4, self.env.ref('purchase_stock.route_warehouse0_buy').id, 0)],
        })
        vendor1 = self.env['res.partner'].create({'name': 'vendor1', 'email': 'from.test@example.com'})
        supplierinfo1 = self.env['product.supplierinfo'].create({
            'partner_id': vendor1.id,
            'price': 100,
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'min_qty': 2
        })
        supplierinfo2 = self.env['product.supplierinfo'].create({
            'partner_id': vendor1.id,
            'price': 60,
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'min_qty': 10
        })
        supplierinfo3 = self.env['product.supplierinfo'].create({
            'partner_id': vendor1.id,
            'price': 80,
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'min_qty': 5
        })
        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=product_to_buy.product_tmpl_id.id).create({
            'product_id': product_to_buy.id,
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'quantity': 10,
            'warehouse_id': self.wh.id,
        })
        genrated_picking = replenish_wizard.launch_replenishment()
        links = genrated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        purchase_order_id, model_name = self.url_extract_rec_id_and_model(url)

        last_po_id = False
        if purchase_order_id and model_name:
            last_po_id = self.env[model_name].browse(int(purchase_order_id))

        self.assertEqual(last_po_id.partner_id, vendor1)
        self.assertEqual(last_po_id.order_line.price_unit, 60)

    def test_chose_supplier_5(self):
        """ Choose supplier based on discounted price
        replenish 1

        1)seq1 vendor 100 discount 10%
        2)seq2 vendor 110 discount 20%
        -> 2) should be chosen
        """
        self.supplierinfo.product_tmpl_id = self.product1.product_tmpl_id.id
        self.supplierinfo.price = 100
        self.supplierinfo.discount = 10.0

        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.product1.product_tmpl_id.id,
            'partner_id': self.vendor.id,
            'price': 110,
            'discount': 20.0,
        })

        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=self.product1.product_tmpl_id.id).create({
            'product_id': self.product1.id,
            'product_tmpl_id': self.product1.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'quantity': 1,
            'warehouse_id': self.wh.id,
        })
        generated_picking = replenish_wizard.launch_replenishment()
        links = generated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        purchase_order_id, model_name = self.url_extract_rec_id_and_model(url)

        last_po_id = False
        if purchase_order_id and model_name:
            last_po_id = self.env[model_name].browse(int(purchase_order_id))
        self.assertEqual(last_po_id.partner_id, self.vendor)
        self.assertEqual(last_po_id.order_line.price_unit, 110)
        self.assertEqual(last_po_id.order_line.discount, 20.0)

    def test_supplier_delay(self):
        product_to_buy = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'route_ids': [(4, self.env.ref('purchase_stock.route_warehouse0_buy').id, 0)],
        })
        vendor1 = self.env['res.partner'].create({'name': 'vendor1', 'email': 'from.test@example.com'})
        supplier_delay = self.env['product.supplierinfo'].create({
            'partner_id': vendor1.id,
            'price': 100,
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'min_qty': 2,
            'delay': 3
        })
        supplier_no_delay = self.env['product.supplierinfo'].create({
            'partner_id': vendor1.id,
            'price': 100,
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'min_qty': 2,
            'delay' : 0
        })
        with freeze_time("2023-01-01"):
            wizard = self.env['product.replenish'].create({
                'product_id': product_to_buy.id,
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'product_uom_id': self.uom_unit.id,
                'quantity': 1,
                'warehouse_id': self.wh.id,
                'route_id': self.env.ref('purchase_stock.route_warehouse0_buy').id
            })
            wizard.supplier_id = supplier_no_delay
            self.assertEqual(fields.Datetime.from_string('2023-01-01 00:00:00'), wizard.date_planned)
            wizard.supplier_id = supplier_delay
            self.assertEqual(fields.Datetime.from_string('2023-01-04 00:00:00'), wizard.date_planned)

    def test_purchase_delay(self):
        product_to_buy = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'route_ids': [(4, self.env.ref('purchase_stock.route_warehouse0_buy').id, 0)],
        })
        vendor = self.env['res.partner'].create({'name': 'vendor1', 'email': 'from.test@example.com'})
        supplier1 = self.env['product.supplierinfo'].create({
            'partner_id': vendor.id,
            'price': 100,
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'min_qty': 2,
            'delay': 0
        })
        supplier2 = self.env['product.supplierinfo'].create({
            'partner_id': vendor.id,
            'price': 100,
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'min_qty': 2,
            'delay' : 0
        })
        self.env['ir.config_parameter'].sudo().set_param('purchase.use_po_lead', True)
        self.env.company.days_to_purchase = 0

        with freeze_time("2023-01-01"):
            wizard = self.env['product.replenish'].create({
                'product_id': product_to_buy.id,
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'product_uom_id': self.uom_unit.id,
                'quantity': 1,
                'warehouse_id': self.wh.id,
                'route_id': self.env.ref('purchase_stock.route_warehouse0_buy').id
            })
            wizard.supplier_id = supplier1
            self.assertEqual(fields.Datetime.from_string('2023-01-01 00:00:00'), wizard.date_planned)
            self.env.company.days_to_purchase = 5
            # change the supplier to trigger the date computation
            wizard.supplier_id = supplier2
            self.assertEqual(fields.Datetime.from_string('2023-01-06 00:00:00'), wizard.date_planned)

    def test_purchase_supplier_route_delay(self):
        product_to_buy = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'route_ids': [(4, self.env.ref('purchase_stock.route_warehouse0_buy').id, 0)],
        })
        vendor = self.env['res.partner'].create({'name': 'vendor1', 'email': 'from.test@example.com'})
        supplier = self.env['product.supplierinfo'].create({
            'partner_id': vendor.id,
            'price': 100,
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'min_qty': 2,
            'delay': 2
        })
        self.env['ir.config_parameter'].sudo().set_param('purchase.use_po_lead', True)
        self.env.company.days_to_purchase = 5

        with freeze_time("2023-01-01"):
            wizard = self.env['product.replenish'].create({
                'product_id': product_to_buy.id,
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'product_uom_id': self.uom_unit.id,
                'quantity': 1,
                'warehouse_id': self.wh.id,
                'route_id': self.env.ref('purchase_stock.route_warehouse0_buy').id
            })
            wizard.supplier_id = supplier
            self.assertEqual(fields.Datetime.from_string('2023-01-08 00:00:00'), wizard.date_planned)

    def test_unit_price_expired_price_list(self):
        vendor = self.env['res.partner'].create({
            'name': 'Contact',
            'type': 'contact',
        })
        product = self.env['product.product'].create({
            'name': 'Product',
            'standard_price': 60,
            'seller_ids': [(0, 0, {
                'partner_id': vendor.id,
                'price': 1.0,
                'date_end': '2019-01-01',
            })],
            'route_ids': [(6, 0, [
                self.env.ref('purchase_stock.route_warehouse0_buy').id
            ])],
        })

        replenish_wizard = self.env['product.replenish'].create({
            'product_id': product.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'quantity': 1,
            'warehouse_id': self.wh.id,
            'route_id': self.env.ref('purchase_stock.route_warehouse0_buy').id
        })
        replenish_wizard.launch_replenishment()
        last_po_id = self.env['purchase.order'].search([
            ('origin', 'ilike', '%Manual Replenishment%'),
        ])[-1]

        self.assertEqual(last_po_id.partner_id, vendor)
        self.assertEqual(last_po_id.order_line.price_unit, 0)

    def test_correct_supplier(self):
        """
        Check that the supplier provided to a replenishment wizard is taken into account
        for buy + pull routes (e.g. corresponding to the 'old' buy + receipt in 2 steps)
        """
        company = self.env.company
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
        buy_pull_route = self.env['stock.route'].create({
            'name': 'Custom buy pull route',
            'rule_ids': [
                Command.create({
                    'name': 'Buy to Input',
                    'action': 'buy',
                    'picking_type_id': warehouse.in_type_id.id,
                    'location_dest_id': warehouse.wh_input_stock_loc_id.id,
                    'company_id': company.id,
                    'propagate_cancel': True,
                }),
                Command.create({
                    'name': 'Input to Stock',
                    'action': 'pull',
                    'picking_type_id': warehouse.int_type_id.id,
                    'location_src_id': warehouse.wh_input_stock_loc_id.id,
                    'location_dest_id': warehouse.lot_stock_id.id,
                    'procure_method': 'make_to_order',
                    'company_id': company.id,
                })
            ]
        })
        product = self.env['product.product'].create({
            'name': 'Product',
            'route_ids': [Command.set(buy_pull_route.ids)],
        })
        partner_a, partner_b = self.env['res.partner'].create([
            {'name': "partner_a"},
            {'name': "partner_b"},
        ])
        self.env['product.supplierinfo'].create([{
            'partner_id': partner_a.id,
            'product_id': product.id,
            'price': 1.0,
            'date_end': '2026-01-01',
        }, {
            'partner_id': partner_b.id,
            'product_id': product.id,
            'price': 10.0,
            'date_end': '2999-01-01',
        }, {
            'partner_id': partner_b.id,
            'product_id': product.id,
            'price': 100.0,
            'date_end': '2999-01-01',
        }])

        replenish_wizard = self.env['product.replenish'].create({
            'product_id': product.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'quantity': 1,
            'warehouse_id': self.wh.id,
            'route_id': buy_pull_route.id,
            'supplier_id': product.seller_ids[2].id  # partner_b price 100$
        })
        replenish_wizard.launch_replenishment()
        po = self.env['purchase.order'].search([('partner_id', '=', partner_b.id)], limit=1)
        self.assertEqual(po.amount_untaxed, 10, "best price is 10$")

    def test_delete_buy_route_and_replenish(self):
        """ Test that the replenish wizard does not crash when the 'buy' route is deleted """
        self.env.ref('purchase_stock.route_warehouse0_buy', raise_if_not_found=False).unlink()
        self.product1.product_tmpl_id.seller_ids.unlink()
        replenish_wizard = self.env['product.replenish'].create({
            'product_id': self.product1.id,
            'product_tmpl_id': self.product1.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
        })
        self.assertTrue(replenish_wizard._get_route_domain(self.product1.product_tmpl_id))

    def test_inter_wh_replenish(self):
        """ Test that the replenish order has the correct supplier in a replenish between
        warehouses of the same company.
        """
        main_warehouse = self.wh
        second_warehouse = self.env['stock.warehouse'].create({
            'name': 'Second Warehouse',
            'code': 'WH02',
        })
        main_warehouse.write({
            'resupply_wh_ids': [Command.set(second_warehouse.ids)]
        })
        interwh_route = self.env['stock.route'].search([('supplied_wh_id', '=', main_warehouse.id), ('supplier_wh_id', '=', second_warehouse.id)])

        self.product1.route_ids = [Command.link(interwh_route.id)]

        wizard_form = Form(self.env['product.replenish'].with_context(default_product_tmpl_id=self.product1.product_tmpl_id.id))
        wizard_form.route_id = interwh_route
        wizard = wizard_form.save()
        generated_picking = wizard.launch_replenishment()
        links = generated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        stock_picking_id, model_name = self.url_extract_rec_id_and_model(url)

        stock_picking = self.env[model_name].browse(int(stock_picking_id))

        self.assertEqual(stock_picking.partner_id, second_warehouse.partner_id)
