# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import collections
import secrets
import textwrap
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import call, patch
from freezegun import freeze_time

import odoo
from odoo import api, fields
from odoo.tests.common import BaseCase, TransactionCase, RecordCapturer, get_db_name, tagged
from odoo.tools import mute_logger


class CronMixinCase:
    def capture_triggers(self, cron_id=None):
        """
        Get a context manager to get all cron triggers created during
        the context lifetime. While in the context, it exposes the
        triggers created so far from the beginning of the context. When
        the context exits, it doesn't capture new triggers anymore.

        The triggers are accessible on the `records` attribute of the
        returned object.

        :param cron_id: An optional cron record id (int) or xmlid (str)
                        to only capture triggers for that cron.
        """
        if isinstance(cron_id, str):  # xmlid case
            cron_id = self.env.ref(cron_id).id

        return RecordCapturer(
            model=self.env['ir.cron.trigger'].sudo(),
            domain=[('cron_id', '=', cron_id)] if cron_id else []
        )

    @classmethod
    def _get_cron_data(cls, env, priority=5):
        unique = secrets.token_urlsafe(8)
        return {
            'name': f'Dummy cron for TestIrCron {unique}',
            'state': 'code',
            'code': '',
            'model_id': env.ref('base.model_res_partner').id,
            'model_name': 'res.partner',
            'user_id': env.uid,
            'active': True,
            'interval_number': 1,
            'interval_type': 'days',
            'numbercall': -1,
            'doall': False,
            'nextcall': fields.Datetime.now() + timedelta(hours=1),
            'lastcall': False,
            'priority': priority,
        }

    @classmethod
    def _get_partner_data(cls, env):
        unique = secrets.token_urlsafe(8)
        return {'name': f'Dummy partner for TestIrCron {unique}'}


