# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import threading
from concurrent.futures import ThreadPoolExecutor

from psycopg2 import IntegrityError

import odoo
from odoo.tests.common import get_db_name, tagged, BaseCase
from odoo.tools import mute_logger


@tagged('-standard', '-at_install', 'post_install', 'database_breaking')
class TestOnboardingConcurrency(BaseCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.registry = odoo.registry(get_db_name())
        cls.addClassCleanup(cls.cleanUpClass)

        with cls.registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            cls.onboarding_id = env['onboarding.onboarding'].create([
                {
                    'name': 'Test Onboarding Concurrent',
                    'is_per_company': False,
                    'route_name': 'onboarding_concurrent'
                }
            ]).id

    @classmethod
    def cleanUpClass(cls):
        with cls.registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            env['onboarding.onboarding'].browse(cls.onboarding_id).unlink()
            env['onboarding.progress'].search([
                ('onboarding_id', '=', cls.onboarding_id)
            ]).unlink()

    @mute_logger('odoo.sql_db')
    def test_concurrent_create_progress(self):
        barrier = threading.Barrier(2)

        def run():
            raised_unique_violation = False

            with self.registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                onboarding = env['onboarding.onboarding'].search([
                    ('id', '=', self.onboarding_id)
                ])
                # There is no progress record
                self.assertFalse(env['onboarding.progress'].search([
                    ('onboarding_id', '=', self.onboarding_id)
                ]))
                barrier.wait(timeout=2)
                try:
                    onboarding._create_progress()
                except IntegrityError as e:
                    if e.pgcode == "23505":  # UniqueViolation
                        raised_unique_violation = True

            return raised_unique_violation

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_1 = executor.submit(run)
            future_2 = executor.submit(run)
            raised_1 = future_1.result(timeout=3)
            raised_2 = future_2.result(timeout=3)

        with self.registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            self.assertEqual(
                len(env['onboarding.progress'].search([('onboarding_id', '=', self.onboarding_id)])),
                1,
                "Exactly one thread should have been able to create a record."
            )

        self.assertEqual(
            raised_1 + raised_2,
            1,
            "Exactly one thread should have raised a UniqueViolation error even though "
            "there was no progress record at the start of its transaction."
        )
