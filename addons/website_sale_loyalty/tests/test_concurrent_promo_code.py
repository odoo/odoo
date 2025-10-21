import threading
import time
from concurrent.futures import ThreadPoolExecutor
from psycopg2 import OperationalError

from odoo import SUPERUSER_ID, api, registry
from odoo.tests import tagged
from odoo.tests.common import BaseCase, get_db_name
from odoo.tools import mute_logger


@tagged('-standard', '-at_install', 'post_install', 'database_breaking')
class TestConcurrencyPromoCode(BaseCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.registry = registry(get_db_name())

        with cls.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})

            cls.promo_code = "AZERTY123456"
            cls.promo_code_program = env['loyalty.program'].create({
                'name': 'FREE FOR ONE',
                'program_type': 'promo_code',
                'limit_usage': True,
                'max_usage': 1,
                'rule_ids': [(0, 0, {
                    'minimum_qty': 0,
                    'code': cls.promo_code,
                })],
                'reward_ids': [(0, 0, {
                    'reward_type': 'discount',
                    'discount_mode': 'percent',
                    'discount_applicability': 'order',
                    'discount': 100.0,
                })]
            })

            cls.partner_1 = env['res.partner'].create([{
                'name': 'Mitchel Notadmin',
                'email': 'mitch.el@example.com',
            }])
            cls.partner_2 = env['res.partner'].create({
                'name': 'John Smith',
                'email': 'john.smith@example.com',
            })

            cls.product = env['product.product'].create({
                'name': "TEST PRODUCT",
                'standard_price': 100,
            })

            cls.order_partner_1 = env['sale.order'].create({'partner_id': cls.partner_1.id})
            cls.order_partner_2 = env['sale.order'].create({'partner_id': cls.partner_2.id})

            cls.order_lines = env['sale.order.line'].create([{
                    'order_id': cls.order_partner_1.id,
                    'product_id': cls.product.id,
                    'product_uom_qty': 1,
                }, {
                    'order_id': cls.order_partner_2.id,
                    'product_id': cls.product.id,
                    'product_uom_qty': 3,
                },
            ])

    def setUp(self):
        super().setUp()

        def reset():
            with self.registry.cursor() as cr:
                cr.execute("""
                    DELETE FROM loyalty_card WHERE program_id = %(program_id)s;
                    DELETE FROM loyalty_rule WHERE program_id = %(program_id)s;
                    DELETE FROM loyalty_reward WHERE program_id = %(program_id)s;
                    DELETE FROM loyalty_program WHERE id = %(program_id)s;
                    DELETE FROM sale_order_line WHERE id IN %(sol_ids)s;
                    DELETE FROM sale_order WHERE id IN %(so_ids)s;
                    DELETE FROM res_partner WHERE id IN %(partner_ids)s;
                    DELETE FROM product_product WHERE id = %(product_id)s;
                """, {
                    'program_id': self.promo_code_program.id,
                    'sol_ids': tuple(self.order_lines.ids),
                    'so_ids': (self.order_partner_1.id, self.order_partner_2.id),
                    'partner_ids': (self.partner_1.id, self.partner_2.id),
                    'product_id': self.product.id,
                })
        self.addCleanup(reset)

    @mute_logger('odoo.sql_db')
    def test_locked_update_promo_code(self):
        """ Test that two cursors cannot lock the same row simultaneously """

        # Commit the orders so that both cursors can read them
        with self.registry.cursor() as cr:
            cr.commit()

        # A simple barrier to make sure threads start roughly at the same time
        start_barrier = threading.Barrier(2)

        def run(order_id):
            with self.registry.cursor() as cr:
                cr.execute("SELECT id FROM loyalty_rule WHERE code = %s", (self.promo_code,))
                self.assertTrue(cr.fetchone())

                env = api.Environment(cr, SUPERUSER_ID, {})
                order = env['sale.order'].browse(order_id)

                # Wait for the other threads to be ready
                start_barrier.wait()

                try:
                    order._try_apply_code(self.promo_code)
                    time.sleep(2)  # Hold the lock for a moment to ensure overlap
                    return True

                except OperationalError:
                    # This catches the Postgres error when a row is locked
                    return False

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_1 = executor.submit(run, self.order_partner_1.id)
            future_2 = executor.submit(run, self.order_partner_2.id)

        # One should go through, the other should be locked (does not matter
        # which thread)
        res_1 = future_1.result(timeout=3)
        res_2 = future_2.result(timeout=3)
        self.assertNotEqual(res_1, res_2)
