# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo import fields
from odoo.fields import Command
from odoo.tests import tagged, Form
from .common import PurchaseTestCommon


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestReplenishWizard(PurchaseTestCommon):
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env['res.partner'].create(dict(name='The Replenisher'))
        cls.product1_price = 500

        # Create a product with the 'buy' route and
        # the 'supplierinfo' prevously created
        cls.product1 = cls.env['product.product'].create({
            'name': 'product a',
            'is_storable': True,
            'route_ids': [Command.link(cls.route_buy.id)],
        })
        # Create a supplier info witch the previous vendor
        cls.supplierinfo = cls.env['product.supplierinfo'].create({
            'product_id': cls.product1.id,
            'partner_id': cls.vendor.id,
            'price': cls.product1_price,
        })

        cls.vendor1, cls.vendor2 = cls.env['res.partner'].create([
            {'name': 'vendor1', 'email': 'from.test@example.com'},
            {'name': 'vendor2', 'email': 'from.test2@example.com'}
        ])

        # Additional Values required by the replenish wizard
        cls.uom_pack_6 = cls.env.ref('uom.product_uom_pack_6')

    def _get_purchase_order_from_replenishment(self, replenish_wizard):
        notification = replenish_wizard.launch_replenishment()
        links = notification.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        purchase_order_id, model_name = self.url_extract_rec_id_and_model(url)

        assert (purchase_order_id and model_name == 'purchase.order'), "replenishment didn't return a link to a purchase order"
        return self.env[model_name].browse(int(purchase_order_id))

||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env['res.partner'].create(dict(name='The Replenisher'))
        cls.product1_price = 500

        # Create a product with the 'buy' route and
        # the 'supplierinfo' prevously created
        cls.product1 = cls.env['product.product'].create({
            'name': 'product a',
            'is_storable': True,
            'route_ids': [Command.link(cls.route_buy.id)],
        })
        # Create a supplier info witch the previous vendor
        cls.supplierinfo = cls.env['product.supplierinfo'].create({
            'product_id': cls.product1.id,
            'partner_id': cls.vendor.id,
            'price': cls.product1_price,
        })

        # Additional Values required by the replenish wizard
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_pack_6 = cls.env.ref('uom.product_uom_pack_6')
        cls.wh = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.user.id)], limit=1)

=======
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
    def test_replenish_buy_1(self):
        """ Set a quantity to replenish via the "Buy" route and check if
        a purchase order is created with the correct values
        """
        self.product_uom_qty = 42
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        # Even though product1 doesn't have the 'Buy' route enabled, as it is enable through the wh it should pick it up regardless.
        self.warehouse_1.buy_to_resupply = True
        self.product1.route_ids = [Command.clear()]

        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=self.product1.product_tmpl_id.id).create({
            'product_id': self.product1.id,
            'product_tmpl_id': self.product1.product_tmpl_id.id,
            'uom_id': self.uom_unit.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        # Even though product1 doesn't have the 'Buy' route enabled, as it is enable through the wh it should pick it up regardless.
        self.wh.buy_to_resupply = True
        self.product1.route_ids = [Command.clear()]

        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=self.product1.product_tmpl_id.id).create({
            'product_id': self.product1.id,
            'product_tmpl_id': self.product1.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
=======
        self._use_route_buy(self.product)
        self.product.seller_ids.price = 10
        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=self.product.product_tmpl_id.id).create({
            'product_id': self.product.id,
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'product_uom_id': self.uom.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
            'quantity': self.product_uom_qty,
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'warehouse_id': self.warehouse_1.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'warehouse_id': self.wh.id,
=======
            'warehouse_id': self.warehouse.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
        })
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        po = self._get_purchase_order_from_replenishment(replenish_wizard)
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        genrated_picking = replenish_wizard.launch_replenishment()
        links = genrated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        purchase_order_id, model_name = self.url_extract_rec_id_and_model(url)
=======
        genrated_picking = replenish_wizard.launch_replenishment()
        links = genrated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        purchase_order_id, model_name = self._url_extract_rec_id_and_model(url)
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4

<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        self.assertTrue(po, 'Purchase Order not found')
        order_line = po.order_line.search([('product_id', '=', self.product1.id)])
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        last_po_id = False
        if purchase_order_id and model_name:
            last_po_id = self.env[model_name].browse(int(purchase_order_id))
        self.assertTrue(last_po_id, 'Purchase Order not found')
        order_line = last_po_id.order_line.search([('product_id', '=', self.product1.id)])
=======
        last_po_id = False
        if purchase_order_id and model_name:
            last_po_id = self.env[model_name].browse(int(purchase_order_id))
        self.assertTrue(last_po_id, 'Purchase Order not found')
        order_line = last_po_id.order_line.search([('product_id', '=', self.product.id)])
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
        self.assertTrue(order_line, 'The product is not in the Purchase Order')
        self.assertEqual(order_line.product_qty, self.product_uom_qty, 'Quantities does not match')
        self.assertEqual(order_line.price_unit, 10, 'Prices does not match')

    def test_chose_supplier_1(self):
        """ Choose supplier based on the ordered quantity and minimum price

        replenish 10

        1)seq1 vendor1 140 min qty 1
        2)seq2 vendor1 100  min qty 10
        -> 2) should be chosen
        """
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        product_to_buy = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'route_ids': [Command.link(self.route_buy.id)],
        })

        self.env['product.supplierinfo'].create([
            {
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'partner_id': self.vendor1.id,
                'min_qty': 1,
                'price': 140,
                'sequence': 1,
            }, {
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'partner_id': self.vendor1.id,
                'min_qty': 10,
                'price': 100,
                'sequence': 2,
            }
        ])

        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=product_to_buy.product_tmpl_id.id).create({
            'product_id': product_to_buy.id,
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'uom_id': self.uom_unit.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        product_to_buy = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'route_ids': [Command.link(self.route_buy.id)],
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
=======
        self._use_route_buy(self.product, create_seller=False)
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'partner_id': self.vendor.id,
            'min_qty': 1,
            'price': 140,
            'sequence': 1,
        })
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'partner_id': self.vendor.id,
            'min_qty': 10,
            'price': 100,
            'sequence': 2,
        })
        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=self.product.product_tmpl_id.id).create({
            'product_id': self.product.id,
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'product_uom_id': self.uom.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
            'quantity': 10,
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'warehouse_id': self.warehouse_1.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'warehouse_id': self.wh.id,
=======
            'warehouse_id': self.warehouse.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
        })
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        po = self._get_purchase_order_from_replenishment(replenish_wizard)
        self.assertEqual(po.partner_id, self.vendor1)
        self.assertEqual(po.order_line.price_unit, 100)
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        genrated_picking = replenish_wizard.launch_replenishment()
        links = genrated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        purchase_order_id, model_name = self.url_extract_rec_id_and_model(url)

        last_po_id = False
        if purchase_order_id and model_name:
            last_po_id = self.env[model_name].browse(int(purchase_order_id))
        self.assertEqual(last_po_id.partner_id, vendor1)
        self.assertEqual(last_po_id.order_line.price_unit, 100)
