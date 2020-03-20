# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import time

from odoo.tests import common, tagged
from odoo.tests.common import users, warmup

_logger = logging.getLogger(__name__)


@tagged('so_batch_perf')
class TestPERF(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ENTITIES = 50

        cls.products = cls.env['product.product'].create([{
            'name': 'Product %s' % i,
            'list_price': 1 + 10 * i,
            'type': 'service',
        } for i in range(10)])

        cls.partners = cls.env['res.partner'].create([{
            'name': 'Partner %s' % i,
        } for i in range(cls.ENTITIES)])

        cls.salesmans = cls.env.ref('base.user_admin') | cls.env.ref('base.user_demo')

        cls.env['base'].flush()

    @users('admin')
    @warmup
    def test_sales_orders_batch_creation_perf(self):
        MSG = "Model %s, %i records, %s, time %.2f"

        vals_list = [{
            "partner_id": self.partners[i].id,
            "user_id": self.salesmans[i % 2].id,
            "order_line": [
                (0, 0, {"display_type": "line_note", "name": "NOTE"})
            ] + [
                (0, 0, {'product_id': product.id}) for product in self.products
            ],
        } for i in range(self.ENTITIES)]

        with self.assertQueryCount(admin=2753):
            t0 = time.time()
            self.env["sale.order"].create(vals_list)
            t1 = time.time()
            _logger.info(MSG, 'sale.order', self.ENTITIES, "BATCH", t1 - t0)
            self.env.cr.flush()
            _logger.info(MSG, 'sale.order', self.ENTITIES, "FLUSH", time.time() - t1)
