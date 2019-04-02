# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import concurrent
import logging, threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from contextlib import closing
from psycopg2.extensions import ISOLATION_LEVEL_READ_COMMITTED
import odoo
from odoo.exceptions import UserError
from odoo.tests.common import tagged, BaseCase, get_db_name
from odoo import api

_logger = logging.getLogger(__name__)


class CommitCase(BaseCase):
    """ TestCase in which all transactions are committed at the end
       this to allow running test functions with different cursors
       from multiple threads/processes
       CAUTION: test records cleanup must be handled by test class
    """

    @classmethod
    def setUpClass(cls):
        super(CommitCase, cls).setUpClass()
        cls.registry = odoo.registry(get_db_name())
        cls.cr = cls.registry.cursor()
        cls.env = api.Environment(cls.cr, odoo.SUPERUSER_ID, {})

    @classmethod
    def tearDownClass(cls):
        cls.cr.commit()
        cls.cr.close()
        super(CommitCase, cls).tearDownClass()

# number of test jobs to run by the 8 processes pool =>  duration of the  stress tests
NBO_TEST_JOBS = 64

@tagged('-standard','post_install') # only "on demand"  with --test-enable --test-tag 'stock_quant_fix'
class MTStockQuant(CommitCase):
    def setUp(self):
        super(MTStockQuant, self).setUp()

        stock_location = self.env.ref('stock.stock_location_stock')
        product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
        })
        self.id_product1 = product1.id
        self.id_stock_location = stock_location.id
        self.cr.commit()

    def tearDown(self):
        product1 = self.env['product.product'].browse(self.id_product1)
        stock_location = self.env['stock.location'].browse(self.id_stock_location)

        self.env['stock.quant']._gather(product1, stock_location).unlink()
        product1.unlink()

        super(MTStockQuant, self).tearDown()

    def gather_relevant(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        quants = self.env['stock.quant']._gather(product_id, location_id, lot_id=lot_id, package_id=package_id,
                                                 owner_id=owner_id, strict=strict)
        return quants.filtered(lambda q: not (q.quantity == 0 and q.reserved_quantity == 0))

    @classmethod
    def thread_env_wrapper(cls, fn_or_list, *args, **kwargs):
        if callable(fn_or_list):
            fn_list = [fn_or_list]
        else:
            fn_list = fn_or_list
        db_name = get_db_name()
        registry = odoo.registry(db_name)
        threading.current_thread().dbname = db_name
        user_error_count = 0
        with closing(registry.cursor()) as thread_cr:
            thread_cr._cnx.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
            with api.Environment.manage():
                env = api.Environment(thread_cr, odoo.SUPERUSER_ID, {})

                stock_location = env['stock.location'].browse(args[0])
                product1 = env['product.product'].browse(args[1])

                for func in fn_list:
                    try:
                        func(env, stock_location, product1, **kwargs)
                    except UserError as e:
                        user_error_count+=1
                        _logger.error(
                            '%s encountered an Exception: %s', func.__name__, e,
                            exc_info=True)
                    except Exception as e:
                        _logger.error(
                            '%s encountered an Exception: %s rolling back', func.__name__, e,
                            exc_info=True)
                        thread_cr.rollback()
                    else:
                        thread_cr.commit()
                thread_cr.commit()
                return user_error_count

    @classmethod
    def set_initial_stock(cls, env, stock_location, product1):
        env['stock.quant']._update_available_quantity(product1, stock_location, NBO_TEST_JOBS*10*64)

    @classmethod
    def increase_quant(cls, env, stock_location, product1):
        env['stock.quant']._update_available_quantity(product1, stock_location, 10)

    @classmethod
    def decrease_quant(cls, env, stock_location, product1):
        env['stock.quant']._update_available_quantity(product1, stock_location, -5)

    @classmethod
    def merge_quants(cls, env, *args):
        # Merge duplicated quants
        env['stock.quant']._merge_quants()
        env['stock.quant']._unlink_zero_quants()

    def run_mp_test_jobs(self, jobs):
        # close current cursor
        self.tearDownClass()
        # then empty the odoo cursor pool before starting multiprocessing,
        # as cursors can't be shared among forked processes.
        odoo.sql_db.close_all()
        user_error_count = 0
        with ProcessPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(self.thread_env_wrapper, stress_function_list, self.id_stock_location,
                                       self.id_product1) for stress_function_list in jobs]
            # wait for all jobs submitted the worker processes to terminate
            concurrent.futures.wait(futures)
            for future in concurrent.futures.as_completed(futures):
                user_error_count += future.result()
        # reinit class registries after end of children test processes
        self.setUpClass()

        return user_error_count


    def test_available_quantity(self):


        self.set_initial_stock(self.env,
                               self.env['stock.location'].browse(self.id_stock_location),
                               self.env['product.product'].browse(self.id_product1))

        user_error_count = self.run_mp_test_jobs(NBO_TEST_JOBS * [128 * [self.decrease_quant]])

        stock_location = self.env['stock.location'].browse(self.id_stock_location)
        product1 = self.env['product.product'].browse(self.id_product1)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 0)
        self.assertEqual(user_error_count, 0)

    @classmethod
    def reserve_quant(cls, env, stock_location, product1):
        env['stock.quant']._update_reserved_quantity(product1, stock_location, 10)

    @classmethod
    def consume_quant(cls, env, stock_location, product1):
        env['stock.quant']._update_reserved_quantity(product1, stock_location, -10)
        env['stock.quant']._update_available_quantity(product1, stock_location, -10)


    def test_reserved_quantity(self):
        self.set_initial_stock(self.env,
                               self.env['stock.location'].browse(self.id_stock_location),
                               self.env['product.product'].browse(self.id_product1))

        user_error_count = self.run_mp_test_jobs(NBO_TEST_JOBS * [64 * [self.reserve_quant, self.consume_quant]])

        stock_location = self.env['stock.location'].browse(self.id_stock_location)
        product1 = self.env['product.product'].browse(self.id_product1)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, stock_location), 0)

        # we must not get any UserError
        # "It is not possible to reserve more products of Product A than you have in stock"
        # or
        # "It is not possible to unreserve more products of Product A than you have in stock"
        self.assertEqual(user_error_count, 0)

