from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAssetTableInheritanceRoot(TransactionCase):
    """`resource.asset` is a table-inheritance root, so PostgreSQL enforces no
    foreign key into it and `mixin.table.inheritance.root` enforces every
    relation's `ondelete` instead. These are the tests that the replacement is
    real: each one deletes an asset and checks what the declaration promised."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Asset = cls.env["resource.asset"]
        cls.vehicle = cls.env.ref("resource_asset.kind_vehicle")
        cls.plate = cls.env.ref("resource_asset.identifier_type_plate")

    def _asset(self, name="Scrap me"):
        return self.Asset.create({"name": name, "kind_id": self.vehicle.id})

    def test_the_asset_table_is_the_root_of_its_own_tree(self):
        self.assertTrue(self.Asset._is_table_inheritance_root())
        self.assertEqual(self.Asset._get_root_model_name(), "resource.asset")
        self.assertIn("resource.asset", self.Asset._get_model_names_in_tree())

    def test_no_foreign_key_points_at_the_root_table(self):
        """The database cannot check one against an inherited row, so any left
        would refuse a legitimate reference as soon as a subtype exists."""
        self.env.cr.execute(
            """
            SELECT c.conrelid::regclass::text, c.conname
              FROM pg_constraint c JOIN pg_class t ON t.oid = c.confrelid
             WHERE c.contype = 'f' AND t.relname = 'resource_asset'
            """
        )
        self.assertEqual(self.env.cr.fetchall(), [])

    def test_what_the_root_grants_the_subtype_grants(self):
        # account_depreciation grants accountants the root; creating a property
        # through the root dispatches to the subtype and must not refuse them.
        group = self.env.ref("base.group_user")
        user = self.env["res.users"].create(
            {"name": "Root Only", "login": "root_only", "group_ids": [(4, group.id)]}
        )
        self.env["ir.model.access"].create(
            {
                "name": "root only",
                "model_id": self.env["ir.model"]._get_id("resource.asset"),
                "group_id": group.id,
                "perm_read": True,
                "perm_write": True,
                "perm_create": True,
            }
        )
        kind = self.env.ref("resource_asset.kind_property")
        plot = self.Asset.with_user(user).create({"name": "Plot", "kind_id": kind.id})
        self.assertEqual(plot._get_concrete()._name, "resource.asset.property")

    def test_the_shipped_kinds_with_a_model_land_in_it(self):
        for code in ("property", "telecom", "device"):
            with self.subTest(kind=code):
                kind = self.env.ref(f"resource_asset.kind_{code}")
                asset = self.Asset.create({"name": f"A {code}", "kind_id": kind.id})
                self.assertEqual(asset._get_concrete()._name, f"resource.asset.{code}")

    def test_a_subtype_column_is_an_identifier_row(self):
        kind = self.env.ref("resource_asset.kind_property")
        parcel = self.Asset.create({"name": "Parcel", "kind_id": kind.id})
        concrete = parcel._get_concrete()
        concrete.cadastral_id = "CAD-1"
        self.assertEqual(parcel.get_identifier("cadastral"), "CAD-1")
        self.assertEqual(
            self.env["resource.asset.property"].search(
                [("cadastral_id", "=", "CAD-1")]
            ),
            concrete,
        )
        self.assertNotIn("cadastral_id", self.Asset._fields)
        concrete.cadastral_id = False
        self.assertFalse(parcel.identifier_ids)

    def test_no_shared_relation_table_points_at_a_subtype_table(self):
        # The vehicle's copy of an inherited many2many keeps the root's
        # relation table, so a key against `resource_asset_vehicle` would
        # refuse every link of an asset that is not a vehicle.
        self.env.cr.execute(
            """
            SELECT c.conrelid::regclass::text, c.conname
              FROM pg_constraint c JOIN pg_class t ON t.oid = c.confrelid
             WHERE c.contype = 'f' AND t.relname = 'resource_asset_vehicle'
            """
        )
        offenders = [
            (table, name)
            for table, name in self.env.cr.fetchall()
            if any(
                field.relation == table
                for field in self.Asset._fields.values()
                if field.type == "many2many" and field.store
            )
        ]
        self.assertEqual(offenders, [])

    def test_the_scan_finds_the_relations_the_database_no_longer_holds(self):
        found = {
            (model, field): ondelete
            for model, field, ondelete in self.Asset._get_fields_ondelete_unenforced()
        }

        self.assertEqual(
            found.get(("resource.asset.identifier", "asset_id")), "cascade"
        )
        self.assertEqual(found.get(("resource.asset.meter", "asset_id")), "cascade")
        for (model, field), ondelete in found.items():
            with self.subTest(model=model, field=field):
                self.assertIn(ondelete, ("cascade", "restrict", "set null"))

    def test_a_cascading_relation_is_deleted_with_the_asset(self):
        asset = self._asset()
        asset.identifier_ids = [(0, 0, {"type_id": self.plate.id, "value": "GONE-1"})]
        identifier = asset.identifier_ids
        meter = self.env["resource.asset.meter"].create(
            {"asset_id": asset.id, "name": "Odometer", "kind": "odometer"}
        )
        reading = meter.record(100)

        asset.unlink()

        self.assertFalse(identifier.exists())
        self.assertFalse(meter.exists())
        self.assertFalse(reading.exists())

    def test_a_restricting_relation_refuses_the_delete(self):
        """`parent_id` declares restrict, and it is the one relation into the
        tree that needs nothing outside this module to exercise."""
        whole = self._asset("Whole")
        self.Asset.create(
            {"name": "Component", "kind_id": self.vehicle.id, "parent_id": whole.id}
        )

        with self.assertRaises(ValidationError):
            whole.unlink()

        self.assertTrue(whole.exists())

    def test_every_restricting_relation_is_one_the_scan_found(self):
        """A restrict the scan misses is a delete the database used to refuse
        and now silently allows, leaving a dangling reference."""
        restricting = {
            (model, field)
            for model, field, ondelete in self.Asset._get_fields_ondelete_unenforced()
            if ondelete == "restrict"
        }

        self.assertIn(("resource.asset", "parent_id"), restricting)

    def test_deleting_the_asset_deletes_its_resource_and_nothing_else(self):
        keeper = self._asset("Keeper")
        keeper.identifier_ids = [(0, 0, {"type_id": self.plate.id, "value": "KEEP-1"})]
        doomed = self._asset("Doomed")

        doomed.unlink()

        self.assertTrue(keeper.exists())
        self.assertTrue(keeper.identifier_ids.exists())
