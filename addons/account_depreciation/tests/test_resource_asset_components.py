from odoo import Command, fields
from odoo.tests import tagged

from .common import TestAccountAssetCommon


@tagged("post_install", "-at_install")
class TestResourceAssetComponents(TestAccountAssetCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vehicle = cls.env.ref("resource_asset.kind_vehicle")
        cls.account = cls.company_data["default_account_assets"].copy()
        cls.account.write({"can_create_asset": True, "create_asset": "draft"})
        cls.depreciable = cls._profile("Automovil FF")
        cls.non_depreciable = cls._profile("Automovil NF")

    @classmethod
    def _profile(cls, name):
        return cls.env["account.depreciation.profile"].create(
            {
                "name": name,
                "kind_id": cls.env.ref("resource_asset.kind_vehicle").id,
                "account_asset_id": cls.company_data["default_account_assets"].id,
                "account_depreciation_id": cls.company_data[
                    "default_account_assets"
                ].id,
                "account_depreciation_expense_id": cls.company_data[
                    "default_account_expense"
                ].id,
                "depreciation_journal_id": cls.company_data["default_journal_misc"].id,
                "depreciation_duration": 5,
                "depreciation_period": "12",
            }
        )

    def _bill(self, price=10000, quantity=1, asset=None, label="Truck"):
        line = {
            "name": label,
            "account_id": self.account.id,
            "price_unit": price,
            "quantity": quantity,
            "tax_ids": [Command.clear()],
        }
        if asset is not None:
            line["asset_id"] = asset.id
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.env["res.partner"].create({"name": "Vendor"}).id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [Command.create(line)],
            }
        )
        bill.action_post()
        return bill

    def _plain_asset(self, name="Truck 7"):
        return self.env["resource.asset"].create(
            {"name": name, "kind_id": self.vehicle.id}
        )

    def test_one_profile_creates_one_root_asset(self):
        self.account.depreciation_profile_ids = self.depreciable
        assets = self._bill().capitalised_asset_ids
        self.assertEqual(len(assets), 1)
        self.assertFalse(assets.parent_id)
        self.assertEqual(assets.depreciation_profile_id, self.depreciable)

    def test_a_second_profile_lands_on_a_component(self):
        self.account.depreciation_profile_ids = self.depreciable | self.non_depreciable
        assets = self._bill().capitalised_asset_ids
        self.assertEqual(len(assets), 2)
        root = assets.filtered(lambda asset: not asset.parent_id)
        component = assets - root
        self.assertEqual(len(root), 1)
        self.assertEqual(component.parent_id, root)
        self.assertIn(component.depreciation_profile_id.name, component.name)
        self.assertIn(root.name, component.name)

    def test_a_line_naming_an_asset_without_a_board_depreciates_that_asset(self):
        self.account.depreciation_profile_ids = self.depreciable
        van = self._plain_asset()
        assets = self._bill(asset=van).capitalised_asset_ids
        self.assertEqual(assets, van)
        self.assertEqual(van.depreciation_state, "draft")
        self.assertFalse(van.parent_id)

    def test_a_line_naming_a_depreciating_asset_creates_a_component(self):
        self.account.depreciation_profile_ids = self.depreciable
        van = self._plain_asset()
        self._bill(asset=van)
        second = self._bill(asset=van, label="Crane").capitalised_asset_ids
        self.assertNotEqual(second, van)
        self.assertEqual(second.parent_id, van)
        self.assertIn(van.name, second.name)

    def test_a_line_naming_an_asset_with_two_profiles_keeps_one_root(self):
        self.account.depreciation_profile_ids = self.depreciable | self.non_depreciable
        van = self._plain_asset()
        assets = self._bill(asset=van).capitalised_asset_ids
        self.assertEqual(len(assets), 2)
        self.assertIn(van, assets)
        self.assertEqual((assets - van).parent_id, van)

    def test_several_units_of_one_line_are_siblings(self):
        self.account.multiple_assets_per_line = True
        self.account.depreciation_profile_ids = self.depreciable
        assets = self._bill(price=1000, quantity=3).capitalised_asset_ids
        self.assertEqual(len(assets), 3)
        self.assertFalse(assets.parent_id)
