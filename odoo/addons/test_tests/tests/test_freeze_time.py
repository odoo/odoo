# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime, timedelta
from odoo.tests.common import tagged, TransactionCase, freeze_time


@tagged('post_install', '-at_install')
class TestFreezeTimeUnit(TransactionCase):
    def test_freeze_time_with_no_parameters(self):
        freeze_time()

    def test_freeze_time_raw(self):
        freezer = freeze_time('2019-01-01').freezer
        freezer.start()

        self.assertEqual(datetime.now(), datetime(2019, 1, 1))

        freezer.stop()

        self.assertNotEqual(datetime.now(), datetime(2019, 1, 1))


@tagged('post_install', '-at_install')
class TestFreezeTimeMethodDecorator(TransactionCase):

    @freeze_time('2020-01-01')
    def test_freeze_time_method_decorator_with_date_string(self):
        self.assertEqual(datetime.now(), datetime(2020, 1, 1))

    @freeze_time('Jan 2th, 2020')
    def test_freeze_time_method_decorator_with_fancy_date_string(self):
        self.assertEqual(datetime.now(), datetime(2020, 1, 2))

    @freeze_time(date(2020, 1, 3))
    def test_freeze_time_method_decorator_with_date(self):
        self.assertEqual(datetime.now(), datetime(2020, 1, 3))

    @freeze_time('2020-01-04 04:04')
    def test_freeze_time_method_decorator_with_datetime_string(self):
        self.assertEqual(datetime.now(), datetime(2020, 1, 4, 4, 4))

    @freeze_time(datetime(2020, 1, 5, 5, 5))
    def test_freeze_time_method_decorator_with_datetime(self):
        self.assertEqual(datetime.now(), datetime(2020, 1, 5, 5, 5))

    @freeze_time('2020-01-06 06:06', tz_offset=-1)
    def test_freeze_time_method_decorator_with_tz_offset_int(self):
        self.assertEqual(datetime.utcnow(), datetime(2020, 1, 6, 6, 6))
        self.assertEqual(datetime.now(), datetime(2020, 1, 6, 5, 6))

    @freeze_time('2020-01-07 08:08', tz_offset=-timedelta(hours=1, minutes=1))
    def test_freeze_time_method_decorator_with_tz_offset_datetime(self):
        self.assertEqual(datetime.utcnow(), datetime(2020, 1, 7, 8, 8))
        self.assertEqual(datetime.now(), datetime(2020, 1, 7, 7, 7))

    @freeze_time('2120-01-08 08:08', tick=True)
    def test_freeze_time_method_decorator_with_tick(self):
        self.assertGreater(datetime.now(), datetime(2120, 1, 8, 8, 8))

    @freeze_time('2020-01-09', as_kwarg='frozen_time')
    def test_freeze_time_method_decorator_with_as_kwarg(self, frozen_time):
        self.assertEqual(datetime.now(), datetime(2020, 1, 9))
        self.assertEqual(frozen_time.time_to_freeze.today(), datetime(2020, 1, 9))

    @freeze_time('2020-01-10 10:10:00', auto_tick_seconds=15)
    def test_freeze_time_method_decorator_with_auto_tick_seconds(self):
        self.assertEqual(datetime.now(), datetime(2020, 1, 10, 10, 10, 0))
        self.assertEqual(datetime.now(), datetime(2020, 1, 10, 10, 10, 15))


@freeze_time('2021-01-01')
@tagged('post_install', '-at_install')
class TestFreezeTimeClassDecoratorWithDateString(TransactionCase):
    # Both methods should have the same freezed time.
    def test_freeze_time_class_decorator_with_date_string_01(self):
        self.assertEqual(datetime.now(), datetime(2021, 1, 1))

    def test_freeze_time_class_decorator_with_date_string_02(self):
        self.assertEqual(datetime.now(), datetime(2021, 1, 1))


@freeze_time('Jan 2th, 2021')
@tagged('post_install', '-at_install')
class TestFreezeTimeClassDecoratorWithFancyDateString(TransactionCase):
    # Both methods should have the same freezed time.
    def test_freeze_time_class_decorator_with_fancy_date_string_01(self):
        self.assertEqual(datetime.now(), datetime(2021, 1, 2))

    def test_freeze_time_class_decorator_with_fancy_date_string_02(self):
        self.assertEqual(datetime.now(), datetime(2021, 1, 2))