=======
        genrated_picking = replenish_wizard.launch_replenishment()
        links = genrated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        purchase_order_id, model_name = self._url_extract_rec_id_and_model(url)

        last_po_id = False
        if purchase_order_id and model_name:
            last_po_id = self.env[model_name].browse(int(purchase_order_id))
        self.assertEqual(last_po_id.partner_id, self.vendor)
        self.assertEqual(last_po_id.order_line.price_unit, 100)
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4

    def test_chose_supplier_2(self):
        """ Choose supplier based on the ordered quantity and minimum price

        replenish 10

        1)seq1 vendor1 140 min qty 1
        2)seq2 vendor2 90  min qty 10
        3)seq3 vendor1 100 min qty 10
        -> 2) should be chosen
        """
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        product_to_buy = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'route_ids': [Command.link(self.route_buy.id)],
        })
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        product_to_buy = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'route_ids': [Command.link(self.route_buy.id)],
        })
        vendor1 = self.env['res.partner'].create({'name': 'vendor1', 'email': 'from.test@example.com'})
        vendor2 = self.env['res.partner'].create({'name': 'vendor2', 'email': 'from.test2@example.com'})
=======
        self._use_route_buy(self.product, create_seller=False)

        vendor1 = self.env['res.partner'].create({'name': 'vendor1', 'email': 'from.test@example.com'})
        vendor2 = self.env['res.partner'].create({'name': 'vendor2', 'email': 'from.test2@example.com'})
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4

<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        self.env['product.supplierinfo'].create([
            {
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'partner_id': self.vendor1.id,
                'min_qty': 1,
                'price': 140,
                'sequence': 1,
            }, {
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'partner_id': self.vendor2.id,
                'min_qty': 10,
                'price': 90,
                'sequence': 2,
            }, {
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'partner_id': self.vendor1.id,
                'min_qty': 10,
                'price': 100,
                'sequence': 3,
            }
        ])
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
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
=======
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'partner_id': vendor1.id,
            'min_qty': 1,
            'price': 140,
            'sequence': 1,
        })
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'partner_id': vendor2.id,
            'min_qty': 10,
            'price': 90,
            'sequence': 2,
        })
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'partner_id': vendor1.id,
            'min_qty': 10,
            'price': 100,
            'sequence': 3,
        })
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4

