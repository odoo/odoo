# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from unittest.mock import patch
from freezegun import freeze_time

from odoo import fields
from odoo.tests.common import TransactionCase, RecordCapturer


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


class TestIrCron(TransactionCase, CronMixinCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        freezer = freeze_time(cls.cr.now())
        cls.frozen_datetime = freezer.start()
        cls.addClassCleanup(freezer.stop)

    def setUp(self):
        super(TestIrCron, self).setUp()

        self.cron = self.env['ir.cron'].create({
            'name': 'TestCron',
            'model_id': self.env.ref('base.model_res_partner').id,
            'state': 'code',
            'code': 'model.search([("name", "=", "TestCronRecord")]).write({"name": "You have been CRONWNED"})',
            'interval_number': 1,
            'interval_type': 'days',
            'numbercall': -1,
            'doall': False,
        })
        self.test_partner = self.env['res.partner'].create({
            'name': 'TestCronRecord'
        })
        self.test_partner2 = self.env['res.partner'].create({
            'name': 'NotTestCronRecord'
        })

    def test_cron_direct_trigger(self):
        self.assertFalse(self.cron.lastcall)
        self.assertEqual(self.test_partner.name, 'TestCronRecord')
        self.assertEqual(self.test_partner2.name, 'NotTestCronRecord')

        def patched_now(*args, **kwargs):
            return '2020-10-22 08:00:00'

        with patch('odoo.fields.Datetime.now', patched_now):
            self.cron.method_direct_trigger()

        self.assertEqual(fields.Datetime.to_string(self.cron.lastcall), '2020-10-22 08:00:00')
        self.assertEqual(self.test_partner.name, 'You have been CRONWNED')
        self.assertEqual(self.test_partner2.name, 'NotTestCronRecord')

    def test_cron_skip_unactive_triggers(self):
        # Situation: an admin disable the cron and another user triggers
        # the cron to be executed *now*, the cron shouldn't be ready and
        # the trigger should not be stored.

        self.cron.active = False
        self.cron.nextcall = fields.Datetime.now() + timedelta(days=2)
        self.cron.flush()
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
        self.cron.flush()

        # user triggers the cron to run *tomorrow of yesterday (=today)
        with self.capture_triggers() as capture:
            self.cron._trigger(at=fields.Datetime.now() + timedelta(days=1))

        # admin re-enable the cron
        self.cron.active = True
        self.cron.flush()

        # go today, check the cron should run
        self.frozen_datetime.tick(delta=timedelta(days=1))
        ready_jobs = self.registry['ir.cron']._get_all_ready_jobs(self.cr)
        self.assertIn(self.cron.id, [job['id'] for job in ready_jobs],
            "cron should be ready")
        self.assertTrue(capture.records, "trigger should has been kept")