@freeze_time(date(2021, 1, 3))
@tagged('post_install', '-at_install')
class TestFreezeTimeClassDecoratorWithDate(TransactionCase):
    # Both methods should have the same freezed time.
    def test_freeze_time_class_decorator_with_date_01(self):
        self.assertEqual(datetime.now(), datetime(2021, 1, 3))

    def test_freeze_time_class_decorator_with_date_02(self):
        self.assertEqual(datetime.now(), datetime(2021, 1, 3))


@freeze_time('2021-01-04 04:04')
@tagged('post_install', '-at_install')
class TestFreezeTimeClassDecoratorWithDatetimeString(TransactionCase):
    # Both methods should have the same freezed time.
    def test_freeze_time_class_decorator_with_datetime_string_01(self):
        self.assertEqual(datetime.now(), datetime(2021, 1, 4, 4, 4))

    def test_freeze_time_class_decorator_with_datetime_string_02(self):
        self.assertEqual(datetime.now(), datetime(2021, 1, 4, 4, 4))


@freeze_time(datetime(2021, 1, 5, 5, 5))
@tagged('post_install', '-at_install')
class TestFreezeTimeClassDecoratorWithDatetime(TransactionCase):
    # Both methods should have the same freezed time.
    def test_freeze_time_class_decorator_with_datetime_01(self):
        self.assertEqual(datetime.now(), datetime(2021, 1, 5, 5, 5))

    def test_freeze_time_class_decorator_with_datetime_02(self):
        self.assertEqual(datetime.now(), datetime(2021, 1, 5, 5, 5))


@freeze_time('2021-01-06 06:06', tz_offset=-1)
@tagged('post_install', '-at_install')
class TestFreezeTimeClassDecoratorWithTzOffsetInt(TransactionCase):
    # Both methods should have the same freezed time.
    def test_freeze_time_class_decorator_with_tz_offset_int_01(self):
        self.assertEqual(datetime.utcnow(), datetime(2021, 1, 6, 6, 6))
        self.assertEqual(datetime.now(), datetime(2021, 1, 6, 5, 6))

    def test_freeze_time_class_decorator_with_tz_offset_int_02(self):
        self.assertEqual(datetime.utcnow(), datetime(2021, 1, 6, 6, 6))
        self.assertEqual(datetime.now(), datetime(2021, 1, 6, 5, 6))


@freeze_time('2021-01-07 08:08', tz_offset=-timedelta(hours=1, minutes=1))
@tagged('post_install', '-at_install')
class TestFreezeTimeClassDecoratorWithTzOffsetDatetime(TransactionCase):
    # Both methods should have the same freezed time.
    def test_freeze_time_class_decorator_with_tz_offset_datetime_01(self):
        self.assertEqual(datetime.utcnow(), datetime(2021, 1, 7, 8, 8))
        self.assertEqual(datetime.now(), datetime(2021, 1, 7, 7, 7))

    def test_freeze_time_class_decorator_with_tz_offset_datetime_02(self):
        self.assertEqual(datetime.utcnow(), datetime(2021, 1, 7, 8, 8))
        self.assertEqual(datetime.now(), datetime(2021, 1, 7, 7, 7))


@freeze_time('2121-01-08 08:08', tick=True)
@tagged('post_install', '-at_install')
class TestFreezeTimeClassDecoratorWithTick(TransactionCase):
    # Both methods should have the same freezed time.
    def test_freeze_time_class_decorator_with_tick_01(self):
        self.assertGreater(datetime.now(), datetime(2021, 1, 8, 8, 8))

    def test_freeze_time_class_decorator_with_tick_02(self):
        self.assertGreater(datetime.now(), datetime(2021, 1, 8, 8, 8))


@tagged('post_install', '-at_install')
class TestFreezeTimeContextManager(TransactionCase):

    def test_freeze_time_context_manager(self):
        self.assertNotEqual(datetime.now(), datetime(2022, 1, 1))

        with freeze_time('2022-01-01'):
            self.assertEqual(datetime.now(), datetime(2022, 1, 1))

        self.assertNotEqual(datetime.now(), datetime(2022, 1, 1))