<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=product_to_buy.product_tmpl_id.id).create({
            'product_id': product_to_buy.id,
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'uom_id': self.uom_unit.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=product_to_buy.product_tmpl_id.id).create({
            'product_id': product_to_buy.id,
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
=======
        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=self.product.product_tmpl_id.id).create({
            'product_id': self.product.id,
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'product_uom_id': self.uom.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
            'quantity': 10,
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'warehouse_id': self.warehouse_1.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'warehouse_id': self.wh.id,
=======
            'warehouse_id': self.warehouse.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
        })
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        po = self._get_purchase_order_from_replenishment(replenish_wizard)
        self.assertEqual(po.partner_id, self.vendor2)
        self.assertEqual(po.order_line.price_unit, 90)
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        genrated_picking = replenish_wizard.launch_replenishment()
        links = genrated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        purchase_order_id, model_name = self.url_extract_rec_id_and_model(url)

        last_po_id = False
        if purchase_order_id and model_name:
            last_po_id = self.env[model_name].browse(int(purchase_order_id))
        self.assertEqual(last_po_id.partner_id, vendor1)
        self.assertEqual(last_po_id.order_line.price_unit, 100)
=======
        genrated_picking = replenish_wizard.launch_replenishment()
        links = genrated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        purchase_order_id, model_name = self._url_extract_rec_id_and_model(url)

        last_po_id = False
        if purchase_order_id and model_name:
            last_po_id = self.env[model_name].browse(int(purchase_order_id))
        self.assertEqual(last_po_id.partner_id, vendor1)
        self.assertEqual(last_po_id.order_line.price_unit, 100)
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4

    def test_chose_supplier_3(self):
        """ Choose supplier based on the ordered quantity and minimum price

        replenish 10

        1)seq2 vendor1 50
        2)seq1 vendor2 50
        -> 2) should be chosen
        """
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        product_to_buy = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'route_ids': [Command.link(self.route_buy.id)],
        })
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        product_to_buy = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'route_ids': [Command.link(self.route_buy.id)],
        })
        vendor1 = self.env['res.partner'].create({'name': 'vendor1', 'email': 'from.test@example.com'})
        vendor2 = self.env['res.partner'].create({'name': 'vendor2', 'email': 'from.test2@example.com'})
=======
        self._use_route_buy(self.product, create_seller=False)
        vendor1 = self.env['res.partner'].create({'name': 'vendor1', 'email': 'from.test@example.com'})
        vendor2 = self.env['res.partner'].create({'name': 'vendor2', 'email': 'from.test2@example.com'})
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4

<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        self.env['product.supplierinfo'].create([
            {
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'partner_id': self.vendor1.id,
                'price': 50,
                'sequence': 2,
            }, {
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'partner_id': self.vendor2.id,
                'price': 50,
                'sequence': 1,
            }
        ])
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
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
=======
        supplierinfo1 = self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'partner_id': vendor1.id,
            'price': 50,
            'sequence': 2,
        })
        supplierinfo2 = self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'partner_id': vendor2.id,
            'price': 50,
            'sequence': 1,
        })
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4

<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=product_to_buy.product_tmpl_id.id).create({
            'product_id': product_to_buy.id,
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'uom_id': self.uom_unit.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=product_to_buy.product_tmpl_id.id).create({
            'product_id': product_to_buy.id,
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
=======
        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=self.product.product_tmpl_id.id).create({
            'product_id': self.product.id,
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'product_uom_id': self.uom.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
            'quantity': 10,
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'warehouse_id': self.warehouse_1.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'warehouse_id': self.wh.id,
=======
            'warehouse_id': self.warehouse.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
        })
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        po = self._get_purchase_order_from_replenishment(replenish_wizard)
        self.assertEqual(po.partner_id, self.vendor2)
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        genrated_picking = replenish_wizard.launch_replenishment()
        links = genrated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        purchase_order_id, model_name = self.url_extract_rec_id_and_model(url)

        last_po_id = False
        if purchase_order_id and model_name:
            last_po_id = self.env[model_name].browse(int(purchase_order_id))

        self.assertEqual(last_po_id.partner_id, vendor2)
=======
        genrated_picking = replenish_wizard.launch_replenishment()
        links = genrated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        purchase_order_id, model_name = self._url_extract_rec_id_and_model(url)

        last_po_id = False
        if purchase_order_id and model_name:
            last_po_id = self.env[model_name].browse(int(purchase_order_id))

        self.assertEqual(last_po_id.partner_id, vendor2)
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4

    def test_chose_supplier_4(self):
        """ Choose supplier based on the ordered quantity and minimum price

        replenish 10

        1)seq1 vendor1 100 min qty 2
        2)seq2 vendor1 60 min qty 10
        2)seq3 vendor1 80 min qty 5
        -> 2) should be chosen
        """
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        product_to_buy = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'route_ids': [Command.link(self.route_buy.id)],
        })

        self.env['product.supplierinfo'].create([
            {
                'partner_id': self.vendor1.id,
                'price': 100,
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'min_qty': 2
            }, {
                'partner_id': self.vendor1.id,
                'price': 60,
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'min_qty': 10
            }, {
                'partner_id': self.vendor1.id,
                'price': 80,
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'min_qty': 5
            }
        ])

        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=product_to_buy.product_tmpl_id.id).create({
            'product_id': product_to_buy.id,
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'uom_id': self.uom_unit.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        product_to_buy = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'route_ids': [Command.link(self.route_buy.id)],
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
=======
        self._use_route_buy(self.product, create_seller=False)
        supplierinfo1 = self.env['product.supplierinfo'].create({
            'partner_id': self.vendor.id,
            'price': 100,
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'min_qty': 2
        })
        supplierinfo2 = self.env['product.supplierinfo'].create({
            'partner_id': self.vendor.id,
            'price': 60,
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'min_qty': 10
        })
        supplierinfo3 = self.env['product.supplierinfo'].create({
            'partner_id': self.vendor.id,
            'price': 80,
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'min_qty': 5
        })
        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=self.product.product_tmpl_id.id).create({
            'product_id': self.product.id,
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'product_uom_id': self.uom.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
            'quantity': 10,
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'warehouse_id': self.warehouse_1.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'warehouse_id': self.wh.id,
=======
            'warehouse_id': self.warehouse.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
        })
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        po = self._get_purchase_order_from_replenishment(replenish_wizard)
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        genrated_picking = replenish_wizard.launch_replenishment()
        links = genrated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        purchase_order_id, model_name = self.url_extract_rec_id_and_model(url)
=======
        genrated_picking = replenish_wizard.launch_replenishment()
        links = genrated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        purchase_order_id, model_name = self._url_extract_rec_id_and_model(url)
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4

<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        self.assertEqual(po.partner_id, self.vendor1)
        self.assertEqual(po.order_line.price_unit, 60)
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        last_po_id = False
        if purchase_order_id and model_name:
            last_po_id = self.env[model_name].browse(int(purchase_order_id))

        self.assertEqual(last_po_id.partner_id, vendor1)
        self.assertEqual(last_po_id.order_line.price_unit, 60)
=======
        last_po_id = False
        if purchase_order_id and model_name:
            last_po_id = self.env[model_name].browse(int(purchase_order_id))

        self.assertEqual(last_po_id.partner_id, self.vendor)
        self.assertEqual(last_po_id.order_line.price_unit, 60)
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4

    def test_chose_supplier_5(self):
        """ Choose supplier based on discounted price
        replenish 1

        1)seq1 vendor 100 discount 10%
        2)seq2 vendor 110 discount 20%
        -> 2) should be chosen
        """
        self._use_route_buy(self.product, create_seller=False)
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'partner_id': self.vendor.id,
            'price': 100,
            'discount': 10.0,
        })

        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'partner_id': self.vendor.id,
            'price': 110,
            'discount': 20.0,
        })

