# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from odoo.addons.stock.tests.common import TestStockCommon
from odoo.tests.common import Form
from odoo.exceptions import UserError


class TestStockLot(TestStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Creates a tracked product using expiration dates.
        cls.product_apple = cls.ProductObj.create({
            'name': 'Apple',
            'type': 'product',
            'tracking': 'lot',
            'use_expiration_date': True,
            'expiration_time': 10,
            'use_time': 5,
            'removal_time': 8,
            'alert_time': 4,
        })
        # Creates an apple lot.
        lot_form = Form(cls.LotObj)
        lot_form.name = 'good-apple-lot'
        lot_form.product_id = cls.product_apple
        lot_form.company_id = cls.env.company
        cls.lot_good_apple = lot_form.save()
        # Creates an expired apple lot.
        lot_form = Form(cls.LotObj)
        lot_form.name = 'expired-apple-lot-01'
        lot_form.product_id = cls.product_apple
        lot_form.company_id = cls.env.company
        cls.lot_expired_apple = lot_form.save()
        lot_form = Form(cls.lot_expired_apple)  # Edits the lot to make it expired.
        lot_form.expiration_date = datetime.today() - timedelta(days=10)
        cls.lot_expired_apple = lot_form.save()

        # Creates a producible product and its BOM.
        cls.product_apple_pie = cls.ProductObj.create({
            'name': 'Apple Pie',
            'type': 'product',
        })
        cls.bom_apple_pie = cls.env['mrp.bom'].create({
            'product_id': cls.product_apple_pie.id,
            'product_tmpl_id': cls.product_apple_pie.product_tmpl_id.id,
            'product_uom_id': cls.uom_unit.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.product_apple.id, 'product_qty': 3}),
            ]})

        cls.location_stock = cls.env['stock.location'].browse(cls.stock_location)

        # Creation of a routing
        cls.workcenter = cls.env['mrp.workcenter'].create({
            'name': 'Bakery',
            'default_capacity': 2,
            'time_start': 10,
            'time_stop': 5,
            'time_efficiency': 80,
        })

    def test_01_product_produce(self):
        """ Checks user doesn't get a confirmation wizard when they produces with
        no expired components. """
        # Creates a Manufacturing Order...
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_apple_pie
        mo_form.bom_id = self.bom_apple_pie
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        # ... and tries to product with a non-expired lot as component.
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        details_operation_form = Form(mo.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.quantity = 3
            ml.lot_id = self.lot_good_apple
        details_operation_form.save()
        res = mo.button_mark_done()
        # Producing must not return a wizard in this case.
        self.assertEqual(res, True)

    def test_02_product_produce_using_expired(self):
        """ Checks user gets a confirmation wizard when they produces with
        expired components. """
        # Creates a Manufacturing Order...
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_apple_pie
        mo_form.bom_id = self.bom_apple_pie
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        # ... and tries to product with an expired lot as component.
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        details_operation_form = Form(mo.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.quantity = 3
            ml.lot_id = self.lot_expired_apple
        details_operation_form.save()
        res = mo.button_mark_done()
        # Producing must return a confirmation wizard.
        self.assertNotEqual(res, None)
        self.assertEqual(res['res_model'], 'expiry.picking.confirmation')
