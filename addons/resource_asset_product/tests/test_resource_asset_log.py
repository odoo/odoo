from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestResourceAssetLog(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Log = cls.env["resource.asset.log"]
        cls.kind = cls.env.ref("resource_asset.kind_tool")
        cls.company_b = cls.env["res.company"].create({"name": "Ledger B"})
        cls.service_category = cls.env["product.category"].create(
            {"name": "Workshop", "log_type": "service"}
        )
        cls.service = cls.env["product.product"].create(
            {"name": "Oil change", "categ_id": cls.service_category.id}
        )

    def _asset(self, **vals):
        return self.env["resource.asset"].create(
            {"name": "Compressor", "kind_id": self.kind.id, **vals}
        )

    def test_the_log_type_comes_from_the_product_category(self):
        log = self.Log.create(
            {"asset_id": self._asset().id, "product_id": self.service.id}
        )

        self.assertEqual(log.log_type, "service")
        self.assertIn(log, log.asset_id.log_ids)

    def test_a_log_belongs_to_its_assets_company(self):
        asset = self._asset(company_id=self.company_b.id)

        log = self.Log.create({"asset_id": asset.id})

        self.assertEqual(log.company_id, self.company_b)

    def test_a_log_is_not_born_cancelled(self):
        with self.assertRaises(UserError):
            self.Log.create({"asset_id": self._asset().id, "state": "cancelled"})

    def test_a_cancelled_log_returns_to_new_before_anything_else(self):
        log = self.Log.create({"asset_id": self._asset().id})
        log.action_set_cancelled()

        with self.assertRaises(UserError):
            log.action_set_done()

        log.action_set_new()
        log.action_set_done()
        self.assertEqual(log.state, "done")

    def test_an_assets_ledger_stays_in_one_company(self):
        asset = self._asset(company_id=False)
        self.Log.create({"asset_id": asset.id, "company_id": self.env.company.id})

        with (
            self.assertRaises(ValidationError),
            self.assertLogs(
                "odoo.addons.resource_asset_product.models.resource_asset_log",
                level="WARNING",
            ),
        ):
            self.Log.create({"asset_id": asset.id, "company_id": self.company_b.id})


@tagged("post_install", "-at_install")
class TestResourceAssetLogOdometer(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Log = cls.env["resource.asset.log"]
        cls.km = cls.env.ref("uom.product_uom_km")
        cls.mile = cls.env.ref("uom.product_uom_mile")
        cls.asset = cls.env["resource.asset"].create(
            {
                "name": "Loader",
                "kind_id": cls.env.ref("resource_asset.kind_machinery").id,
                "odometer_uom_id": cls.km.id,
            }
        )

    def _reading(self, odometer, date):
        return self.Log.create(
            {"asset_id": self.asset.id, "odometer": odometer, "date": date}
        )

    def test_a_ledger_reading_reaches_the_meter(self):
        self._reading(1200, "2026-01-01")

        self.assertEqual(self.asset.odometer_meter_id.kind, "odometer")
        self.assertEqual(self.asset.odometer, 1200)
        self.assertEqual(self.asset.odometer_meter_id.uom_id, self.km)

    def test_the_newest_reading_is_the_one_the_meter_carries(self):
        self._reading(1200, "2026-01-01")
        self._reading(1800, "2026-02-01")

        self.assertEqual(self.asset.odometer, 1800)

    def test_a_reading_below_an_earlier_one_is_refused(self):
        self._reading(1200, "2026-01-01")

        with self.assertRaises(ValidationError):
            self._reading(900, "2026-02-01")

    def test_a_reading_above_a_later_one_is_refused(self):
        self._reading(1800, "2026-02-01")

        with self.assertRaises(ValidationError):
            self._reading(2500, "2026-01-01")

    def test_a_negative_reading_is_refused(self):
        with self.assertRaises(ValidationError):
            self._reading(-1, "2026-01-01")

    def test_deleting_the_newest_reading_walks_the_meter_back(self):
        self._reading(1200, "2026-01-01")
        newest = self._reading(1800, "2026-02-01")

        newest.unlink()

        self.assertEqual(self.asset.odometer, 1200)

    def test_writing_the_odometer_records_a_reading(self):
        self.asset.odometer = 500

        self.assertEqual(self.asset.odometer_meter_id.value, 500)
        with self.assertRaises(ValidationError):
            self.asset.odometer = 400

    def test_the_unit_may_still_be_set_before_any_reading(self):
        self.asset.odometer_uom_id = self.mile

        self.assertEqual(self.asset.odometer_uom_id, self.mile)

    def test_switching_the_unit_would_restate_history_and_is_refused(self):
        self._reading(1200, "2026-01-01")

        with self.assertRaises(ValidationError):
            self.asset.odometer_uom_id = self.mile

    def test_rewriting_the_same_unit_is_not_a_change(self):
        self._reading(1200, "2026-01-01")

        self.asset.odometer_uom_id = self.km

        self.assertEqual(self.asset.odometer_uom_id, self.km)


@tagged("post_install", "-at_install")
class TestResourceAssetLedgerSurface(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Log = cls.env["resource.asset.log"]
        cls.asset = cls.env["resource.asset"].create(
            {"name": "Press", "kind_id": cls.env.ref("resource_asset.kind_tool").id}
        )
        cls.service = cls.env["product.product"].create(
            {
                "name": "Belt change",
                "categ_id": cls.env["product.category"]
                .create({"name": "Repairs", "log_type": "service"})
                .id,
            }
        )

    def test_an_asset_counts_every_log_booked_against_it(self):
        self.assertEqual(self.asset.log_count, 0)

        self.Log.create(
            [
                {"asset_id": self.asset.id, "product_id": self.service.id},
                {"asset_id": self.asset.id},
            ]
        )
        self.asset.invalidate_recordset(["log_count"])

        self.assertEqual(self.asset.log_count, 2)
        self.assertEqual(
            self.asset._get_log_counts_by_type()[self.asset.id]["service"], 1
        )

    def test_an_archived_log_leaves_the_count_it_was_in(self):
        log = self.Log.create({"asset_id": self.asset.id})
        self.asset.invalidate_recordset(["log_count"])
        self.assertEqual(self.asset.log_count, 1)

        log.active = False
        self.asset.invalidate_recordset(["log_count"])

        self.assertEqual(self.asset.log_count, 0)

    def test_the_ledger_button_opens_this_assets_rows(self):
        action = self.asset.action_view_logs()

        self.assertEqual(action["res_model"], "resource.asset.log")
        self.assertEqual(action["domain"], [("asset_id", "=", self.asset.id)])
        self.assertEqual(action["context"]["default_asset_id"], self.asset.id)

    def test_a_window_onto_a_slice_keeps_the_assets_own_filter(self):
        action = self.asset._action_view_logs([("log_type", "=", "service")])

        self.assertEqual(
            action["domain"],
            [("asset_id", "=", self.asset.id), ("log_type", "=", "service")],
        )
