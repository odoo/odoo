# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.stock.tests.common import TestStockCommon
from odoo.tests import Form
from odoo.exceptions import ValidationError


class TestLotSerial(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.locationA = cls.env['stock.location'].create({
            'name': 'Location A',
            'usage': 'internal',
        })
        cls.locationB = cls.env['stock.location'].create({
            'name': 'Location B',
            'usage': 'internal',
        })
        cls.locationC = cls.env['stock.location'].create({
            'name': 'Location C',
            'usage': 'internal',
        })
        cls.productA.tracking = 'lot'
        cls.lot_p_a = cls.LotObj.create({
            'name': 'lot_product_a',
            'product_id': cls.productA.id,
        })
        cls.StockQuantObj.create({
            'product_id': cls.productA.id,
            'location_id': cls.locationA.id,
            'quantity': 10.0,
            'lot_id': cls.lot_p_a.id
        })

        cls.productB.tracking = 'serial'
        cls.lot_p_b = cls.LotObj.create({
            'name': 'lot_product_b',
            'product_id': cls.productB.id,
        })
        cls.env['stock.quant']._update_available_quantity(
            cls.productB,
            cls.locationA,
            1.0,
            lot_id=cls.lot_p_b,
        )

    def test_single_location(self):
        self.assertEqual(self.lot_p_a.location_id, self.locationA)
        self.assertEqual(self.lot_p_b.location_id, self.locationA)

        # testing changing the location from the lot form
        lot_b_form = Form(self.lot_p_b)
        lot_b_form.location_id = self.locationB
        lot_b_form.save()
        self.assertEqual(self.lot_p_b.quant_ids.filtered(lambda q: q.quantity > 0).location_id, self.locationB)

        # testing changing the location from the quant
        self.lot_p_b.quant_ids.move_quants(location_dest_id=self.locationC, message='test_quant_move')
        self.assertEqual(self.lot_p_b.location_id, self.locationC)

        # testing having the lot in multiple locations
        self.StockQuantObj.create({
            'product_id': self.productA.id,
            'location_id': self.locationC.id,
            'quantity': 10.0,
            'lot_id': self.lot_p_a.id
        })
        self.assertEqual(self.lot_p_a.location_id.id, False)

        # testing having the lot back in a single location
        self.lot_p_a.quant_ids.filtered(lambda q: q.location_id == self.locationA).move_quants(location_dest_id=self.locationC)
        self.StockQuantObj.invalidate_model()
        self.StockQuantObj._unlink_zero_quants()
        self.assertEqual(self.lot_p_a.location_id, self.locationC)

    def test_import_lots(self):
        vals = self.MoveObj.action_generate_lot_line_vals({
            'default_tracking': 'lot',
            'default_product_id': self.productA.id,
            'default_location_dest_id': self.locationC.id,
        }, "import", "", 0, "aze;2\nqsd;4\nwxc")

        self.assertEqual(len(vals), 3)
        self.assertEqual(vals[0]['lot_name'], 'aze')
        self.assertEqual(vals[0]['quantity'], 2)
        self.assertEqual(vals[1]['lot_name'], 'qsd')
        self.assertEqual(vals[1]['quantity'], 4)
        self.assertEqual(vals[2]['lot_name'], 'wxc')
        self.assertEqual(vals[2]['quantity'], 1, "default lot qty")

    def test_lot_no_company(self):
        """ check the lot created in a receipt should not have a company if the product is not
        linked to a company"""
        picking1 = self.env['stock.picking'].create({
            'name': 'Picking 1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
            'move_ids': [Command.create({
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_id': self.productB.id,
                'product_uom_qty': 1.0,
            })]
        })
        picking1.action_confirm()
        move = picking1.move_ids
        move.move_line_ids.lot_name = 'sn_test'
        move.picked = True
        picking1._action_done()
        self.assertEqual(move.state, 'done')
        # there is a lot but without a company
        self.assertTrue(move.move_line_ids.lot_id)
        self.assertFalse(move.move_line_ids.lot_id.company_id)

    def test_lot_uniqueness(self):
        """ Checks that the same lot name cannot be inserted twice for the same company or 'no-company'.
        """
        lot_1 = self.env['stock.lot'].create({
            'name': 'unique',
            'product_id': self.productB.id,
            'company_id': False,
        })
        self.assertTrue(lot_1)
        # Now try to insert the same one without company
        with self.assertRaises(ValidationError):
            self.env['stock.lot'].create({
                'name': 'unique',
                'product_id': self.productB.id,
                'company_id': False,
            })
        # Same thing should happen when creating it from a company now
        with self.assertRaises(ValidationError):
            self.env['stock.lot'].create({
                'name': 'unique',
                'product_id': self.productB.id,
                'company_id': self.env.company.id,
            })

        lot_2 = self.env['stock.lot'].create({
            'name': 'also_unique',
            'product_id': self.productB.id,
            'company_id': self.env.company.id,
        })
        self.assertTrue(lot_2)
        # Now try to insert the same one without company
        with self.assertRaises(ValidationError):
            self.env['stock.lot'].create({
                'name': 'also_unique',
                'product_id': self.productB.id,
                'company_id': False,
            })
        # Same thing should happen when creating it from a company now
        with self.assertRaises(ValidationError):
            self.env['stock.lot'].create({
                'name': 'also_unique',
                'product_id': self.productB.id,
                'company_id': self.env.company.id,
            })

    def test_bypass_reservation(self):
        """
        Check that the reservation of is bypassed when a stock move is added after the picking is done
        """
        customer = self.PartnerObj.create({'name': 'bob'})
        delivery_picking = self.env['stock.picking'].create({
            'partner_id': customer.id,
            'picking_type_id': self.picking_type_out.id,
            'move_ids': [Command.create({
                'product_id': self.productC.id,
                'product_uom_qty': 5,
                'quantity': 5,
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
            })]
        })
        additional_product = self.productA
        lot = self.lot_p_a
        lot.location_id = self.stock_location
        quant = additional_product.stock_quant_ids.filtered(lambda q: q.location_id == self.stock_location)
        self.assertRecordValues(quant, [{'quantity': 10.0, 'reserved_quantity': 0.0}])
        delivery_picking.button_validate()
        delivery_picking.is_locked = False
        self.env['stock.move.line'].create({
            'product_id': additional_product.id,
            'product_uom_id': additional_product.uom_id.id,
            'picking_id': delivery_picking.id,
            'quantity': 3,
            'lot_id': lot.id,
            'quant_id': quant.id
        })
        self.assertRecordValues(delivery_picking.move_ids, [{'state': 'done', 'quantity': 5.0, 'picked': True}, {'state': 'done', 'quantity': 3.0, 'picked': True}])
        self.assertRecordValues(quant, [{'quantity': 7.0, 'reserved_quantity': 0.0}])

    def test_location_lot_id_update_quant_qty(self):
        """
        Test that the location of a lot is updated when its linked quants change
        """
        # check that the serial number linked to productB is in location A
        self.assertEqual(self.lot_p_b.location_id, self.locationA)
        # Make a delivery move
        starting_quant = self.lot_p_b.quant_ids
        self.assertEqual(starting_quant.quantity, 1)
        move = self.env["stock.move"].create({
            'location_id': self.locationA.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.productB.id,
            'product_uom_qty': 1.0,
        })
        move._action_confirm()
        self.assertEqual(move.state, 'confirmed')
        move._action_assign()
        move.picked = True
        move._action_done()
        self.assertEqual(move.state, 'done')
        # check that the quantity of starting quant is moved to a new quant
        self.assertEqual(starting_quant.quantity, 0)
        # check that the sn is in customer location
        self.assertEqual(self.lot_p_b.location_id.id, self.customer_location.id)
        # create a return
        move = self.env['stock.move'].create({
            'location_id': self.customer_location.id,
            'location_dest_id': self.locationA.id,
            'product_id': self.productB.id,
            'lot_ids': self.lot_p_b,
            'product_uom_qty': 1.0,
        })
        move._action_confirm()
        move.picked = True
        move._action_done()
        self.assertEqual(move.state, 'done')
        self.assertEqual(starting_quant.quantity, 1)
        self.assertEqual(self.lot_p_b.location_id, self.locationA)

    def test_lot_id_with_branch_company(self):
        """Test that a lot can be created in branch company when
        the product is limited to the parent company"""
        branch_a = self.env['res.company'].create({
            'name': 'Branch X',
            'country_id': self.env.company.country_id.id,
            'parent_id': self.env.company.id,
        })
        self.assertEqual(self.productB.tracking, 'serial')
        self.productB.company_id = self.env.company
        branch_a_warehouse = self.env['stock.warehouse'].search([('company_id', '=', branch_a.id)])
        branch_receipt_type = self.env['stock.picking.type'].search([('company_id', '=', branch_a.id), ('code', '=', 'incoming')], limit=1)
        # create a receipt and confirm it
        picking1 = self.env['stock.picking'].create({
            'name': 'Picking 1',
            'location_id': self.supplier_location.id,
            'location_dest_id': branch_a_warehouse.lot_stock_id.id,
            'picking_type_id': branch_receipt_type.id,
        })
        move = self.env["stock.move"].with_company(branch_a).create({
            'location_id': self.supplier_location.id,
            'location_dest_id': branch_a_warehouse.lot_stock_id.id,
            'product_id': self.productB.id,
            'product_uom_qty': 1.0,
            'picking_id': picking1.id,
        })
        picking1.with_company(branch_a).action_confirm()
        move.move_line_ids.lot_name =  'sn_test'
        move.picked = True
        picking1.with_company(branch_a)._action_done()
        self.assertTrue(move.move_line_ids.lot_id)
        self.assertEqual(move.state, 'done')
        sn_form = Form(self.env['stock.lot'].with_company(branch_a))
        sn_form.name = 'sn_test_2'
        sn_form.product_id = self.productB
        sn = sn_form.save()
        self.assertEqual(sn.company_id, branch_a)

    def test_lot_search_partner_ids(self):
        """Test that the correct lots show when doing searches based on partner_ids"""
        customer = self.PartnerObj.create({'name': 'bob'})
        picking1 = self.env['stock.picking'].create({
            'name': 'Picking 1',
            'partner_id': customer.id,
            'location_id': self.locationA.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
            'move_ids': [Command.create({
                'location_id': self.locationA.id,
                'location_dest_id': self.customer_location.id,
                'product_id': self.productA.id,
                'product_uom_qty': 1.0,
                'quantity': 1.0,
            })]
        })
        picking1.move_ids.move_line_ids.lot_id = self.lot_p_a
        picking1.action_confirm()
        picking1.button_validate()
        lot_id = self.env['stock.lot'].search([('partner_ids', '!=', False)])
        self.assertEqual(len(lot_id), 1)
        self.assertEqual(lot_id, self.lot_p_a)
        lot_id = self.env['stock.lot'].search([('partner_ids', '=', False)])
        self.assertEqual(len(lot_id), 1)
        self.assertEqual(lot_id, self.lot_p_b)
        lot_id = self.env['stock.lot'].search([('partner_ids.name', 'ilike', 'bo')])
        self.assertEqual(len(lot_id), 1)
        self.assertEqual(lot_id, self.lot_p_a)

    def test_default_lot_sequence(self):
        """Test that the default lot sequence is used when the product is created with a null prefix"""
        product_a = self.env['product.product'].create({
            'name': 'Test Product A',
            'tracking': 'lot',
            'serial_prefix_format': False,
        })
        default_lot_sequence = self.env.ref('stock.sequence_production_lots')
        product_a.invalidate_recordset()
        self.assertEqual(product_a.lot_sequence_id, default_lot_sequence)
