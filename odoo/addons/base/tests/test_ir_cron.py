# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# ruff: noqa: E201, E272, E301, E306

import secrets
import textwrap
from contextlib import closing
from datetime import timedelta
from unittest.mock import patch
from freezegun import freeze_time

from odoo import fields
from odoo.tests.common import TransactionCase, RecordCapturer
from odoo.tools import mute_logger
from odoo.addons.base.models.ir_cron import MIN_FAILURE_COUNT_BEFORE_DEACTIVATION, MIN_DELTA_BEFORE_DEACTIVATION


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
        super().setUp()
        self.partner.write(self._get_partner_data(self.env))
        self.cron.write(self._get_cron_data(self.env))

        domain = [('cron_id', '=', self.cron.id)]
        self.env['ir.cron.trigger'].search(domain).unlink()
        self.env['ir.cron.progress'].search(domain).unlink()

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
        self.env.flush_all()

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
        Progress = self.env['ir.cron.progress']
        default_progress_values = {'done': 0, 'remaining': 0, 'timed_out_counter': 0}
        ten_days_ago = fields.Datetime.now() - MIN_DELTA_BEFORE_DEACTIVATION - timedelta(days=2)
        almost_failed = MIN_FAILURE_COUNT_BEFORE_DEACTIVATION - 1

        def nothing(cron):
            state = {'call_count': 0}
            def f(self):
                state['call_count'] += 1
            return f, state

        def eleven_success(cron):
            state = {'call_count': 0}
            CALL_TARGET = 11
            def f(self):
                state['call_count'] += 1
                self.env['ir.cron']._notify_progress(
                    done=1,
                    remaining=CALL_TARGET - state['call_count']
                )
            return f, state

        def five_success(cron):
            state = {'call_count': 0}
            CALL_TARGET = 5
            def f(self):
                state['call_count'] += 1
                self.env['ir.cron']._notify_progress(
                    done=1,
                    remaining=CALL_TARGET - state['call_count']
                )
            return f, state

        def failure(cron):
            state = {'call_count': 0}
            def f(self):
                state['call_count'] += 1
                raise ValueError
            return f, state

        def failure_partial(cron):
            state = {'call_count': 0}
            CALL_TARGET = 5
            def f(self):
                state['call_count'] += 1
                self.env['ir.cron']._notify_progress(
                    done=1,
                    remaining=CALL_TARGET - state['call_count']
                )
                self.env.cr.commit()
                raise ValueError
            return f, state

        def failure_fully(cron):
            state = {'call_count': 0}
            def f(self):
                state['call_count'] += 1
                self.env['ir.cron']._notify_progress(done=1, remaining=0)
                self.env.cr.commit()
                raise ValueError
            return f, state

        CASES = [
            #                 IN          |                 OUT
            #       callback, curr_failures, trigger, call_count, done_count, fail_count, active,
            (        nothing,             0,   False,          1,          0,          0,  True),
            (        nothing, almost_failed,   False,          1,          0,          0,  True),
            ( eleven_success,             0,    True,         10,         10,          0,  True),
            ( eleven_success, almost_failed,    True,         10,         10,          0,  True),
            (   five_success,             0,   False,          5,          5,          0,  True),
            (   five_success, almost_failed,   False,          5,          5,          0,  True),
            (        failure,             0,   False,          1,          0,          1,  True),
            (        failure, almost_failed,   False,          1,          0,          0, False),
            (failure_partial,             0,   False,          5,          5,          1,  True),
            (failure_partial, almost_failed,   False,          5,          5,          0, False),
            (  failure_fully,             0,   False,          1,          1,          1,  True),
            (  failure_fully, almost_failed,   False,          1,          1,          0, False),
        ]

        for cb, curr_failures, trigger, call_count, done_count, fail_count, active in CASES:
            with self.subTest(cb=cb, failure=curr_failures), closing(self.cr.savepoint()):
                self.cron.write({
                    'active': True,
                    'failure_count': curr_failures,
                    'first_failure_date': ten_days_ago if curr_failures else None
                })
                with self.capture_triggers(self.cron.id) as capture:
                    if trigger:
                        self.cron._trigger()

                self.env.flush_all()
                with self.enter_registry_test_mode():
                    cb, state = cb(self.cron)
                    with mute_logger('odoo.addons.base.models.ir_cron'),\
                            patch.object(self.registry['ir.actions.server'], 'run', cb):
                        self.registry['ir.cron']._process_job(
                            self.registry.db_name,
                            self.registry.cursor(),
                            {**self.cron.read(load=None)[0], **default_progress_values}
                        )
                self.cron.invalidate_recordset()
                capture.records.invalidate_recordset()

                self.assertEqual(self.cron.id in [job['id'] for job in self.cron._get_all_ready_jobs(self.env.cr)], trigger)
                self.assertEqual(state['call_count'], call_count)
                self.assertEqual(Progress.search_count([('cron_id', '=', self.cron.id), ('done', '=', 1)]), done_count)
                self.assertEqual(self.cron.failure_count, fail_count)
                self.assertEqual(self.cron.active, active)

    def test_cron_retrigger(self):
        Trigger = self.env['ir.cron.trigger']
        Progress = self.env['ir.cron.progress']
        default_progress_values = {'done': 0, 'remaining': 0, 'timed_out_counter': 0}

        def make_run(cron):
            state = {'call_count': 0}
            CALL_TARGET = 11

            def run(self):
                state['call_count'] += 1
                self.env['ir.cron']._notify_progress(done=1, remaining=CALL_TARGET - state['call_count'])
            return run, state

        self.cron._trigger()
        self.env.flush_all()
        with self.enter_registry_test_mode():
            mocked_run, mocked_run_state = make_run(self.cron)
            with patch.object(self.registry['ir.actions.server'], 'run', mocked_run):
                self.registry['ir.cron']._process_job(
                    self.registry.db_name,
                    self.registry.cursor(),
                    {**self.cron.read(load=None)[0], **default_progress_values}
                )

        self.assertEqual(
            mocked_run_state['call_count'], 10,
            '`run` should have been called ten times',
        )
        self.assertEqual(
            Progress.search_count([('done', '=', 1), ('cron_id', '=', self.cron.id)]), 10,
            'There should be 10 progress log for this cron',
        )
        self.assertEqual(
            Trigger.search_count([('cron_id', '=', self.cron.id)]), 1,
            "One trigger should have been kept",
        )

        self.env.flush_all()
        with (
            self.enter_registry_test_mode(),
            patch.object(self.registry['ir.actions.server'], 'run', mocked_run),
        ):
            self.registry['ir.cron']._process_job(
                self.registry.db_name,
                self.registry.cursor(),
                {**self.cron.read(load=None)[0], **default_progress_values}
            )

        ready_jobs = self.registry['ir.cron']._get_all_ready_jobs(self.cr)
        self.assertNotIn(
            self.cron.id, [job['id'] for job in ready_jobs],
            'The cron has finished executing'
        )
        self.assertEqual(
            mocked_run_state['call_count'], 10 + 1,
            '`run` should have been called one additional time',
        )
        self.assertEqual(
            Progress.search_count([('done', '=', 1), ('cron_id', '=', self.cron.id)]), 11,
            'There should be 11 progress log for this cron',
        )

    def test_cron_failed_increase(self):
        self.cron._trigger()
        self.env.flush_all()
        default_progress = {'done': 0, 'remaining': 0, 'timed_out_counter': 0}
        with self.enter_registry_test_mode():
            with (
                patch.object(self.registry['ir.cron'], '_callback', side_effect=Exception),
                patch.object(self.registry['ir.cron'], '_notify_admin') as notify,
            ):
                self.registry['ir.cron']._process_job(
                    self.registry.db_name,
                    self.registry.cursor(),
                    {**self.cron.read(load=None)[0], **default_progress}
                )

        self.env.invalidate_all()
        self.assertEqual(self.cron.failure_count, 1, 'The cron should have failed once')
        self.assertEqual(self.cron.active, True, 'The cron should still be active')
        self.assertFalse(notify.called)

        self.cron.failure_count = 4

        self.cron._trigger()
        self.env.flush_all()
        with (
            self.enter_registry_test_mode(),
            patch.object(self.registry['ir.cron'], '_callback', side_effect=Exception),
            patch.object(self.registry['ir.cron'], '_notify_admin') as notify,
        ):
            self.registry['ir.cron']._process_job(
                self.registry.db_name,
                self.registry.cursor(),
                {**self.cron.read(load=None)[0], **default_progress}
            )

        self.env.invalidate_all()
        self.assertEqual(self.cron.failure_count, 5, 'The cron should have failed one more time but not reset (due to time)')
        self.assertEqual(self.cron.active, True, 'The cron should not have been deactivated due to time constraint')
        self.assertFalse(notify.called)

        self.cron.failure_count = 4
        self.cron.first_failure_date = fields.Datetime.now() - timedelta(days=8)

        self.cron._trigger()
        self.env.flush_all()
        with (
            self.enter_registry_test_mode(),
            patch.object(self.registry['ir.cron'], '_callback', side_effect=Exception),
            patch.object(self.registry['ir.cron'], '_notify_admin') as notify,
        ):
            self.registry['ir.cron']._process_job(
                self.registry.db_name,
                self.registry.cursor(),
                {**self.cron.read(load=None)[0], **default_progress}
            )

        self.env.invalidate_all()
        self.assertEqual(self.cron.failure_count, 0, 'The cron should have failed one more time and reset to 0')
        self.assertEqual(self.cron.active, False, 'The cron should have been deactivated after 5 failures')
        self.assertTrue(notify.called)

    def test_cron_timeout_failure(self):
        self.cron._trigger()
        progress = self.env['ir.cron.progress'].create([{
                'cron_id': self.cron.id,
                'remaining': 0,
                'done': 0,
                'timed_out_counter': 3,
        }])
        self.env.flush_all()
        with self.enter_registry_test_mode(), mute_logger('odoo.addons.base.models.ir_cron'):
            self.registry['ir.cron']._process_job(
                self.registry.db_name,
                self.registry.cursor(),
                {**progress.read(fields=['done', 'remaining', 'timed_out_counter'], load=None)[0], 'progress_id': progress.id, **self.cron.read(load=None)[0]}
            )

        self.env.invalidate_all()
        self.assertEqual(self.cron.failure_count, 1, 'The cron should have failed once')
        self.assertEqual(self.cron.active, True, 'The cron should still be active')

        self.cron._trigger()
        with self.enter_registry_test_mode():
            self.registry['ir.cron']._process_job(
                self.registry.db_name,
                self.registry.cursor(),
                {**progress.read(fields=['done', 'remaining', 'timed_out_counter'], load=None)[0], 'progress_id': progress.id, **self.cron.read(load=None)[0]}
            )

        self.env.invalidate_all()
        self.assertEqual(self.cron.failure_count, 0, 'The cron should have succeeded and reset the counter')

    def test_cron_timeout_success(self):
        self.cron._trigger()
        progress = self.env['ir.cron.progress'].create([{
                'cron_id': self.cron.id,
                'remaining': 0,
                'done': 0,
                'timed_out_counter': 3,
        }])
        self.env.flush_all()
        with self.enter_registry_test_mode(), mute_logger('odoo.addons.base.models.ir_cron'):
            self.registry['ir.cron']._process_job(
                self.registry.db_name,
                self.registry.cursor(),
                {**progress.read(fields=['done', 'remaining', 'timed_out_counter'], load=None)[0], 'progress_id': progress.id, **self.cron.read(load=None)[0]}
            )

        self.env.invalidate_all()
        self.assertEqual(self.cron.failure_count, 1, 'The cron should have failed once')
        self.assertEqual(self.cron.active, True, 'The cron should still be active')

        self.cron._trigger()
        with self.enter_registry_test_mode():
            self.registry['ir.cron']._process_job(
                self.registry.db_name,
                self.registry.cursor(),
                {**progress.read(fields=['done', 'remaining', 'timed_out_counter'], load=None)[0], 'progress_id': progress.id, **self.cron.read(load=None)[0]}
            )

        self.env.invalidate_all()
        self.assertEqual(self.cron.failure_count, 0, 'The cron should have succeeded and reset the counter')

    def test_acquire_processed_job(self):
        # Test acquire job on already processed jobs
        job = self.env['ir.cron']._acquire_one_job(self.cr, self.cron.id)
        self.assertEqual(job, None, "No error should be thrown, job should just be none")

    def test_cron_deactivate(self):
        default_progress_values = {'done': 0, 'remaining': 0, 'timed_out_counter': 0}

        def mocked_run(self):
            self.env['ir.cron']._notify_progress(done=1, remaining=0, deactivate=True)

        self.cron._trigger()
        self.env.flush_all()
        with self.enter_registry_test_mode(), patch.object(self.registry['ir.actions.server'], 'run', mocked_run):
            self.registry['ir.cron']._process_job(
                self.registry.db_name,
                self.registry.cursor(),
                {**self.cron.read(load=None)[0], **default_progress_values}
            )

        self.env.invalidate_all()
        self.assertFalse(self.cron.active)
