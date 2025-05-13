from datetime import date, datetime

from odoo.tests.common import HttpCase, TransactionCase, freeze_time, tagged


@tagged('post_install', '-at_install')
class TestFreezeTimeMethodDecorator(TransactionCase):
    @freeze_time('2022-02-02')
    def test_freeze_time_method_decorator_with_date_string(self):
        self.assertEqual(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '2022-02-02 00:00:00')

    @freeze_time('2022-02-02 02:02')
    def test_freeze_time_method_decorator_with_datetime_string(self):
        self.assertEqual(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '2022-02-02 02:02:00')

    @freeze_time(date(2023, 3, 3))
    def test_freeze_time_method_decorator_with_date(self):
        self.assertEqual(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '2023-03-03 00:00:00')

    @freeze_time(datetime(2024, 4, 4, 4, 4))
    def test_freeze_time_method_decorator_with_datetime(self):
        self.assertEqual(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '2024-04-04 04:04:00')


@freeze_time('2021-01-01')
@tagged('post_install', '-at_install')
class TestFreezeTimeClassDecorator(TransactionCase):
    # Both methods should be frozen.
    def test_freeze_time_class_decorator_01(self):
        self.assertEqual(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '2021-01-01 00:00:00')

    def test_freeze_time_class_decorator_02(self):
        self.assertEqual(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '2021-01-01 00:00:00')


# TODO (rugo) Why a special test for HttpCase ?
@freeze_time(datetime(2024, 4, 4, 4, 4))
@tagged('post_install', '-at_install')
class TestHttpCaseFreezeTimeClassDecorator(HttpCase):
    # Both methods should be frozen.
    def test_http_freeze_time_class_decorator_01(self):
        self.assertEqual(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '2024-04-04 04:04:00')

    def test_http_freeze_time_class_decorator_02(self):
        self.assertEqual(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '2024-04-04 04:04:00')


@tagged('post_install', '-at_install')
class TestFreezeTimeContextManager(TransactionCase):
    def test_freeze_time_context_manager(self):
        self.assertNotEqual(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '2024-04-04 04:04:00', "The datetime should not be altered by a freeze_time from the previous class")
        with freeze_time('2025-05-05 05:05') as frozen_time:
            self.assertEqual(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '2025-05-05 05:05:00')
            frozen_time.move_to('2026-06-06 06:06')
            self.assertEqual(datetime.now().strftime('%Y-%m-%d %H:%M'), '2026-06-06 06:06')
