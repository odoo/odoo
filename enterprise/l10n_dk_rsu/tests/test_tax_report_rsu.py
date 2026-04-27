from datetime import datetime
from odoo import fields
from odoo.tests import tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.addons.l10n_dk_rsu.wizard.tax_report_wizard import FrequencyCode


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nDKTaxReportRSU(TestAccountReportsCommon):
    @classmethod
    @TestAccountReportsCommon.setup_country('dk')
    def setUpClass(cls):
        super().setUpClass()

    def test_calculate_settlement_period(self):
        wizard = self.env['l10n_dk_rsu.tax.report.calendar.wizard'].new({})
        # test immediately
        res1, res2 = wizard._calculate_settlement_period(FrequencyCode.IMMEDIATELY_FREQUENCY_CODE, datetime(day=27, month=2, year=2023))
        self.assertEqual(res1, datetime(day=27, month=2, year=2023))
        self.assertEqual(res2, datetime(day=27, month=2, year=2023))

        # test daily
        res1, res2 = wizard._calculate_settlement_period(FrequencyCode.DAILY_FREQUENCY_CODE, datetime(day=27, month=2, year=2023))
        self.assertEqual(res1, datetime(day=26, month=2, year=2023))
        self.assertEqual(res2, datetime(day=27, month=2, year=2023))

        # test weekly
        res1, res2 = wizard._calculate_settlement_period(FrequencyCode.WEEKLY_FREQUENCY_CODE, datetime(day=27, month=2, year=2023))
        self.assertEqual(res1, datetime(day=27, month=2, year=2023))
        self.assertEqual(fields.Datetime.to_datetime(res2.date()), datetime(day=5, month=3, year=2023))

        # test two weeks
        res1, res2 = wizard._calculate_settlement_period(FrequencyCode.TWO_WEEKS_FREQUENCY_CODE, datetime(day=27, month=2, year=2023))
        self.assertEqual(res1, datetime(day=20, month=2, year=2023))
        self.assertEqual(fields.Datetime.to_datetime(res2.date()), datetime(day=5, month=3, year=2023))

        # test monthly
        res1, res2 = wizard._calculate_settlement_period(FrequencyCode.MONTH_FREQUENCY_CODE, datetime(day=27, month=2, year=2023))
        self.assertEqual(res1, datetime(day=1, month=2, year=2023))
        self.assertEqual(res2, datetime(day=28, month=2, year=2023))

        res1, res2 = wizard._calculate_settlement_period(FrequencyCode.MONTH_FREQUENCY_CODE, datetime(day=25, month=4, year=2023))
        self.assertEqual(res1, datetime(day=1, month=4, year=2023))
        self.assertEqual(res2, datetime(day=30, month=4, year=2023))

        # test quarterly
        res1, res2 = wizard._calculate_settlement_period(FrequencyCode.QUARTER_FREQUENCY_CODE, datetime(day=1, month=6, year=2023))
        self.assertEqual(res1, datetime(day=1, month=4, year=2023))
        self.assertEqual(res2, datetime(day=30, month=6, year=2023))

        res1, res2 = wizard._calculate_settlement_period(FrequencyCode.QUARTER_FREQUENCY_CODE, datetime(day=1, month=9, year=2023))
        self.assertEqual(res1, datetime(day=1, month=7, year=2023))
        self.assertEqual(res2, datetime(day=30, month=9, year=2023))

        res1, res2 = wizard._calculate_settlement_period(FrequencyCode.QUARTER_FREQUENCY_CODE, datetime(day=1, month=3, year=2024))
        self.assertEqual(res1, datetime(day=1, month=1, year=2024))
        self.assertEqual(res2, datetime(day=31, month=3, year=2024))

        # test half yearly
        res1, res2 = wizard._calculate_settlement_period(FrequencyCode.HALF_YEAR_FREQUENCY_CODE, datetime(day=1, month=9, year=2023))
        self.assertEqual(res1, datetime(day=1, month=7, year=2023))
        self.assertEqual(fields.Datetime.to_datetime(res2.date()), datetime(day=31, month=12, year=2023))

        res1, res2 = wizard._calculate_settlement_period(FrequencyCode.HALF_YEAR_FREQUENCY_CODE, datetime(day=1, month=3, year=2024))
        self.assertEqual(res1, datetime(day=1, month=1, year=2024))
        self.assertEqual(fields.Datetime.to_datetime(res2.date()), datetime(day=30, month=6, year=2024))

        # test yearly
        res1, res2 = wizard._calculate_settlement_period(FrequencyCode.YEAR_FREQUENCY_CODE, datetime(day=1, month=1, year=2024))
        self.assertEqual(res1, datetime(day=1, month=1, year=2024))
        self.assertEqual(fields.Datetime.to_datetime(res2.date()), datetime(day=31, month=12, year=2024))