<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=self.product1.product_tmpl_id.id).create({
            'product_id': self.product1.id,
            'product_tmpl_id': self.product1.product_tmpl_id.id,
            'uom_id': self.uom_unit.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=self.product1.product_tmpl_id.id).create({
            'product_id': self.product1.id,
            'product_tmpl_id': self.product1.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
=======
        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=self.product.product_tmpl_id.id).create({
            'product_id': self.product.id,
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'product_uom_id': self.uom.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
            'quantity': 1,
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'warehouse_id': self.warehouse_1.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'warehouse_id': self.wh.id,
=======
            'warehouse_id': self.warehouse.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
        })
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        po = self._get_purchase_order_from_replenishment(replenish_wizard)
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        generated_picking = replenish_wizard.launch_replenishment()
        links = generated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        purchase_order_id, model_name = self.url_extract_rec_id_and_model(url)
=======
        generated_picking = replenish_wizard.launch_replenishment()
        links = generated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        purchase_order_id, model_name = self._url_extract_rec_id_and_model(url)
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4

        self.assertEqual(po.partner_id, self.vendor)
        self.assertEqual(po.order_line.price_unit, 110)
        self.assertEqual(po.order_line.discount, 20.0)

    def test_supplier_delay(self):
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        product_to_buy = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'route_ids': [Command.link(self.route_buy.id)],
        })
        supplier_delay, supplier_no_delay = self.env['product.supplierinfo'].create([
            {
                'partner_id': self.vendor1.id,
                'price': 100,
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'min_qty': 2,
                'delay': 3
            }, {
                'partner_id': self.vendor2.id,
                'price': 100,
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'min_qty': 2,
                'delay': 0
            }
        ])
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        product_to_buy = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'route_ids': [Command.link(self.route_buy.id)],
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
=======
        self._use_route_buy(self.product, create_seller=False)
        supplier_delay = self.env['product.supplierinfo'].create({
            'partner_id': self.vendor.id,
            'price': 100,
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'min_qty': 2,
            'delay': 3
        })
        supplier_no_delay = self.env['product.supplierinfo'].create({
            'partner_id': self.vendor.id,
            'price': 100,
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'min_qty': 2,
            'delay' : 0
        })
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
        with freeze_time("2023-01-01"):
            wizard = self.env['product.replenish'].create({
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
                'product_id': product_to_buy.id,
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'uom_id': self.uom_unit.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
                'product_id': product_to_buy.id,
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'product_uom_id': self.uom_unit.id,
=======
                'product_id': self.product.id,
                'product_tmpl_id': self.product.product_tmpl_id.id,
                'product_uom_id': self.uom.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
                'quantity': 1,
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
                'warehouse_id': self.warehouse_1.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
                'warehouse_id': self.wh.id,
=======
                'warehouse_id': self.warehouse.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
                'route_id': self.route_buy.id,
            })
            wizard.partner_id = supplier_no_delay.partner_id
            self.assertEqual(fields.Datetime.from_string('2023-01-01 00:00:00'), wizard.date_planned)
            wizard.partner_id = supplier_delay.partner_id
            self.assertEqual(fields.Datetime.from_string('2023-01-04 00:00:00'), wizard.date_planned)

    def test_purchase_delay(self):
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        product_to_buy = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'route_ids': [Command.link(self.route_buy.id)],
        })

        supplier1, supplier2 = self.env['product.supplierinfo'].create([
            {
                'partner_id': self.vendor1.id,
                'price': 100,
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'min_qty': 2,
                'delay': 0
            },
            {
                'partner_id': self.vendor2.id,
                'price': 100,
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'min_qty': 2,
                'delay': 0
            }
        ])
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        product_to_buy = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'route_ids': [Command.link(self.route_buy.id)],
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
=======
        self._use_route_buy(self.product, create_seller=False)
        supplier1 = self.env['product.supplierinfo'].create({
            'partner_id': self.vendor.id,
            'price': 100,
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'min_qty': 2,
            'delay': 0
        })
        supplier2 = self.env['product.supplierinfo'].create({
            'partner_id': self.vendor.id,
            'price': 100,
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'min_qty': 2,
            'delay' : 0
        })
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
        self.env.company.days_to_purchase = 0

        with freeze_time("2023-01-01"):
            wizard = self.env['product.replenish'].create({
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
                'product_id': product_to_buy.id,
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'uom_id': self.uom_unit.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
                'product_id': product_to_buy.id,
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'product_uom_id': self.uom_unit.id,
=======
                'product_id': self.product.id,
                'product_tmpl_id': self.product.product_tmpl_id.id,
                'product_uom_id': self.uom.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
                'quantity': 1,
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
                'warehouse_id': self.warehouse_1.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
                'warehouse_id': self.wh.id,
=======
                'warehouse_id': self.warehouse.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
                'route_id': self.route_buy.id,
            })
            wizard.partner_id = supplier1.partner_id
            self.assertEqual(fields.Datetime.from_string('2023-01-01 00:00:00'), wizard.date_planned)
            self.env.company.days_to_purchase = 5
            # change the supplier to trigger the date computation
            wizard.partner_id = supplier2.partner_id
            self.assertEqual(fields.Datetime.from_string('2023-01-06 00:00:00'), wizard.date_planned)

    def test_purchase_supplier_route_delay(self):
        self.product = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'route_ids': [Command.link(self.route_buy.id)],
        })
        supplier = self.env['product.supplierinfo'].create({
            'partner_id': self.vendor.id,
            'price': 100,
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'min_qty': 2,
            'delay': 2
        })
        self.env.company.days_to_purchase = 5

        with freeze_time("2023-01-01"):
            wizard = self.env['product.replenish'].create({
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
                'product_id': product_to_buy.id,
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'uom_id': self.uom_unit.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
                'product_id': product_to_buy.id,
                'product_tmpl_id': product_to_buy.product_tmpl_id.id,
                'product_uom_id': self.uom_unit.id,
=======
                'product_id': self.product.id,
                'product_tmpl_id': self.product.product_tmpl_id.id,
                'product_uom_id': self.uom.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
                'quantity': 1,
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
                'warehouse_id': self.warehouse_1.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
                'warehouse_id': self.wh.id,
=======
                'warehouse_id': self.warehouse.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
                'route_id': self.route_buy.id,
            })
            wizard.partner_id = supplier.partner_id
            self.assertEqual(fields.Datetime.from_string('2023-01-08 00:00:00'), wizard.date_planned)

    def test_unit_price_expired_price_list(self):
        product = self.env['product.product'].create({
            'name': 'Product',
            'standard_price': 60,
            'seller_ids': [(0, 0, {
                'partner_id': self.vendor.id,
                'price': 1.0,
                'date_end': '2019-01-01',
            })],
            'route_ids': [Command.set([self.route_buy.id])],
        })

        replenish_wizard = self.env['product.replenish'].create({
            'product_id': product.id,
            'product_tmpl_id': product.product_tmpl_id.id,
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'uom_id': self.uom_unit.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'product_uom_id': self.uom_unit.id,
=======
            'product_uom_id': self.uom.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
            'quantity': 1,
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'warehouse_id': self.warehouse_1.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'warehouse_id': self.wh.id,
=======
            'warehouse_id': self.warehouse.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
            'route_id': self.route_buy.id,
        })
        po = self._get_purchase_order_from_replenishment(replenish_wizard)

        self.assertEqual(po.partner_id, self.vendor)
        self.assertEqual(po.order_line.price_unit, 0)

    def test_correct_supplier(self):
        self.warehouse_1.reception_steps = 'two_steps'
        product = self.env['product.product'].create({
            'name': 'Product',
            'route_ids': [Command.set([self.route_buy.id])],
        })

        self.env['product.supplierinfo'].create([{
            'partner_id': self.vendor1.id,
            'product_id': product.id,
            'price': 1.0,
        }, {
            'partner_id': self.vendor2.id,
            'product_id': product.id,
            'price': 10.0,
        }, {
            'partner_id': self.vendor2.id,
            'product_id': product.id,
            'price': 100.0,
        }])

        replenish_wizard = self.env['product.replenish'].create({
            'product_id': product.id,
            'product_tmpl_id': product.product_tmpl_id.id,
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'uom_id': self.uom_unit.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'product_uom_id': self.uom_unit.id,
=======
            'product_uom_id': self.uom.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
            'quantity': 1,
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'warehouse_id': self.warehouse_1.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'warehouse_id': self.wh.id,
=======
            'warehouse_id': self.warehouse.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
            'route_id': self.route_buy.id,
            'partner_id': self.vendor2.id,  # vendor2 price 100$
        })
        po = self._get_purchase_order_from_replenishment(replenish_wizard)
        self.assertEqual(po.amount_untaxed, 10, "best price is 10$")

    def test_delete_buy_route_and_replenish(self):
        """ Test that the replenish wizard does not crash when the 'buy' route is deleted """
        self.env.ref('purchase_stock.route_warehouse0_buy', raise_if_not_found=False).unlink()
        replenish_wizard = self.env['product.replenish'].create({
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'product_id': self.product1.id,
            'product_tmpl_id': self.product1.product_tmpl_id.id,
            'uom_id': self.uom_unit.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'product_id': self.product1.id,
            'product_tmpl_id': self.product1.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
=======
            'product_id': self.product.id,
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'product_uom_id': self.uom.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
        })
        self.assertTrue(replenish_wizard._get_route_domain(self.product.product_tmpl_id))

    def test_inter_wh_replenish(self):
        """ Test that the replenish order has the correct supplier in a replenish between
        warehouses of the same company.
        """
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        main_warehouse = self.warehouse_1
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        main_warehouse = self.wh
=======
        main_warehouse = self.warehouse
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
        second_warehouse = self.env['stock.warehouse'].create({
            'name': 'Second Warehouse',
            'code': 'WH02',
        })
        main_warehouse.write({
            'resupply_wh_ids': [Command.set(second_warehouse.ids)]
        })
        interwh_route = self.env['stock.route'].search([('supplied_wh_id', '=', main_warehouse.id), ('supplier_wh_id', '=', second_warehouse.id)])

        self.product.route_ids = [Command.link(interwh_route.id)]

        wizard_form = Form(self.env['product.replenish'].with_context(default_product_tmpl_id=self.product.product_tmpl_id.id))
        wizard_form.route_id = interwh_route
        wizard = wizard_form.save()
        generated_picking = wizard.launch_replenishment()
        links = generated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        stock_picking_id, model_name = self._url_extract_rec_id_and_model(url)

        stock_picking = self.env[model_name].browse(int(stock_picking_id))

        self.assertEqual(stock_picking.partner_id, second_warehouse.partner_id)

    def test_purchase_order_uom(self):
        self._use_route_buy(self.product, create_seller=False)
        price_list_uom, price_list_pack_of_6 = self.env['product.supplierinfo'].create([{
            'partner_id': self.vendor.id,
            'product_id': self.product.id,
            'price': 1.0,
            'product_uom_id': self.uom.id,
        }, {
            'partner_id': self.vendor.id,
            'product_id': self.product.id,
            'price': 5.0,
            'product_uom_id': self.uom_pack_of_6.id,
            'min_qty': 2,
        }])

        replenish_wizard = self.env['product.replenish'].create({
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'product_id': self.fuzzy_drink.id,
            'product_tmpl_id': self.fuzzy_drink.product_tmpl_id.id,
            'uom_id': self.uom_unit.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'product_id': self.fuzzy_drink.id,
            'product_tmpl_id': self.fuzzy_drink.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
=======
            'product_id': self.product.id,
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'product_uom_id': self.uom.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
            'quantity': 10,
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'warehouse_id': self.warehouse_1.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'warehouse_id': self.wh.id,
=======
            'warehouse_id': self.warehouse.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
            'route_id': self.env.ref('purchase_stock.route_warehouse0_buy').id,
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'partner_id': self.fuzzy_drink.seller_ids[1].partner_id.id,  # pricelist with uom "Pack of 6"
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'supplier_id': self.fuzzy_drink.seller_ids[1].id,  # pricelist with uom "Pack of 6"
=======
            'supplier_id': price_list_pack_of_6.id,  # pricelist with uom "Pack of 6"
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
        })
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        po = self._get_purchase_order_from_replenishment(replenish_wizard)

