# -*- coding: utf-8 -*-

from openerp.addons.stock.tests.common import TestStockCommon
from openerp.tools import mute_logger, float_round


class TestResupply(TestStockCommon):
    def setUp(self):
        super(TestResupply, self).setUp()
        self.Warehouse = self.env['stock.warehouse']
        # create 2 WH, BIG and SMALL
        # SMALL resupplies from BIG
        self.bigwh = self.Warehouse.create({'name': 'BIG', 'code': 'B'})
        self.smallwh = self.Warehouse.create({'name': 'SMALL', 'code': 'S',
                                              'default_resupply_wh_id': self.bigwh.id,
                                              'resupply_wh_ids': [(6, 0, [self.bigwh.id])],
                                              })
        # minimum stock rule for Product A on SMALL
        Orderpoint = self.env['stock.warehouse.orderpoint']
        Orderpoint.create({'warehouse_id': self.smallwh.id,
                           'location_id': self.smallwh.lot_stock_id.id,
                           'product_id': self.productA.id,
                           'product_min_qty': 100,
                           'product_max_qty': 200,
                           'product_uom': self.uom_unit.id,
                           })
        # create some stock on BIG
        Wiz = self.env['stock.change.product.qty']
        wiz = Wiz.create({'product_id': self.productA.id,
                          'new_quantity': 1000,
                          'location_id':  self.bigwh.lot_stock_id.id,
                          })
        wiz.change_product_qty()

    def test_resupply_from_wh(self):
        sched = self.env['procurement.order']
        sched.run_scheduler()
        # we generated 2 procurements for product A: one on small wh and the
        # other one on the transit location
        procs = sched.search([('product_id', '=', self.productA.id)])
        self.assertEqual(len(procs), 2)
        proc1 = sched.search([('product_id', '=', self.productA.id),
                              ('warehouse_id', '=', self.smallwh.id)])
        self.assertEqual(proc1.state, 'running')
        proc2 = sched.search([('product_id', '=', self.productA.id),
                              ('warehouse_id', '=', self.bigwh.id)])
        self.assertEqual(proc2.location_id.usage, 'transit')
        self.assertNotEqual(proc2.state, 'exception')
        proc2.run()
        self.assertEqual(proc2.state, 'running')
        self.assertTrue(proc2.rule_id)
