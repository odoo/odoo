# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.stock.tests.test_packing import TestPackingCommon
from odoo.exceptions import UserError


class TestPacking(TestPackingCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPacking, cls).setUpClass()
        cls.uom_kg = cls.env.ref('uom.product_uom_kgm')
        cls.product_aw = cls.env['product.product'].create({
            'name': 'Product AW',
            'type': 'product',
            'weight': 2.4,
            'uom_id': cls.uom_kg.id,
            'uom_po_id': cls.uom_kg.id
        })
        cls.product_bw = cls.env['product.product'].create({
            'name': 'Product BW',
            'type': 'product',
            'weight': 0.3,
            'uom_id': cls.uom_kg.id,
            'uom_po_id': cls.uom_kg.id
        })
        test_carrier_product = cls.env['product.product'].create({
            'name': 'Test carrier product',
            'type': 'service',
        })
        cls.test_carrier = cls.env['delivery.carrier'].create({
            'name': 'Test carrier',
            'delivery_type': 'fixed',
            'product_id': test_carrier_product.id,
        })

    def test_put_in_pack_weight_wizard(self):
        """ Check that de default weight is correctly set by default when using the 'choose.delivery.package' wizard.
        This purpose of this wizard is
        """
        self.env['stock.quant']._update_available_quantity(self.product_aw, self.stock_location, 20.0)
        self.env['stock.quant']._update_available_quantity(self.product_bw, self.stock_location, 20.0)

        picking_ship = self.env['stock.picking'].create({
            'partner_id': self.env['res.partner'].create({'name': 'A partner'}).id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'carrier_id': self.test_carrier.id
        })
        move_line_paw = self.env['stock.move.line'].create({
            'product_id': self.product_aw.id,
            'product_uom_id': self.uom_kg.id,
            'picking_id': picking_ship.id,
            'qty_done': 5,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id
        })
        move_line_pbw = self.env['stock.move.line'].create({
            'product_id': self.product_bw.id,
            'product_uom_id': self.uom_kg.id,
            'picking_id': picking_ship.id,
            'qty_done': 5,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id
        })
        picking_ship.action_confirm()
        pack_action = picking_ship.action_put_in_pack()
        pack_action_ctx = pack_action['context']
        pack_action_model = pack_action['res_model']

        # We make sure the correct action was returned
        self.assertEqual(pack_action_model, 'choose.delivery.package')

        # We instanciate the wizard with the context of the action and check that the
        # default weight was set.
        pack_wiz = self.env['choose.delivery.package'].with_context(pack_action_ctx).create({})
        self.assertEqual(pack_wiz.shipping_weight, 13.5)

    def test_send_to_shipper_without_sale_order(self):
        """
            Check we can validate delivery with a delivery carrier set when it isn't linked to a sale order
        """
        self.env['stock.quant']._update_available_quantity(self.product_aw, self.stock_location, 20.0)

        picking_ship = self.env['stock.picking'].create({
            'partner_id': self.env['res.partner'].create({'name': 'A partner'}).id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'carrier_id': self.test_carrier.id
        })
        self.env['stock.move.line'].create({
            'product_id': self.product_aw.id,
            'product_uom_id': self.uom_kg.id,
            'picking_id': picking_ship.id,
            'qty_done': 5,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id
        })

        self.assertEqual(picking_ship.state, 'draft', 'Delivery state should be draft.')
        self.assertFalse(picking_ship.sale_id.id, 'Sale order shouldn\'t be set')
        picking_ship.action_confirm()
        picking_ship.button_validate()
        self.assertEqual(picking_ship.state, 'done')

    def test_batch_picking_delivery(self):
        """
            Check that when Put in Pack is called for batch pickings (i.e. faked with multi-record action
            calling to avoid extra batch+delivery module for just a test) then:
             - Same delivery carrier = works
             - Different delivery carriers = UserError
        """
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 4.0)
        another_test_carrier_product = self.env['product.product'].create({
            'name': 'Another test carrier product',
            'type': 'service',
        })
        test_carrier = self.env['delivery.carrier'].create({
            'name': 'Another Test carrier',
            'delivery_type': 'fixed',
            'product_id': another_test_carrier_product.id,
        })

        delivery_1 = self.env['stock.picking'].create({
            'partner_id': self.env['res.partner'].create({'name': 'A partner'}).id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'carrier_id': self.test_carrier.id
        })
        ml_1 = self.env['stock.move.line'].create({
            'product_id': self.productA.id,
            'product_uom_id': self.productA.uom_id.id,
            'picking_id': delivery_1.id,
            'qty_done': 1,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id
        })

        # Test that differing carrier + put in pack = UserError
        delivery_2 = delivery_1.copy({'carrier_id': test_carrier.id})
        ml_1.copy({'picking_id': delivery_2.id, 'qty_done': 1})
        # recreate the `action_put_in_pack`` steps so we don't have to add test to new module for batch pickings
        # to use batch version of method (which bypass the ensure_one() check in the stock_picking action)
        move_lines_to_pack = (delivery_1 | delivery_2)._package_move_lines()
        self.assertEqual(len(move_lines_to_pack), 2, 'There should be move lines that can be "put in pack"')
        with self.assertRaises(UserError):
            delivery_1._pre_put_in_pack_hook(move_lines_to_pack)

        # Test that same carrier + put in pack = OK!
        delivery_2.carrier_id = delivery_1.carrier_id
        move_lines_to_pack = (delivery_1 | delivery_2)._package_move_lines()
        self.assertEqual(len(move_lines_to_pack), 2, 'There should be move lines that can be "put in pack"')
        delivery_1._pre_put_in_pack_hook(move_lines_to_pack)
        package = delivery_1._put_in_pack(move_lines_to_pack)
        self.assertEqual(delivery_1.move_line_ids.result_package_id, package, 'Delivery 1 moves should have been put in package.')
        self.assertEqual(delivery_2.move_line_ids.result_package_id, package, 'Delivery 2 moves should have been put in package.')

    def test_picking_access_error_on_package(self):
        """
        In a multi-company environment, a reusable package which is used by 2+ companies can cause access errors
            on a company's picking history when it is in an in-use state (waiting to be unpacked)
        """
        company_a_user = self.env['res.users'].create({
            'name': 'test user company a',
            'login': 'test@testing.testing',
            'password': 'password',
            'groups_id': [Command.set([self.env.ref('stock.group_stock_user').id])],
        })
        wh_a = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        wh_a.delivery_steps = 'pick_pack_ship'
        company_b = self.env['res.company'].create({'name': 'Company B'})
        wh_b = self.env['stock.warehouse'].with_company(company_b).create({
            'name': 'Company B WH',
            'code': 'WH B',
            'delivery_steps': 'pick_pack_ship',
            'company_id': company_b.id,
        })

        reusable_box = self.env['stock.quant.package'].create({
            'name': 'Reusable Box',
            'package_use': 'reusable',
        })

        delivery_company_a = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'move_ids_without_package': [Command.create({
                'name': self.productA.name,
                'product_id': self.productA.id,
                'product_uom_qty': 5.0,
                'location_id': self.stock_location.id,
                'product_uom': self.productA.uom_id.id,
                'location_dest_id': self.customer_location.id,
            })],
            'move_line_ids': [Command.create({
                'location_id': self.stock_location.id,
                'result_package_id': reusable_box.id,
                'qty_done': 5.0,
                'product_id': self.productA.id,
                'location_dest_id': self.customer_location.id,
                'product_uom_id': self.productA.uom_id.id,
            })],
        })
        delivery_company_a.action_confirm()
        delivery_company_a.button_validate()
        reusable_box.unpack()

        other_picking_company_b = self.env['stock.picking'].with_company(company_b).create({
            'picking_type_id': wh_b.int_type_id.id,
            'location_id': wh_b.lot_stock_id.id,
            'location_dest_id': wh_b.lot_stock_id.id,
            'move_ids_without_package': [Command.create({
                'name': self.productA.name,
                'product_id': self.productA.id,
                'product_uom_qty': 3.0,
                'location_id': wh_b.lot_stock_id.id,
                'location_dest_id': wh_b.lot_stock_id.id,
                'product_uom': self.productA.uom_id.id,
            })],
            'move_line_ids': [Command.create({
                'location_id': wh_b.lot_stock_id.id,
                'location_dest_id': wh_b.lot_stock_id.id,
                'result_package_id': reusable_box.id,
                'qty_done': 3.0,
                'product_id': self.productA.id,
                'product_uom_id': self.productA.uom_id.id,
            })],
        })
        other_picking_company_b.action_confirm()
        other_picking_company_b.button_validate()

        company_a_user.groups_id = [Command.unlink(self.env.ref('stock.group_stock_multi_warehouses').id)]
        res = delivery_company_a.with_user(company_a_user).read()
        self.assertTrue(res)