||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        replenish_wizard.launch_replenishment()
        po = self.env['purchase.order'].search([
            ('partner_id', '=', self.fuzzy_drink.seller_ids[1].partner_id.id)
        ], order='id DESC', limit=1)
=======
        replenish_wizard.launch_replenishment()
        po = self.env['purchase.order'].search([
            ('partner_id', '=', self.vendor.id)
        ], order='id DESC', limit=1)
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
        self.assertEqual(po.order_line.product_qty, 10, 'Generated PO line must respect the requested quantity from the wizard')
        self.assertEqual(po.order_line.uom_id, replenish_wizard.uom_id, 'Generated PO line must respect the requested UOM from the wizard')
        self.assertEqual(po.order_line.price_unit, 1, 'Generated PO line must respect the supplier price of UoM "Unit"')
        po.button_cancel()

        replenish_wizard = self.env['product.replenish'].create({
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'product_id': self.fuzzy_drink.id,
            'product_tmpl_id': self.fuzzy_drink.product_tmpl_id.id,
            'uom_id': self.uom_unit.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'product_id': self.fuzzy_drink.id,
            'product_tmpl_id': self.fuzzy_drink.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
=======
            'product_id': self.product.id,
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'product_uom_id': self.uom.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
            'quantity': 15,
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'warehouse_id': self.warehouse_1.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'warehouse_id': self.wh.id,
=======
            'warehouse_id': self.warehouse.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
            'route_id': self.env.ref('purchase_stock.route_warehouse0_buy').id,
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'partner_id': self.fuzzy_drink.seller_ids[1].partner_id.id,  # pricelist with uom "Pack of 6"
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'supplier_id': self.fuzzy_drink.seller_ids[1].id,  # pricelist with uom "Pack of 6"
=======
            'supplier_id': price_list_pack_of_6.id,  # pricelist with uom "Pack of 6"
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
        })
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        po = self._get_purchase_order_from_replenishment(replenish_wizard)

