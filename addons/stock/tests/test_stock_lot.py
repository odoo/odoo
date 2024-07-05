# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock.tests.common import TestStockCommon
from odoo.tests.common import Form
from odoo import Command

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
            'company_id': cls.env.company.id,
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
            'company_id': cls.env.company.id,
        })
        cls.StockQuantObj.create({
            'product_id': cls.productB.id,
            'location_id': cls.locationA.id,
            'quantity': 1.0,
            'lot_id': cls.lot_p_b.id
        })

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

    def test_bypass_reservation(self):
        """
        Check that the reservation of is bypassed when the stock move is added after the picking is done
        """
        customer = self.PartnerObj.create({'name': 'bob'})
        delivery_picking = self.env['stock.picking'].create({
            'partner_id': customer.id,
            'picking_type_id': self.picking_type_out,
            'move_ids': [Command.create({
                'name': self.productC.name,
                'product_id': self.productC.id,
                'product_uom_qty': 5,
                'quantity': 5,
                'location_id': self.stock_location,
                'location_dest_id': self.customer_location,
            })]
        })
        delivery_picking.button_validate()
        delivery_picking.is_locked = False
        self.env['stock.move.line'].create({
            'product_id': self.productA.id,
            'product_uom_id': self.productA.uom_id.id,
            'picking_id': delivery_picking.id,
            'quantity': 1,
            'lot_id': self.lot_p_a.id,
            'quant_id': self.lot_p_a.quant_ids.id
        })
        self.assertRecordValues(delivery_picking.move_ids, [{'state': 'done', 'quantity': 5.0, 'picked': True}, {'state': 'done', 'quantity': 1.0, 'picked': True}])
        quant = self.lot_p_a.quant_ids.filtered(lambda q: q.location_id == self.locationA)
        self.assertRecordValues(quant, [{'quantity': 9.0, 'reserved_quantity': 0.0}])
