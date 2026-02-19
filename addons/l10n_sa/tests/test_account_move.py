from datetime import date, datetime, time

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSaAccountMove(AccountTestInvoicingCommon):

    @freeze_time('2026-06-15 14:00:00')
    def test_normalized_confirmation_datetime_future_date_rejected(self):
        """
            UTC time    -> 2026-06-15 14:00:00 (2026-06-15 17:00:00 in Asia/Riyadh)
            Setting the invoice date to 2026-06-16 would make the
            l10n_sa_confirmation_datetime -> 2026-06-16 14:00:00 UTC which is in the future
            this should raise an exception
        """
        with self.assertRaises(UserError):
            self.env['account.move']._get_normalized_l10n_sa_confirmation_datetime(date(2026, 6, 16))

    @freeze_time('2026-06-15 14:00:00')
    def test_normalized_confirmation_datetime_past_date(self):
        """
            UTC time    -> 2026-06-15 14:00:00 (2026-06-15 17:00:00 in Asia/Riyadh)
            Setting the invoice date to 2026-06-14 would make the
            l10n_sa_confirmation_datetime -> 2026-06-14 14:00:00 UTC which is in the past
            this should be fine
        """
        result = self.env['account.move']._get_normalized_l10n_sa_confirmation_datetime(date(2026, 6, 14))
        self.assertEqual(result, datetime(2026, 6, 14, 14, 0, 0))

    @freeze_time('2026-06-15 23:00:00')
    def test_normalized_confirmation_datetime_today_capped(self):
        """
            UTC time    -> 2026-06-15 23:00:00 (2026-06-16 02:00:00 in Asia/Riyadh)
            Setting the invoice date to 2026-06-16 (the date in Saudi Arabia) with
            invoice_time 05:00 SA (which is after now 02:00 SA), the min() should cap
            the result to now_sa -> 2026-06-15 23:00:00 UTC
        """
        result = self.env['account.move']._get_normalized_l10n_sa_confirmation_datetime(date(2026, 6, 16), time(5, 0, 0))
        self.assertEqual(result, datetime(2026, 6, 15, 23, 0, 0))
