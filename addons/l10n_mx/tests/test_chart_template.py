from odoo.tests import tagged

from odoo.addons.l10n_mx.tests.common import TestMxCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestMxChartTemplate(TestMxCommon):
    """What a company created on the `mx` template actually gets."""

    def _account(self, code):
        return (
            self.env["account.account"]
            .with_company(self.company_data["company"])
            .search([("code", "=", code)])
        )

    def test_the_fixed_asset_block_is_created(self):
        """The SAT fixed-asset accounts, their accumulated depreciation and the
        matching depreciation expense accounts."""
        expected = {
            "153.01.01": "asset_fixed",  # Machinery & equipment
            "154.01.01": "asset_fixed",  # Vehicles
            "155.01.01": "asset_fixed",  # Furniture & office equipment
            "156.01.01": "asset_fixed",  # Technology
            "171.02.01": "asset_fixed",  # Acc. depreciation, machinery
            "171.03.01": "asset_fixed",  # Acc. depreciation, vehicles
            "183.01.01": "asset_non_current",  # Acc. amortization, deferred
            "613.02.01": "expense_direct_cost",  # Depreciation, machinery
            "614.01.01": "expense_direct_cost",  # Amortization, deferred
        }
        for code, account_type in expected.items():
            account = self._account(code)
            self.assertTrue(account, f"account {code} is missing from the MX chart")
            self.assertEqual(
                account.account_type,
                account_type,
                f"account {code} has the wrong type",
            )

    def test_accounts_carry_their_description(self):
        """The template now explains what each account is for.

        `description` is declared by account_coa (models/account_account.py:32)
        and reaches l10n_mx because account depends on account_coa. This
        account already existed; what is new is the text on it.
        """
        stock_valuation = self._account("115.01.01")
        self.assertTrue(stock_valuation)
        self.assertEqual(
            stock_valuation.description,
            "Goods stored in your warehouse, as part of your activity",
        )

    def test_the_depreciation_profiles_are_created(self):
        """The nine SAT depreciation profiles, and the accounts they post to.

        Upstream hangs these off `account.asset` records in `state='model'`,
        which lived in enterprise. This fork moved asset management into core
        as `account_depreciation`, where the same concept is its own model,
        `account.depreciation.profile`. So this needs no skip: if the module
        is installed the profiles must exist, and they are reachable from the
        account through `depreciation_profile_ids`.
        """
        if "account.depreciation.profile" not in self.env:
            self.skipTest("account_depreciation is not installed")
        profiles = (
            self.env["account.depreciation.profile"]
            .with_company(self.company_data["company"])
            .search([])
        )
        self.assertEqual(len(profiles), 9)
        machinery = profiles.filtered(lambda p: p.name == "Machinery & equipment")
        self.assertTrue(machinery, "the machinery profile is missing")
        self.assertEqual(machinery.depreciation_period, "12")
        self.assertEqual(machinery.depreciation_duration, 5)
        self.assertEqual(machinery.account_asset_id, self._account("153.01.01"))
        self.assertEqual(machinery.account_depreciation_id, self._account("171.02.01"))
        self.assertEqual(
            machinery.account_depreciation_expense_id, self._account("613.02.01")
        )

    def test_the_fixed_asset_accounts_offer_their_profile(self):
        """The link the user actually meets: opening the asset account shows
        the profile, so a vendor bill on it can raise the asset by itself."""
        if "account.depreciation.profile" not in self.env:
            self.skipTest("account_depreciation is not installed")
        machinery_account = self._account("153.01.01")
        self.assertTrue(machinery_account)
        self.assertIn(
            "Machinery & equipment",
            machinery_account.depreciation_profile_ids.mapped("name"),
        )
