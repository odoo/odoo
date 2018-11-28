# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from datetime import datetime, date, timedelta
from pytz import timezone
from unittest import TestCase, TestSuite, TextTestRunner

from odoo.tools import freeze_time
from odoo.tests.common import TransactionCase
from odoo import fields


class FreezeTimeTests(TransactionCase):

    def test_freeze_datetime(self):
        with freeze_time('2018-12-03 09:42:35'):
            frozen_dt = datetime.now()
            frozen_d = datetime.today()
            frozen_utc = datetime.utcnow()

        manual_dt = datetime(2018, 12, 3, 9, 42, 35)
        self.assertEqual(manual_dt, frozen_dt)
        self.assertEqual(manual_dt, frozen_d)
        self.assertEqual(manual_dt, frozen_utc)

    def test_freeze_date(self):
        with freeze_time('2018-12-03'):
            frozen = date.today()

        manual = date(2018, 12, 3)
        self.assertEqual(frozen, manual)

    def test_freeze_time(self):
        with freeze_time('2018-12-03'):
            frozen_t = time.time()
            frozen_strft = time.strftime("%a, %d-%b-%Y")

        manual_t = datetime(2018, 12, 3).timestamp()
        manual_strft = datetime(2018, 12, 3).strftime("%a, %d-%b-%Y")
        self.assertEqual(frozen_t, manual_t)
        self.assertEqual(frozen_strft, manual_strft)

    def test_context_mgr_freeze(self):
        real_time = fields.Datetime.now()

        with freeze_time('2018-12-03 09:05:25'):
            fake_time = fields.Datetime.now()

        self.assertNotEqual(real_time, fake_time)
        self.assertEqual(fields.Datetime.to_string(fake_time), '2018-12-03 09:05:25')

    @freeze_time('2018-12-03')
    def test_func_decorator_freeze(self):
        self.assertEqual(fields.Date.to_string(fields.Date.today()), '2018-12-03')

    def test_manual_freeze(self):
        patcher = freeze_time('2018-12-03 09:15:45')
        real_time = fields.Datetime.now()

        patcher.apply()
        fake_time = fields.Datetime.now()
        patcher.revert()

        self.assertNotEqual(real_time, fake_time)
        self.assertEqual(fields.Datetime.to_string(fake_time), '2018-12-03 09:15:45')

    def test_class_decorator_good_freeze(self):
        @freeze_time('2018-12-02')
        class Foo(TestCase):
            def test_time(self):
                self.assertEqual(datetime.now(), datetime(2018, 12, 2))

        def suite():
            suite = TestSuite()
            suite.addTest(Foo('test_time'))
            return suite

        runner = TextTestRunner(verbosity=0)
        runner.run(suite())

    def test_class_decorator_bad_freeze(self):
        with self.assertRaises(AssertionError):
            @freeze_time('2018-12-03')
            class Bar:
                pass

    def test_after_revert(self):
        real_before = fields.Datetime.now()

        with freeze_time('2018-12-03 09:33:55'):
            fake_time = fields.Datetime.now()
        real_after = fields.Datetime.now()

        self.assertNotEqual(real_before, fake_time)
        self.assertNotEqual(real_after, fake_time)
        self.assertGreaterEqual(real_after, real_before)

    def test_nested_freeze(self):
        real_before = fields.Datetime.now()

        with freeze_time('2018-12-03 09:38:10'):
            fake_before = fields.Datetime.now()

            with freeze_time('2018-12-03 09:40:00'):
                fake_fake = fields.Datetime.now()

            fake_after = fields.Datetime.now()

        real_after = fields.Datetime.now()

        self.assertEqual(fake_before, fake_after)
        self.assertNotEqual(fake_before, fake_fake)
        self.assertNotEqual(fake_fake, real_before)
        self.assertNotEqual(fake_fake, real_after)
        self.assertGreaterEqual(real_after, real_before)

    def test_same_context_freeze(self):
        f1 = freeze_time('2012-03-07')
        f2 = freeze_time('2015-01-01')

        with f1:
            t1 = datetime.now()
            with f2:
                t2 = datetime.now()
            t3 = datetime.now()

        self.assertEqual(t1, t3)
        self.assertNotEqual(t1, t2)

    def test_datetime_to_date_freeze(self):
        with freeze_time('2018-05-05 09:12:55'):
            dt = datetime.now()
            d = dt.date()

        manual_d = date(2018, 5, 5)
        self.assertEqual(d, manual_d)

    def test_datetime_addition(self):
        with freeze_time('2018-05-05 09:12:55'):
            dt = datetime.now()
            dt2 = dt + timedelta(hours=2)

        manual_dt = datetime(2018, 5, 5, 11, 12, 55)
        self.assertEqual(dt2, manual_dt)

    def test_datetime_subtraction(self):
        with freeze_time('2018-05-05 09:12:55'):
            dt = datetime.now()
            dt2 = timedelta(hours=-2) + dt
            dt3 = dt - timedelta(hours=2)
            dt4 = dt - dt

        manual_dt = datetime(2018, 5, 5, 7, 12, 55)
        self.assertEqual(dt3, manual_dt)
        self.assertEqual(dt4, timedelta(0))
        self.assertEqual(dt2, dt3)

    def test_astimezone_freeze(self):
        gmt = timezone('GMT')
        gmt2 = timezone('Etc/GMT+2')

        with freeze_time('2018-05-05 09:12:53'):
            dt = datetime.now(gmt2)
            dt2 = dt.astimezone(gmt)

        manual_dt_gmt = datetime(2018, 5, 5, 9, 12, 53, tzinfo=gmt)
        self.assertEqual(dt2.tzinfo, gmt)
        self.assertEqual(dt2, manual_dt_gmt)

    def test_date_addition(self):
        with freeze_time('2018-05-05'):
            d = date.today()
            d2 = d + timedelta(days=1)

        manual_d = date(2018, 5, 6)
        self.assertEqual(d2, manual_d)

    def test_date_subtraction(self):
        with freeze_time('0001-01-02'):
            d = date.today()
            d2 = d - timedelta(days=1)
            d3 = timedelta(days=-1) + d
            d4 = d - d2

        manual_d = date.min
        self.assertEqual(d2, manual_d)
        self.assertEqual(d4, timedelta(days=1))
        self.assertEqual(d2, d3)

    def test_no_context_escape(self):
        with freeze_time('2018-03-03'):
            dt = datetime.now()
            dt2 = dt.now()
            dt3 = dt + timedelta(hours=5)
            dt4 = dt3.now()
            d = dt.date()
            d2 = d.today()
            dt5 = datetime.min
            dt6 = dt5.min

        self.assertEqual(dt, dt2)
        self.assertEqual(dt4, dt2)
        self.assertEqual(d, d2)
        self.assertTrue(dt5 is dt6)

    def test_fake_type(self):
        real_dt = datetime(2018, 3, 3)

        with freeze_time('2018-03-03'):
            fake_dt = datetime.now()
            fake_d = date.today()

        self.assertIsInstance(fake_dt, datetime)
        self.assertIsInstance(fake_dt, date)
        self.assertIsInstance(fake_d, date)
        self.assertNotIsInstance(fake_d, datetime)
        self.assertEqual(real_dt, fake_dt)
        self.assertEqual(fake_dt, real_dt)

    def test_graceful_context_exit(self):
        try:
            with freeze_time('2018-03-03'):
                fake_dt = datetime.now()
            raise ValueError
        except ValueError:
            pass

        self.assertNotEqual(fake_dt, datetime.now())
