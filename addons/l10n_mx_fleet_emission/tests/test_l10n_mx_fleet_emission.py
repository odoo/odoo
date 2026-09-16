from datetime import date

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nMxFleetEmission(TransactionCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.kind_vehicle = cls.env.ref("resource_asset.kind_vehicle")
        cls.kind_tool = cls.env.ref("resource_asset.kind_tool")
        cls.model = cls.env["product.product"].create(
            {
                "name": "Emissions Test Model",
                "type": "consu",
                "asset_kind_id": cls.kind_vehicle.id,
            }
        )
        cls.press = cls.env["product.product"].create(
            {
                "name": "Emissions Test Press",
                "type": "consu",
                "asset_kind_id": cls.kind_tool.id,
            }
        )
        cls.Inspection = cls.env["l10n_mx.fleet.emission.inspection"]

    def _vehicle(self, plate, product=None):
        product = product or self.model
        return self.env["resource.asset"].create(
            {
                "name": plate,
                "kind_id": product.asset_kind_id.id,
                "product_id": product.id,
                "license_plate": plate,
            }
        )

    def test_color_from_last_digit(self) -> None:
        expected = {
            "ABC-125": "yellow",
            "ABC-126": "yellow",
            "MXK7897": "pink",
            "NEV 3213": "red",
            "1234": "red",
            "LMN-002": "green",
            "XYZ 999": "blue",
            "ABC 120": "blue",
        }
        for plate, color in expected.items():
            vehicle = self._vehicle(plate)
            self.assertEqual(vehicle.l10n_mx_emission_plate_digit, plate[-1])
            self.assertEqual(vehicle.l10n_mx_emission_color, color, plate)

    def test_no_digit_no_calendar(self) -> None:
        vehicle = self._vehicle("SINNUMERO")
        self.assertFalse(vehicle.l10n_mx_emission_plate_digit)
        self.assertFalse(vehicle.l10n_mx_emission_calendar_id)
        self.assertFalse(vehicle.l10n_mx_emission_status)

    def test_period_display(self) -> None:
        vehicle = self._vehicle("ABC-125")
        self.assertEqual(vehicle.l10n_mx_emission_period, "Jan-Feb / Jul-Aug")

    def test_status(self) -> None:
        yellow = self._vehicle("ABC-125")
        blue = self._vehicle("ABC-129")
        red = self._vehicle("ABC-123")
        today = date(2026, 9, 10)
        self.assertEqual(yellow._get_l10n_mx_emission_status(today), "overdue")
        self.assertEqual(blue._get_l10n_mx_emission_status(today), "upcoming")
        self.assertEqual(red._get_l10n_mx_emission_status(today), "due")
        self.assertEqual(red._get_l10n_mx_emission_deadline(today), date(2026, 10, 31))
        self.assertEqual(blue._get_l10n_mx_emission_deadline(today), date(2026, 12, 31))
        self.assertEqual(
            yellow._get_l10n_mx_emission_deadline(date(2026, 1, 5)), date(2026, 2, 28)
        )

        self.Inspection._generate_inspections(2026, yellow)
        inspection = yellow.l10n_mx_emission_inspection_ids.filtered(
            lambda i: i.year == 2026 and i.period == "2"
        )
        inspection.date_scheduled = date(2026, 8, 3)
        self.assertEqual(inspection.state, "scheduled")
        self.assertEqual(yellow._get_l10n_mx_emission_status(today), "scheduled")
        inspection.is_done = True
        self.assertEqual(inspection.state, "done")
        self.assertTrue(inspection.date_done)
        self.assertEqual(yellow._get_l10n_mx_emission_status(today), "passed")
        self.assertEqual(yellow.l10n_mx_emission_last_date, inspection.date_done)
        inspection.is_done = False
        self.assertEqual(inspection.state, "scheduled")
        self.assertEqual(yellow._get_l10n_mx_emission_status(today), "scheduled")
        inspection.date_scheduled = False
        self.assertEqual(inspection.state, "pending")
        self.assertEqual(yellow._get_l10n_mx_emission_status(today), "overdue")

    def test_status_search(self) -> None:
        red = self._vehicle("ABC-123")
        found = self.env["resource.asset"].search(
            [("l10n_mx_emission_status", "in", ["due", "overdue", "upcoming"])]
        )
        self.assertIn(red, found)

    def test_plate_change_recomputes(self) -> None:
        vehicle = self._vehicle("ABC-125")
        self.assertEqual(vehicle.l10n_mx_emission_color, "yellow")
        vehicle.license_plate = "ABC-127"
        self.assertEqual(vehicle.l10n_mx_emission_color, "pink")

    def test_calendar_change_recomputes_vehicles(self) -> None:
        vehicle = self._vehicle("ABC-125")
        yellow = self.env.ref("l10n_mx_fleet_emission.emission_calendar_yellow")
        pink = self.env.ref("l10n_mx_fleet_emission.emission_calendar_pink")
        yellow.plate_digits = "6"
        pink.plate_digits = "5,7,8"
        self.assertEqual(vehicle.l10n_mx_emission_color, "pink")

    def test_checklist_generated(self) -> None:
        vehicle = self._vehicle("ABC-125")
        year = date.today().year
        inspections = vehicle.l10n_mx_emission_inspection_ids.filtered(
            lambda i: i.year == year
        )
        self.assertEqual(sorted(inspections.mapped("period")), ["1", "2"])
        first = inspections.filtered(lambda i: i.period == "1")
        self.assertEqual(first.window_display, "Jan-Feb")
        self.assertEqual(first.deadline, date(year, 2, 28 + (year % 4 == 0)))
        self.assertEqual(first.window_start, date(year, 1, 1))
        self.Inspection._generate_inspections(year)
        self.assertEqual(
            len(
                vehicle.l10n_mx_emission_inspection_ids.filtered(
                    lambda i: i.year == year
                )
            ),
            2,
        )
        self.assertEqual(vehicle.l10n_mx_emission_pending_count, 2)

    def test_no_checklist_without_plate_digit(self) -> None:
        vehicle = self._vehicle("SINNUMERO")
        self.assertFalse(vehicle.l10n_mx_emission_inspection_ids)
        vehicle.license_plate = "ABC-123"
        self.assertEqual(len(vehicle.l10n_mx_emission_inspection_ids), 2)
        self.assertEqual(
            vehicle.l10n_mx_emission_inspection_ids.mapped("sticker_color"),
            ["red", "red"],
        )

    def test_overdue_search(self) -> None:
        vehicle = self._vehicle("ABC-125")
        old = self.Inspection.create(
            {"asset_id": vehicle.id, "year": 2020, "period": "1"}
        )
        self.assertTrue(old.is_overdue)
        self.assertIn(old, self.Inspection.search([("is_overdue", "=", True)]))
        old.is_done = True
        self.assertFalse(old.is_overdue)
        self.assertNotIn(old, self.Inspection.search([("is_overdue", "=", True)]))

    def test_only_vehicles_are_inspected(self) -> None:
        press = self._vehicle("PRS-125", product=self.press)
        self.assertFalse(press.is_vehicle)
        self.assertFalse(press.l10n_mx_emission_calendar_id)
        self.assertFalse(press.l10n_mx_emission_inspection_ids)
        self.assertNotIn(
            press,
            self.env["resource.asset"].search(
                [("l10n_mx_emission_status", "in", ["due", "overdue", "upcoming"])]
            ),
        )

    def test_a_calendar_arriving_after_the_vehicle_stores_its_color(self) -> None:
        Calendar = self.env["l10n_mx.fleet.emission.calendar"]
        Calendar.search([]).unlink()
        vehicle = self._vehicle("ABC-125")
        self.assertFalse(vehicle.l10n_mx_emission_calendar_id)
        Calendar.create(
            {
                "name": "Yellow again",
                "color": "yellow",
                "plate_digits": "5,6",
                "first_period_start": 1,
                "first_period_end": 2,
                "second_period_start": 7,
                "second_period_end": 8,
            }
        )
        vehicle.invalidate_recordset()
        self.env.cr.execute(
            "SELECT l10n_mx_emission_color FROM resource_asset WHERE id = %s",
            [vehicle.id],
        )
        self.assertEqual(self.env.cr.fetchone()[0], "yellow")
        self.assertEqual(vehicle.l10n_mx_emission_color, "yellow")

    def test_the_inspection_follows_the_vehicle_driver(self) -> None:
        vehicle = self._vehicle("ABC-125")
        inspection = vehicle.l10n_mx_emission_inspection_ids[:1]
        self.assertFalse(inspection.driver_id)
        driver = (
            self.env["res.partner"]
            .create({"name": "Emissions Driver"})
            ._get_or_create_resources(self.env.company)
        )
        vehicle.driver_id = driver
        self.assertEqual(inspection.driver_id, driver)
        self.assertIn(
            inspection, self.Inspection.search([("driver_id", "=", driver.id)])
        )

    def test_a_vehicle_registered_without_fleet_rights_gets_its_checklist(self) -> None:
        user = self.env["res.users"].create(
            {
                "name": "Asset Clerk",
                "login": "emission_asset_clerk",
                "group_ids": [
                    (4, self.env.ref("resource_asset.group_asset_manager").id)
                ],
            }
        )
        vehicle = (
            self.env["resource.asset"]
            .with_user(user)
            .create(
                {
                    "name": "ABC-123",
                    "kind_id": self.kind_vehicle.id,
                    "product_id": self.model.id,
                    "license_plate": "ABC-123",
                }
            )
        )
        self.assertEqual(len(vehicle.sudo().l10n_mx_emission_inspection_ids), 2)
