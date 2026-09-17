from datetime import datetime, timedelta

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestResourceAssetPart(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Part = cls.env["resource.asset.part"]
        cls.kind = cls.env["resource.asset.kind"].create(
            {"name": "Parts Truck", "code": "parts_truck"}
        )
        cls.tyres = cls.env["product.category"].create({"name": "Tyres"})
        cls.left, cls.right = cls.env["resource.asset.kind.position"].create(
            [
                {
                    "kind_id": cls.kind.id,
                    "name": "Front-left tyre",
                    "code": "tyre_fl",
                    "product_category_id": cls.tyres.id,
                    "expected_life_days": 180,
                    "meter_kind": "odometer",
                    "expected_life_meter": 40000,
                },
                {
                    "kind_id": cls.kind.id,
                    "name": "Front-right tyre",
                    "code": "tyre_fr",
                    "product_category_id": cls.tyres.id,
                },
            ]
        )
        cls.tyre = cls.env["product.product"].create(
            {"name": "Tyre 295/80", "categ_id": cls.tyres.id}
        )
        cls.vendor = cls.env["res.partner"].create({"name": "Tyre Shop"})
        cls.asset = cls.env["resource.asset"].create(
            {"name": "Truck 7", "kind_id": cls.kind.id}
        )
        cls.odometer = cls.env["resource.asset.meter"].create(
            {"asset_id": cls.asset.id, "name": "Odometer", "kind": "odometer"}
        )
        cls.manager = new_test_user(
            cls.env,
            login="parts_manager",
            groups="base.group_user,resource_asset.group_asset_manager",
        )
        cls.user = new_test_user(
            cls.env,
            login="parts_user",
            groups="base.group_user,resource_asset.group_asset_user",
        )

    def _install(self, when, position=None, **vals):
        return self.Part.create(
            {
                "asset_id": self.asset.id,
                "position_id": (position or self.left).id,
                "product_id": self.tyre.id,
                "date_installed": when,
                "vendor_id": self.vendor.id,
                "removed_returned": True,
                "state": "installed",
                **vals,
            }
        )

    def _reasons(self, part):
        return set(part.flag_ids.filtered(lambda f: f.state == "open").mapped("reason"))

    def test_the_first_part_at_a_position_is_the_baseline(self):
        part = self._install(datetime(2026, 1, 1))

        self.assertEqual(part.state, "installed")
        self.assertFalse(part.previous_part_id)
        self.assertEqual(part.review_state, "none")

    def test_a_replacement_removes_the_part_it_replaces(self):
        first = self._install(datetime(2026, 1, 1))
        second = self._install(datetime(2026, 12, 1))

        self.assertEqual(second.previous_part_id, first)
        self.assertEqual(first.state, "removed")
        self.assertEqual(first.date_removed, datetime(2026, 12, 1))
        self.assertEqual(second.review_state, "none")

    def test_two_positions_replaced_the_same_day_are_not_a_repeat(self):
        self._install(datetime(2026, 1, 1))
        right = self._install(datetime(2026, 1, 1), position=self.right)

        self.assertFalse(right.previous_part_id)
        self.assertEqual(right.review_state, "none")

    def test_a_replacement_within_the_expected_days_is_flagged(self):
        self._install(datetime(2026, 1, 1))
        second = self._install(datetime(2026, 2, 1))

        self.assertEqual(self._reasons(second), {"within_life"})
        self.assertEqual(second.review_state, "flagged")
        self.assertEqual(self.asset.part_flagged_count, 1)

    def test_a_replacement_within_the_expected_distance_is_flagged(self):
        self.left.expected_life_days = 0
        self.odometer.record(10000, date=datetime(2025, 12, 31))
        self._install(datetime(2026, 1, 1))
        self.odometer.record(25000, date=datetime(2026, 11, 30))
        second = self._install(datetime(2026, 12, 1))

        self.assertEqual(second.meter_installed, 25000)
        self.assertEqual(self._reasons(second), {"within_life"})

    def test_no_reading_on_either_side_compares_no_distance(self):
        self.left.expected_life_days = 0
        self._install(datetime(2026, 1, 1))
        second = self._install(datetime(2026, 1, 2))

        self.assertFalse(second.meter_id)
        self.assertEqual(second.review_state, "none")

    def test_a_replacement_under_the_previous_warranty_opens_a_claim(self):
        self.left.expected_life_days = 0
        self._install(datetime(2026, 1, 1), warranty_date=datetime(2027, 1, 1).date())
        second = self._install(datetime(2026, 6, 1))

        self.assertEqual(self._reasons(second), {"within_warranty"})
        self.assertTrue(second.activity_ids)

    def test_a_removed_serial_that_is_not_the_installed_one_is_flagged(self):
        self.left.expected_life_days = 0
        self._install(datetime(2026, 1, 1), serial="TY-001")
        second = self._install(datetime(2026, 6, 1), removed_serial="TY-999")

        self.assertEqual(self._reasons(second), {"serial_mismatch"})

    def test_a_matching_removed_serial_raises_nothing(self):
        self.left.expected_life_days = 0
        self._install(datetime(2026, 1, 1), serial="TY-001")
        second = self._install(datetime(2026, 6, 1), removed_serial=" ty-001 ")

        self.assertEqual(second.review_state, "none")

    def test_a_vendor_part_not_returned_is_flagged_until_it_arrives(self):
        part = self._install(datetime(2026, 1, 1), removed_returned=False)
        part._flag_not_returned()
        self.assertEqual(self._reasons(part), {"not_returned"})

        part.removed_returned = True

        self.assertEqual(part.review_state, "cleared")
        self.assertEqual(part.flag_ids.state, "resolved")

    def test_only_an_asset_manager_clears_a_flag(self):
        self._install(datetime(2026, 1, 1))
        second = self._install(datetime(2026, 2, 1))
        Clear = self.env["resource.asset.part.clear"]

        with self.assertRaises(UserError):
            second.with_user(self.user)._clear_flags("looks fine")

        Clear.with_user(self.manager).create(
            {"part_ids": [(6, 0, second.ids)], "note": "Blowout, road damage"}
        ).action_clear()

        self.assertEqual(second.review_state, "cleared")
        self.assertEqual(second.flag_ids.cleared_user_id, self.manager)
        self.assertEqual(second.flag_ids.clear_note, "Blowout, road damage")

    def test_an_installed_part_is_evidence(self):
        part = self._install(datetime(2026, 1, 1), serial="TY-001")

        with self.assertRaises(UserError):
            part.serial = "TY-002"
        with self.assertRaises(UserError):
            part.unlink()
        with self.assertRaises(UserError):
            part.removed_returned = False

    def test_a_planned_part_changes_freely_and_installs_later(self):
        part = self.Part.create(
            {
                "asset_id": self.asset.id,
                "position_id": self.left.id,
                "product_id": self.tyre.id,
            }
        )
        part.serial = "TY-010"
        part.action_install()

        self.assertEqual(part.state, "installed")
        self.assertTrue(part.date_installed)

    def test_a_position_takes_parts_of_its_category_on_assets_of_its_kind(self):
        other = self.env["product.product"].create({"name": "Battery"})
        with self.assertRaises(ValidationError):
            self._install(datetime(2026, 1, 1), product_id=other.id)

        van = self.env["resource.asset"].create(
            {"name": "Van", "kind_id": self.env.ref("resource_asset.kind_tool").id}
        )
        with self.assertRaises(ValidationError):
            self._install(datetime(2026, 1, 1), asset_id=van.id)

    def test_a_backdated_part_does_not_count_a_later_one_as_previous(self):
        later = self._install(datetime(2026, 6, 1))
        earlier = self._install(datetime(2025, 1, 1) + timedelta(days=1))

        self.assertFalse(earlier.previous_part_id)
        self.assertEqual(later.state, "installed")
