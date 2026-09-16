import datetime

from odoo.tests import tagged

from .common import TestAccountAssetCommon


@tagged("post_install", "-at_install")
class TestAnnualClosingCheck(TestAccountAssetCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_return = cls.env["account.return"].create(
            {
                "name": "annual closing probe",
                "type_id": cls.env["account.return.type"].search([], limit=1).id,
                "date_from": "2022-01-01",
                "date_to": "2022-12-31",
                "company_id": cls.env.company.id,
            }
        )

    def _fixed_asset_checks(self, ignore=()):
        return [
            check
            for check in self.account_return._check_suite_annual_closing(list(ignore))
            if check["code"] == "check_fixed_assets"
        ]

    def test_the_check_is_raised_when_nothing_depreciated(self):
        self.assertEqual(len(self._fixed_asset_checks()), 1)
        self.assertEqual(self._fixed_asset_checks()[0]["result"], "todo")

    def test_the_check_is_silent_when_the_period_has_a_depreciation(self):
        asset = self.create_asset(10000, "yearly", 5)
        asset.action_confirm()
        self.assertIn(
            datetime.date(2022, 12, 31), asset.depreciation_move_ids.mapped("date")
        )

        self.assertFalse(self._fixed_asset_checks())

    def test_an_asset_paused_across_the_period_does_not_silence_the_check(self):
        asset = self.create_asset(10000, "yearly", 5)
        asset.action_confirm()
        asset._pause(date=datetime.date(2021, 12, 31))
        self.env["asset.modify"].create(
            {"asset_id": asset.id, "date": datetime.date(2023, 12, 31)}
        ).with_context(resume_after_pause=True).action_modify()
        self.env.flush_all()

        dates = asset.depreciation_move_ids.mapped("date")
        self.assertTrue([d for d in dates if d.year == 2021])
        self.assertTrue([d for d in dates if d.year == 2023])
        self.assertFalse(
            [d for d in dates if d.year == 2022], "the gap year is what this tests"
        )

        self.assertEqual(
            len(self._fixed_asset_checks()),
            1,
            "no entry falls in the period, so the reminder has to be raised",
        )

    def test_the_check_can_be_ignored_by_code(self):
        self.assertFalse(self._fixed_asset_checks(ignore=["check_fixed_assets"]))

    def test_a_draft_asset_does_not_silence_the_check(self):
        self.create_asset(10000, "yearly", 5)._create_depreciation_entries()

        self.assertEqual(len(self._fixed_asset_checks()), 1)
