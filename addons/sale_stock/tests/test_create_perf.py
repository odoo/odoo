# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import random
import time

from decorator import decorator

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import users, warmup

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo

_logger = logging.getLogger(__name__)

@decorator
def prepare(func, self):
    """Prepare data to remove common querries from the count.

    Must be run after `warmup` because of the invalidations"""
    # prefetch the data linked to the company and its country code to avoid changing
    # the query count during l10n tests
    self.env.company.country_id.code
    func(self)


@tagged('so_batch_perf')
class TestPERF(TransactionCaseWithUserDemo):

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

        cls.salesmans = cls.env.ref('base.user_admin') | cls.user_demo

        cls.env.flush_all()

    @users('admin')
    @warmup
    @prepare
    def test_empty_sale_order_creation_perf(self):
        with self.assertQueryCount(admin=33):
            self.env['sale.order'].create({
                'partner_id': self.partners[0].id,
                'user_id': self.salesmans[0].id,
            })

    @users('admin')
    @warmup
    @prepare
    def test_empty_sales_orders_batch_creation_perf(self):
        # + 1 SO insert
        # + 1 SO sequence fetch
        # + 1 warehouse fetch
        # + 1 query to get analytic default account
        # + 1 followers queries ?
        with self.assertQueryCount(admin=37):
            self.env['sale.order'].create([{
                'partner_id': self.partners[0].id,
                'user_id': self.salesmans[0].id,
            } for i in range(2)])

    @users('admin')
    @warmup
    @prepare
    def test_dummy_sales_orders_batch_creation_perf(self):
        """ Dummy SOlines (notes/sections) should not add any custom queries other than their insert"""
        # + 2 SOL (batched) insert
        with self.assertQueryCount(admin=40):
            self.env['sale.order'].create([{
                'partner_id': self.partners[0].id,
                'user_id': self.salesmans[0].id,
                "order_line": [
                    (0, 0, {"display_type": "line_note", "name": "NOTE"}),
                    (0, 0, {"display_type": "line_section", "name": "SECTION"})
                ]
            } for i in range(2)])

    @users('admin')
    @warmup
    @prepare
    def test_light_sales_orders_batch_creation_perf_without_taxes(self):
        self.env['res.country'].search([]).mapped('code')
        self.products[0].taxes_id = [Command.set([])]
        # + 2 SQL insert
        # + 2 queries to get analytic default tags
        # + 9 follower queries ?
        with self.assertQueryCount(admin=50):  # com 46
            self.env['sale.order'].create([{
                'partner_id': self.partners[0].id,
                'user_id': self.salesmans[0].id,
                "order_line": [
                    (0, 0, {"display_type": "line_note", "name": "NOTE"}),
                    (0, 0, {"display_type": "line_section", "name": "SECTION"}),
                    (0, 0, {'product_id': self.products[0].id})
                ]
            } for i in range(2)])

    # Following tests are not deterministic
    # And are privatized on purpose
    # until the problem is found

    @users('admin')
    @warmup
    def __test_light_sales_orders_batch_creation_perf(self):
        with self.assertQueryCount(admin=70):  # 69 locally, 70 in nightly runbot
            self.env['sale.order'].create([{
                'partner_id': self.partners[0].id,
                'user_id': self.salesmans[0].id,
                "order_line": [
                    (0, 0, {"display_type": "line_note", "name": "NOTE"}),
                    (0, 0, {"display_type": "line_section", "name": "SECTION"}),
                    (0, 0, {'product_id': self.products[0].id})
                ]
            } for i in range(2)])

    @users('admin')
    @warmup
    def __test_complex_sales_orders_batch_creation_perf(self):
        # NOTE: sometimes more queries on runbot,
        # do not change without verifying in multi-builds
        # (Seems to be a time-based problem, everytime happening around 10PM)
        self._test_complex_sales_orders_batch_creation_perf(1504)

    def _test_complex_sales_orders_batch_creation_perf(self, query_count):
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

        with self.assertQueryCount(admin=query_count):
            t0 = time.time()
            self.env["sale.order"].create(vals_list)
            t1 = time.time()
            _logger.info(MSG, 'sale.order', self.ENTITIES, "BATCH", t1 - t0)
            self.env.cr.flush()
            _logger.info(MSG, 'sale.order', self.ENTITIES, "FLUSH", time.time() - t1)

    @users('admin')
    @warmup
    def __test_randomized_solines_qties(self):
        """Make sure the price and discounts computation are complexified
        and do not gain from any prefetch/batch gains during the price computation
        """

        vals_list = [{
            "partner_id": self.partners[i].id,
            "user_id": self.salesmans[i % 2].id,
            "order_line": [
                (0, 0, {"display_type": "line_note", "name": "NOTE"})
            ] + [
                (0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': random.random()
                }) for product in self.products
            ],
        } for i in range(self.ENTITIES)]

        # 1592 locally, 1593 in nightly runbot, 1954 sometimes
        with self.assertQueryCount(admin=1593):
            self.env["sale.order"].create(vals_list)
