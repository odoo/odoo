import datetime

from odoo.tests.common import TransactionCase


class TestDatetimeExtract(TransactionCase):

    def test_100_datetime_extract_mixin(self):
        kw_get_date_from_format = \
            self.env['kw.datetime.extract.mixin'].kw_get_date_from_format

        self.assertEqual(kw_get_date_from_format('2022-05-15'),
                         datetime.datetime(2022, 5, 15).date())
        self.assertEqual(kw_get_date_from_format(123), False)

        kw_mining_date = self.env['kw.datetime.extract.mixin'].kw_mining_date

        self.assertEqual(kw_mining_date('2022-05-15'),
                         datetime.datetime(2022, 5, 15).date())
        self.assertEqual(kw_mining_date(datetime.datetime(2022, 5, 15).date()),
                         datetime.datetime(2022, 5, 15).date())
        self.assertEqual(kw_mining_date(datetime.datetime(2022, 5, 15)),
                         datetime.datetime(2022, 5, 15).date())
        self.assertEqual(kw_mining_date(123, silent=True), False)
        self.assertEqual(kw_mining_date('123', silent=True), False)

        with self.assertRaises(Exception):
            kw_mining_date(123)
        with self.assertRaises(Exception):
            kw_mining_date('123')

        kw_get_datetime_from_format = \
            self.env['kw.datetime.extract.mixin'].kw_get_datetime_from_format

        self.assertEqual(kw_get_datetime_from_format('2022-05-15 12:11:23'),
                         datetime.datetime(2022, 5, 15, 12, 11, 23))
        self.assertEqual(kw_get_datetime_from_format(123), False)

        kw_mining_datetime = \
            self.env['kw.datetime.extract.mixin'].kw_mining_datetime

        self.assertEqual(kw_mining_datetime('2022-05-15 12:11:23'),
                         datetime.datetime(2022, 5, 15, 12, 11, 23))
        self.assertEqual(
            kw_mining_datetime(datetime.datetime(2022, 5, 15).date()),
            datetime.datetime(2022, 5, 15))
        self.assertEqual(
            kw_mining_datetime(datetime.datetime(2022, 5, 15, 12, 11, 23)),
            datetime.datetime(2022, 5, 15, 12, 11, 23))
        self.assertEqual(kw_mining_datetime(123, silent=True), False)
        self.assertEqual(kw_mining_datetime('123', silent=True), False)

        with self.assertRaises(Exception):
            kw_mining_datetime(123)
        with self.assertRaises(Exception):
            kw_mining_datetime('123')