class TestIrCron(TransactionCase, CronMixinCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        freezer = freeze_time(cls.cr.now())
        cls.frozen_datetime = freezer.start()
        cls.addClassCleanup(freezer.stop)

        cls.cron = cls.env['ir.cron'].create(cls._get_cron_data(cls.env))
        cls.partner = cls.env['res.partner'].create(cls._get_partner_data(cls.env))

    def setUp(self):
        self.partner.write(self._get_partner_data(self.env))
        self.cron.write(self._get_cron_data(self.env))
        self.env['ir.cron.trigger'].search(
            [('cron_id', '=', self.cron.id)]
        ).unlink()

    def test_cron_direct_trigger(self):
        self.cron.code = textwrap.dedent(f"""\
            model.search(
                [("id", "=", {self.partner.id})]
            ).write(
                {{"name": "You have been CRONWNED"}}
            )
        """)

        self.cron.method_direct_trigger()

        self.assertEqual(self.cron.lastcall, fields.Datetime.now())
        self.assertEqual(self.partner.name, 'You have been CRONWNED')

    def test_cron_no_job_ready(self):
        self.cron.nextcall = fields.Datetime.now() + timedelta(days=1)
        self.cron.flush_recordset()

        ready_jobs = self.registry['ir.cron']._get_all_ready_jobs(self.cr)
        self.assertNotIn(self.cron.id, [job['id'] for job in ready_jobs])

    def test_cron_ready_by_nextcall(self):
        self.cron.nextcall = fields.Datetime.now()
        self.cron.flush_recordset()

        ready_jobs = self.registry['ir.cron']._get_all_ready_jobs(self.cr)
        self.assertIn(self.cron.id, [job['id'] for job in ready_jobs])

    def test_cron_ready_by_trigger(self):
        self.cron._trigger()
        self.env['ir.cron.trigger'].flush_model()

        ready_jobs = self.registry['ir.cron']._get_all_ready_jobs(self.cr)
        self.assertIn(self.cron.id, [job['id'] for job in ready_jobs])

    def test_cron_unactive_never_ready(self):
        self.cron.active = False
        self.cron.nextcall = fields.Datetime.now()
        self.cron._trigger()
        self.cron.flush_recordset()
        self.env['ir.cron.trigger'].flush_model()

        ready_jobs = self.registry['ir.cron']._get_all_ready_jobs(self.cr)
        self.assertNotIn(self.cron.id, [job['id'] for job in ready_jobs])

    def test_cron_numbercall0_never_ready(self):
        self.cron.numbercall = 0
        self.cron.nextcall = fields.Datetime.now()
        self.cron._trigger()
        self.cron.flush_recordset()
        self.env['ir.cron.trigger'].flush_model()

        ready_jobs = self.registry['ir.cron']._get_all_ready_jobs(self.cr)
        self.assertNotIn(self.cron.id, [job['id'] for job in ready_jobs])

    def test_cron_ready_jobs_order(self):
        cron_avg = self.cron.copy()
        cron_avg.priority = 5  # average priority

        cron_high = self.cron.copy()
        cron_high.priority = 0  # highest priority

        cron_low = self.cron.copy()
        cron_low.priority = 10  # lowest priority

        crons = cron_high | cron_avg | cron_low  # order is important
        crons.write({'nextcall': fields.Datetime.now()})
        crons.flush_recordset()
        ready_jobs = self.registry['ir.cron']._get_all_ready_jobs(self.cr)

        self.assertEqual(
            [job['id'] for job in ready_jobs if job['id'] in crons._ids],
            list(crons._ids),
        )

    def test_cron_skip_unactive_triggers(self):
        # Situation: an admin disable the cron and another user triggers
        # the cron to be executed *now*, the cron shouldn't be ready and
        # the trigger should not be stored.

        self.cron.active = False
        self.cron.nextcall = fields.Datetime.now() + timedelta(days=2)
        self.cron.flush_recordset()
        with self.capture_triggers() as capture:
            self.cron._trigger()

        ready_jobs = self.registry['ir.cron']._get_all_ready_jobs(self.cr)
        self.assertNotIn(self.cron.id, [job['id'] for job in ready_jobs],
            "the cron shouldn't be ready")
        self.assertFalse(capture.records, "trigger should has been skipped")

    def test_cron_keep_future_triggers(self):
        # Situation: yesterday an admin disabled the cron, while the
        # cron was disabled, another user triggered it to run today.
        # In case the cron as been re-enabled before "today", it should
        # run.

        # go yesterday
        self.frozen_datetime.tick(delta=timedelta(days=-1))

        # admin disable the cron
        self.cron.active = False
        self.cron.nextcall = fields.Datetime.now() + timedelta(days=10)
        self.cron.flush_recordset()

        # user triggers the cron to run *tomorrow of yesterday (=today)
        with self.capture_triggers() as capture:
            self.cron._trigger(at=fields.Datetime.now() + timedelta(days=1))

        # admin re-enable the cron
        self.cron.active = True
        self.cron.flush_recordset()

        # go today, check the cron should run
        self.frozen_datetime.tick(delta=timedelta(days=1))
        ready_jobs = self.registry['ir.cron']._get_all_ready_jobs(self.cr)
        self.assertIn(self.cron.id, [job['id'] for job in ready_jobs],
            "cron should be ready")
        self.assertTrue(capture.records, "trigger should has been kept")

    def test_cron_process_job(self):

        Setup = collections.namedtuple('Setup', ['doall', 'numbercall', 'missedcall', 'trigger'])
        Expect = collections.namedtuple('Expect', ['call_count', 'call_left', 'active'])

        matrix = [
            (Setup(doall=False, numbercall=-1, missedcall=2, trigger=False),
             Expect(call_count=1, call_left=-1, active=True)),
            (Setup(doall=True, numbercall=-1, missedcall=2, trigger=False),
             Expect(call_count=2, call_left=-1, active=True)),
            (Setup(doall=False, numbercall=3, missedcall=2, trigger=False),
             Expect(call_count=1, call_left=2, active=True)),
            (Setup(doall=True, numbercall=3, missedcall=2, trigger=False),
             Expect(call_count=2, call_left=1, active=True)),
            (Setup(doall=True, numbercall=3, missedcall=4, trigger=False),
             Expect(call_count=3, call_left=0, active=False)),
            (Setup(doall=True, numbercall=3, missedcall=0, trigger=True),
             Expect(call_count=1, call_left=2, active=True)),
        ]

        for setup, expect in matrix:
            with self.subTest(setup=setup, expect=expect):
                self.cron.write({
                    'active': True,
                    'doall': setup.doall,
                    'numbercall': setup.numbercall,
                    'nextcall': fields.Datetime.now() - timedelta(days=setup.missedcall - 1),
                })
                with self.capture_triggers(self.cron.id) as capture:
                    if setup.trigger:
                        self.cron._trigger()

                self.cron.flush_recordset()
                capture.records.flush_recordset()
                self.registry.enter_test_mode(self.cr)
                try:
                    with patch.object(self.registry['ir.cron'], '_callback') as callback:
                        self.registry['ir.cron']._process_job(
                            self.registry.db_name,
                            self.registry.cursor(),
                            self.cron.read(load=None)[0]
                        )
                finally:
                    self.registry.leave_test_mode()
                self.cron.invalidate_recordset()
                capture.records.invalidate_recordset()

                self.assertEqual(callback.call_count, expect.call_count)
                self.assertEqual(self.cron.numbercall, expect.call_left)
                self.assertEqual(self.cron.active, expect.active)
                self.assertEqual(self.cron.lastcall, fields.Datetime.now())
                self.assertEqual(self.cron.nextcall, fields.Datetime.now() + timedelta(days=1))
                self.assertEqual(self.env['ir.cron.trigger'].search_count([
                    ('cron_id', '=', self.cron.id),
                    ('call_at', '<=', fields.Datetime.now())]
                ), 0)

    def test_cron_null_interval(self):
        self.cron.interval_number = 0
        self.cron.flush_recordset()
        with self.assertLogs('odoo.addons.base.models.ir_cron', 'ERROR'):
            self.cron._process_job(get_db_name(), self.env.cr, self.cron.read(load=False)[0])
        self.cron.invalidate_recordset(['active'])
        self.assertFalse(self.cron.active)


@tagged('-standard', '-at_install', 'post_install', 'database_breaking')
class TestIrCronConcurrent(BaseCase, CronMixinCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Keep a reference on the real cron methods, those without patch
        cls.registry = odoo.registry(get_db_name())
        cls.cron_process_job = cls.registry['ir.cron']._process_job
        cls.cron_process_jobs = cls.registry['ir.cron']._process_jobs
        cls.cron_get_all_ready_jobs = cls.registry['ir.cron']._get_all_ready_jobs
        cls.cron_acquire_one_job = cls.registry['ir.cron']._acquire_one_job
        cls.cron_callback = cls.registry['ir.cron']._callback

    def setUp(self):
        super().setUp()

        with self.registry.cursor() as cr:
            env = api.Environment(cr, odoo.SUPERUSER_ID, {})
            env['ir.cron'].search([]).unlink()
            env['ir.cron.trigger'].search([]).unlink()

            self.cron1_data = env['ir.cron'].create(self._get_cron_data(env, priority=1)).read(load=None)[0]
            self.cron2_data = env['ir.cron'].create(self._get_cron_data(env, priority=2)).read(load=None)[0]
            self.partner_data = env['res.partner'].create(self._get_partner_data(env)).read(load=None)[0]
            self.cron_ids = [self.cron1_data['id'], self.cron2_data['id']]

    def test_cron_concurrency_1(self):
        """
        Two cron threads "th1" and "th2" wake up at the same time and
        see two jobs "job1" and "job2" that are ready (setup).

        Th1 acquire job1, before it can process and release its job, th2
        acquire a job too (setup). Th2 shouldn't be able to acquire job1
        as another thread is processing it, it should skips job1 and
        should acquire job2 instead (test). Both thread then process
        their job, update its `nextcall` and release it (setup).

        All the threads update and release their job before any thread
        attempt to acquire another job. (setup)

        The two thread each attempt to acquire a new job (setup), they
        should both fail to acquire any as each job's nextcall is in the
        future* (test).

        *actually, in their own transaction, the other job's nextcall is
        still "in the past" but any attempt to use that information
        would result in a serialization error. This tests ensure that
        that serialization error is correctly handled and ignored.
        """
        lock = threading.Lock()
        barrier = threading.Barrier(2)

        ###
        # Setup
        ###

        # Watchdog, if a thread was waiting at the barrier when the
        # other exited, it receives a BrokenBarrierError and exits too.
        def process_jobs(*args, **kwargs):
            try:
                self.cron_process_jobs(*args, **kwargs)
            finally:
                barrier.reset()

        # The two threads get the same list of jobs
        def get_all_ready_jobs(*args, **kwargs):
            jobs = self.cron_get_all_ready_jobs(*args, **kwargs)
            barrier.wait()
            return jobs

        # When a thread acquire a job, it processes it till the end
        # before another thread can acquire one.
        def acquire_one_job(*args, **kwargs):
            lock.acquire(timeout=1)
            try:
                with mute_logger('odoo.sql_db'):
                    job = self.cron_acquire_one_job(*args, **kwargs)
            except Exception:
                lock.release()
                raise
            if not job:
                lock.release()
            return job

        # When a thread is done processing its job, it waits for the
        # other thread to catch up.
        def process_job(*args, **kwargs):
            try:
                return_value = self.cron_process_job(*args, **kwargs)
            finally:
                lock.release()
            barrier.wait(timeout=1)
            return return_value

        # Set 2 jobs ready, process them in 2 different threads.
        with self.registry.cursor() as cr:
            env = api.Environment(cr, odoo.SUPERUSER_ID, {})
            env['ir.cron'].browse(self.cron_ids).write({
                'nextcall': fields.Datetime.now() - timedelta(hours=1)
            })

        ###
        # Run
        ###
        with patch.object(self.registry['ir.cron'], '_process_jobs', process_jobs), \
             patch.object(self.registry['ir.cron'], '_get_all_ready_jobs', get_all_ready_jobs), \
             patch.object(self.registry['ir.cron'], '_acquire_one_job', acquire_one_job), \
             patch.object(self.registry['ir.cron'], '_process_job', process_job), \
             patch.object(self.registry['ir.cron'], '_callback') as callback, \
             ThreadPoolExecutor(max_workers=2) as executor:
            fut1 = executor.submit(self.registry['ir.cron']._process_jobs, self.registry.db_name)
            fut2 = executor.submit(self.registry['ir.cron']._process_jobs, self.registry.db_name)
            fut1.result(timeout=2)
            fut2.result(timeout=2)

        ###
        # Validation
        ###

        self.assertEqual(len(callback.call_args_list), 2, 'Two jobs must have been processed.')
        self.assertEqual(callback.call_args_list, [
            call(
                self.cron1_data['name'],
                self.cron1_data['ir_actions_server_id'],
                self.cron1_data['id'],
            ),
            call(
                self.cron2_data['name'],
                self.cron2_data['ir_actions_server_id'],
                self.cron2_data['id'],
            ),
        ])