||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        replenish_wizard.launch_replenishment()
        po = self.env['purchase.order'].search([
            ('partner_id', '=', self.fuzzy_drink.seller_ids[1].partner_id.id)
        ], order='id DESC', limit=1)
=======
        replenish_wizard.launch_replenishment()
        po = self.env['purchase.order'].search([
            ('partner_id', '=', self.vendor.id)
        ], order='id DESC', limit=1)
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
        self.assertEqual(po.order_line.product_qty, 15, 'Generated PO line must respect the requested quantity from the wizard')
        self.assertEqual(po.order_line.uom_id, replenish_wizard.uom_id, 'Generated PO line must respect the requested UOM from the wizard')
        self.assertEqual(po.order_line.price_unit, 1, 'Generated PO line must respect the supplier price of UoM "Unit"')
        po.button_cancel()

        replenish_wizard = self.env['product.replenish'].create({
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'product_id': self.fuzzy_drink.id,
            'product_tmpl_id': self.fuzzy_drink.product_tmpl_id.id,
            'uom_id': self.uom_pack_6.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'product_id': self.fuzzy_drink.id,
            'product_tmpl_id': self.fuzzy_drink.product_tmpl_id.id,
            'product_uom_id': self.uom_pack_6.id,
=======
            'product_id': self.product.id,
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'product_uom_id': self.uom_pack_of_6.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
            'quantity': 1,
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'warehouse_id': self.warehouse_1.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'warehouse_id': self.wh.id,
=======
            'warehouse_id': self.warehouse.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
            'route_id': self.env.ref('purchase_stock.route_warehouse0_buy').id,
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'partner_id': self.fuzzy_drink.seller_ids[1].partner_id.id,  # pricelist with uom "Pack of 6"
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'supplier_id': self.fuzzy_drink.seller_ids[1].id,  # pricelist with uom "Pack of 6"
=======
            'supplier_id': price_list_pack_of_6.id,  # pricelist with uom "Pack of 6"
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
        })
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        po = self._get_purchase_order_from_replenishment(replenish_wizard)

||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        replenish_wizard.launch_replenishment()
        po = self.env['purchase.order'].search([
            ('partner_id', '=', self.fuzzy_drink.seller_ids[1].partner_id.id)
        ], order='id DESC', limit=1)
=======
        replenish_wizard.launch_replenishment()
        po = self.env['purchase.order'].search([
            ('partner_id', '=', self.vendor.id)
        ], order='id DESC', limit=1)
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
        self.assertEqual(po.order_line.product_qty, 1, 'Generated PO line must respect the requested quantity from the wizard')
        self.assertEqual(po.order_line.uom_id, replenish_wizard.uom_id, 'Generated PO line must respect the requested UOM from the wizard')
        self.assertEqual(po.order_line.price_unit, 6, 'Generated PO line must respect the supplier price of UoM "Unit" because the quantity doesn\'t match the "Pack of 6" pricelist')
        po.button_cancel()

        replenish_wizard = self.env['product.replenish'].create({
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'product_id': self.fuzzy_drink.id,
            'product_tmpl_id': self.fuzzy_drink.product_tmpl_id.id,
            'uom_id': self.uom_pack_6.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'product_id': self.fuzzy_drink.id,
            'product_tmpl_id': self.fuzzy_drink.product_tmpl_id.id,
            'product_uom_id': self.uom_pack_6.id,
=======
            'product_id': self.product.id,
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'product_uom_id': self.uom_pack_of_6.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
            'quantity': 2,
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'warehouse_id': self.warehouse_1.id,
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'warehouse_id': self.wh.id,
=======
            'warehouse_id': self.warehouse.id,
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
            'route_id': self.env.ref('purchase_stock.route_warehouse0_buy').id,
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
            'partner_id': self.fuzzy_drink.seller_ids[0].partner_id.id,  # pricelist with uom "Unit"
||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
            'supplier_id': self.fuzzy_drink.seller_ids[0].id,  # pricelist with uom "Unit"
=======
            'supplier_id': price_list_uom.id,  # pricelist with uom "Unit"
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
        })
<<<<<<< d98aff1232df958b925f71190b12fd23f7245c63
        po = self._get_purchase_order_from_replenishment(replenish_wizard)

||||||| c2f2e0f2009e6db56c8c21c0e6faf01667b0e109
        replenish_wizard.launch_replenishment()
        po = self.env['purchase.order'].search([
            ('partner_id', '=', self.fuzzy_drink.seller_ids[0].partner_id.id)
        ], order='id DESC', limit=1)
=======
        replenish_wizard.launch_replenishment()
        po = self.env['purchase.order'].search([
            ('partner_id', '=', self.vendor.id)
        ], order='id DESC', limit=1)
>>>>>>> 4a1a218c76e1c1d984006b2cf59d4be474c15aa4
        self.assertEqual(po.order_line.product_qty, 2, 'Generated PO line must respect the requested quantity from the wizard')
        self.assertEqual(po.order_line.uom_id, replenish_wizard.uom_id, 'Generated PO line must respect the requested UOM from the wizard')
        self.assertEqual(po.order_line.price_unit, 5, 'Generated PO line must respect the supplier price of UoM "Pack of 6" because the quantity matches the "Pack of 6" pricelist')
        po.button_cancel()

    def test_buy_replenish_supplier_not_on_pricelist(self):
        """ Replenish from a partner that is not in the product's seller_ids. """
        # Create a product with no pricelist
        product_to_buy = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'route_ids': [Command.link(self.route_buy.id)],
        })

        # Replenishing with partner not on pricelist
        replenish_wizard = self.env['product.replenish'].create({
            'product_id': product_to_buy.id,
            'product_tmpl_id': product_to_buy.product_tmpl_id.id,
            'uom_id': self.uom_unit.id,
            'route_id': self.route_buy.id,
            'partner_id': self.vendor1.id,
            'quantity': 1,
        })
        po_1 = self._get_purchase_order_from_replenishment(replenish_wizard)

        self.assertEqual(po_1.partner_id, self.vendor1)
        self.assertEqual(po_1.order_line.price_unit, 0.0)
        self.assertEqual(po_1.currency_id, self.env.company.currency_id)

        self.env['product.supplierinfo'].create([{
            'partner_id': self.vendor2.id,
            'product_id': product_to_buy.id,
            'price': 140.0,
        }])
        # Test replenishing again with same params (now checking the new pricelist is not taken)
        po = self._get_purchase_order_from_replenishment(replenish_wizard)

        self.assertEqual(po.partner_id, self.vendor1)
        self.assertEqual(po.order_line.price_unit, 0.0)  # Should not take price from pricelist
        self.assertEqual(po.currency_id, self.env.company.currency_id)
        self.assertEqual(po.id, po_1.id)  # Should not create a new PO
        self.assertEqual(po.order_line.product_qty, 2.0)  # Should add to previous PO

        # Test replenishing from partner on pricelist
        replenish_wizard.partner_id = self.vendor2.id
        po = self._get_purchase_order_from_replenishment(replenish_wizard)

        self.assertEqual(po.partner_id, self.vendor2)  # Should take pricelist
        self.assertEqual(po.order_line.price_unit, 140.0)

    def test_buy_replenish_name_search(self):
        """ On replenishement with buy route, suppliers should display supplier first and then contacts"""

        name_search = (
            self.env['res.partner']
            .with_context(highlight_supplier=1, product_id=self.product1.id)
            .name_search('', limit=10)
        )
        self.assertEqual(name_search[0][0], self.vendor.id, "Vendors not listed first with highlight_supplier flag")

        # Edge case of vendors starting with eg. Z are still displayed at top even not part of limit
        name_search = (
            self.env['res.partner']
            .with_context(highlight_supplier=1, product_id=self.product1.id)
            .name_search('', limit=2)  # Simulate a lot of contacts with limit 2
        )
        self.assertEqual(name_search[0][0], self.vendor.id, "Vendors beyond results within limit not listed first")

        name_search = self.env['res.partner'].name_search('', limit=10)  # without the flag default behaviour
        self.assertNotEqual(name_search[0][0], self.vendor.id, "Vendors listed first without highlight_supplier in ctx")

    def test_buy_replenish_defaults(self):
        """ The partner and scheduled date fields of the replenish wizard
            with the BUY route should select to the best pricelist for parameters
            UOM and quantity on open form and on_change 'route_id' & 'quantity' """

        product = self.env['product.product'].create({
            'name': "Furniture Service",
            'is_storable': True,
            'route_ids': [Command.link(self.route_buy.id)],
        })
        self.env['product.supplierinfo'].create([{
            'partner_id': self.vendor1.id,
            'product_id': product.id,
            'price': 140.0,
            'delay': 10,
        }, {
            'partner_id': self.vendor1.id,
            'product_id': product.id,
            'price': 100.0,
            'min_qty': 10,
            'delay': 12,
        }, {
            'partner_id': self.vendor2.id,
            'product_id': product.id,
            'price': 50.0,
            'min_qty': 100,
        }])

        with freeze_time("2023-01-01"):
            f = Form(self.env['product.replenish'].with_context(default_product_id=product.id))
            f.quantity = 1
            f.route_id = self.route_buy
            replenish_wizard = f.save()

            self.assertEqual(replenish_wizard.partner_id, self.vendor1)
            self.assertEqual(replenish_wizard.date_planned.day, 11)

            # Changing quantity should trigger recompute of best pricelist without changing the selected partner
            f.quantity = 120
            self.assertEqual(f.date_planned.day, 13)
            self.assertEqual(f.partner_id, self.vendor1)  # Should not take vendor2 even if pricelist is better for UX reason: would be weird if someone selects vendor1 and then changing quantities overrides his choice

            # But if partner is empty route change should select best pricelist for any partner
            f.partner_id = self.env['res.partner']
            f.route_id = self.route_buy  # Changing the route will trigger onchange
            self.assertEqual(f.partner_id, self.vendor2)
