import re
from ast import literal_eval
from datetime import UTC, datetime, timedelta

from lxml import etree

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import Form, TransactionCase, new_test_user, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestResourceAsset(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Asset = cls.env["resource.asset"]
        cls.vehicle = cls.env.ref("resource_asset.kind_vehicle")
        cls.machinery = cls.env.ref("resource_asset.kind_machinery")
        cls.plate = cls.env.ref("resource_asset.identifier_type_plate")
        cls.vin = cls.env.ref("resource_asset.identifier_type_vin")
        cls.serial = cls.env.ref("resource_asset.identifier_type_serial")
        cls.company_b = cls.env["res.company"].create({"name": "Second"})
        cls.driver = cls.env["resource.resource"].create(
            {"name": "Driver", "resource_type": "user", "tz": "UTC"}
        )

    def _truck(self, name="Truck", **vals):
        return self.Asset.create({"name": name, "kind_id": self.vehicle.id, **vals})

    def test_an_asset_is_a_material_resource(self):
        truck = self._truck()
        self.assertEqual(truck.resource_id.resource_type, "material")
        self.assertEqual(truck.resource_id.name, "Truck")
        self.assertEqual(truck.resource_id.asset_id, truck)
        truck.name = "Truck 7"
        self.assertEqual(truck.resource_id.name, "Truck 7")

    def test_the_asset_list_shows_whole_assets_and_hides_components(self):
        truck = self._truck()
        crane = self._truck("Crane on truck", parent_id=truck.id)
        action = self.env.ref("resource_asset.action_resource_asset")
        self.assertEqual(action.context, "{'search_default_top_level': 1}")
        search = self.env.ref("resource_asset.resource_asset_view_search")
        arch = etree.fromstring(search.arch)
        domain = arch.xpath("//filter[@name='top_level']")[0].get("domain")
        listed = self.Asset.search(literal_eval(domain))
        self.assertIn(truck, listed)
        self.assertNotIn(crane, listed)

    def test_an_asset_created_through_a_form_is_active(self):
        form = Form(self.Asset)
        form.name = "Form truck"
        form.kind_id = self.vehicle
        truck = form.save()
        self.assertTrue(truck.active)
        self.assertTrue(truck.resource_id.active)

    def test_an_unscheduled_kind_is_available_around_the_clock(self):
        truck = self._truck(company_id=self.env.company.id)
        self.assertFalse(truck.resource_calendar_id)
        self.assertTrue(truck.resource_id._is_fully_flexible())

    def test_a_scheduled_kind_takes_the_company_calendar(self):
        press = self.Asset.create({"name": "Press", "kind_id": self.machinery.id})
        self.assertEqual(
            press.resource_calendar_id, self.env.company.resource_calendar_id
        )

    def test_a_shared_asset_of_a_scheduled_kind_takes_no_company_calendar(self):
        press = self.Asset.create(
            {"name": "Shared press", "kind_id": self.machinery.id, "company_id": False}
        )
        self.assertFalse(press.company_id)
        self.assertFalse(press.resource_calendar_id)
        self.assertFalse(press.resource_id.calendar_id)

    def test_an_explicit_calendar_wins(self):
        calendar = self.env["resource.calendar"].create({"name": "Nights", "tz": "UTC"})
        truck = self._truck(resource_calendar_id=calendar.id)
        self.assertEqual(truck.resource_calendar_id, calendar)

    def test_missing_identifiers_follow_the_kind(self):
        truck = self._truck()
        self.assertEqual(truck.missing_identifier_type_ids, self.plate | self.vin)
        truck.identifier_ids = [(0, 0, {"type_id": self.plate.id, "value": "abc-123"})]
        self.assertEqual(truck.missing_identifier_type_ids, self.vin)
        self.assertEqual(truck.get_identifier("plate"), "abc-123")
        self.assertIn(
            truck,
            self.Asset.search([("missing_identifier_type_ids", "in", self.vin.ids)]),
        )

    def test_furniture_wants_the_company_s_inventory_tag(self):
        desk = self.Asset.create(
            {
                "name": "Reception desk",
                "kind_id": self.env.ref("resource_asset.kind_furniture").id,
            }
        )
        inventory = self.env.ref("resource_asset.identifier_type_inventory")
        self.assertEqual(desk.missing_identifier_type_ids, inventory)
        self.assertEqual(inventory.unique_scope, "company")

    def test_a_kind_that_does_not_enforce_takes_an_incomplete_asset(self):
        """The default everywhere. A unit arrives before its paperwork, and a
        fleet that is already incomplete must stay writable."""
        truck = self._truck()

        self.assertFalse(self.vehicle.enforce_identifiers)
        self.assertEqual(truck.missing_identifier_type_ids, self.plate | self.vin)
        truck.name = "Still editable"

    def test_an_enforcing_kind_refuses_an_asset_missing_an_identifier(self):
        self.vehicle.enforce_identifiers = True

        with self.assertRaises(ValidationError):
            self._truck("Bare truck")

    def test_an_enforcing_kind_takes_an_asset_that_carries_everything(self):
        self.vehicle.enforce_identifiers = True

        truck = self._truck("Complete truck", license_plate="ENF-1", vin_sn="ENFVIN1")

        self.assertFalse(truck.missing_identifier_type_ids)

    def test_clearing_an_identifier_an_enforcing_kind_needs_is_refused(self):
        truck = self._truck("Losing its vin", license_plate="ENF-2", vin_sn="ENFVIN2")
        self.vehicle.enforce_identifiers = True

        with self.assertRaises(ValidationError):
            truck.vin_sn = False

    def test_enforcement_reaches_an_asset_that_changes_kind(self):
        tool = self.Asset.create(
            {
                "name": "Reclassified",
                "kind_id": self.env.ref("resource_asset.kind_tool").id,
            }
        )
        self.vehicle.enforce_identifiers = True

        with self.assertRaises(ValidationError):
            tool.kind_id = self.vehicle

    def test_an_enforcing_kind_is_still_refused_nothing_when_asked_to_skip(self):
        """The seam a receipt uses: the serial is created before the paperwork
        arrives, and `resource_asset_stock` opens it on that one path."""
        self.vehicle.enforce_identifiers = True

        truck = self.Asset.with_context(skip_asset_identity_check=True).create(
            {"name": "Just received", "kind_id": self.vehicle.id}
        )

        self.assertEqual(truck.missing_identifier_type_ids, self.plate | self.vin)

    def test_telecom_equipment_wants_a_serial_and_an_imei(self):
        radio = self.Asset.create(
            {
                "name": "Base radio",
                "kind_id": self.env.ref("resource_asset.kind_telecom").id,
            }
        )
        self.assertEqual(
            radio.missing_identifier_type_ids,
            self.serial | self.env.ref("resource_asset.identifier_type_imei"),
        )

    def test_assets_are_searched_by_what_identifiers_they_miss(self):
        complete = self._truck("Complete")
        complete.identifier_ids = [
            (0, 0, {"type_id": self.plate.id, "value": "P-1"}),
            (0, 0, {"type_id": self.vin.id, "value": "V1"}),
        ]
        no_vin = self._truck("No VIN")
        no_vin.identifier_ids = [(0, 0, {"type_id": self.plate.id, "value": "P-2"})]
        bare = self._truck("Bare")
        trucks = complete | no_vin | bare

        def found(domain):
            return self.Asset.search(domain + [("id", "in", trucks.ids)])

        cases = [
            ([("missing_identifier_type_ids", "=", False)], complete),
            ([("missing_identifier_type_ids", "!=", False)], no_vin | bare),
            ([("missing_identifier_type_ids", "in", self.vin.ids)], no_vin | bare),
            ([("missing_identifier_type_ids", "in", self.plate.ids)], bare),
            (
                [("missing_identifier_type_ids", "not in", self.plate.ids)],
                complete | no_vin,
            ),
            (
                [("missing_identifier_type_ids", "in", [False, self.plate.id])],
                complete | bare,
            ),
            ([("missing_identifier_type_ids.code", "=", "plate")], bare),
        ]
        for domain, expected in cases:
            with self.subTest(domain=domain):
                self.assertEqual(found(domain), expected)
                for asset in trucks:
                    self.assertEqual(
                        bool(asset.filtered_domain(domain)), asset in expected
                    )

    def test_identifier_is_normalized_and_matches_its_pattern(self):
        self.vin.pattern = "[A-HJ-NPR-Z0-9]{17}"
        truck = self._truck()
        identifier = self.env["resource.asset.identifier"].create(
            {
                "asset_id": truck.id,
                "type_id": self.vin.id,
                "value": "1hgcm82633a-004352",
            }
        )
        self.assertEqual(identifier.normalized_value, "1HGCM82633A004352")
        with self.assertRaises(ValidationError):
            identifier.write({"value": "TOO-SHORT"})

    def test_global_uniqueness_crosses_companies(self):
        one = self._truck("One")
        two = self._truck("Two", company_id=self.company_b.id)
        self.env["resource.asset.identifier"].create(
            {"asset_id": one.id, "type_id": self.vin.id, "value": "1HGCM82633A004352"}
        )
        with self.assertRaises(ValidationError):
            self.env["resource.asset.identifier"].create(
                {
                    "asset_id": two.id,
                    "type_id": self.vin.id,
                    "value": "1hgcm82633a004352",
                }
            )

    def test_company_uniqueness_stops_at_the_company(self):
        one = self._truck("One")
        two = self._truck("Two", company_id=self.company_b.id)
        three = self._truck("Three")
        self.env["resource.asset.identifier"].create(
            {"asset_id": one.id, "type_id": self.plate.id, "value": "ABC 123"}
        )
        self.env["resource.asset.identifier"].create(
            {"asset_id": two.id, "type_id": self.plate.id, "value": "ABC-123"}
        )
        with self.assertRaises(ValidationError):
            self.env["resource.asset.identifier"].create(
                {"asset_id": three.id, "type_id": self.plate.id, "value": "abc123"}
            )

    def test_an_identifier_is_found_however_it_is_typed(self):
        truck = self._truck()
        other = self._truck("Other")
        self.env["resource.asset.identifier"].create(
            {"asset_id": truck.id, "type_id": self.plate.id, "value": "ABC 123"}
        )
        for typed in ("ABC 123", "abc-123", "ABC123", "c-12"):
            with self.subTest(typed=typed):
                found = self.Asset.search([("identifier_ids", "ilike", typed)])
                self.assertIn(truck, found)
                self.assertNotIn(other, found)
        self.assertFalse(self.Asset.search([("identifier_ids", "ilike", "XYZ-9")]))
        self.assertNotIn(
            truck, self.Asset.search([("identifier_ids", "not ilike", "abc-123")])
        )

    def test_one_value_per_type_per_asset(self):
        truck = self._truck()
        self.env["resource.asset.identifier"].create(
            {"asset_id": truck.id, "type_id": self.plate.id, "value": "A"}
        )
        with self.assertRaises(Exception), mute_logger("odoo.sql_db", "odoo.db.cursor"):
            with self.env.cr.savepoint():
                self.env["resource.asset.identifier"].create(
                    {"asset_id": truck.id, "type_id": self.plate.id, "value": "B"}
                )

    def test_meter_keeps_the_latest_reading_and_refuses_to_run_backwards(self):
        truck = self._truck()
        meter = self.env["resource.asset.meter"].create(
            {"asset_id": truck.id, "name": "Odometer", "kind": "odometer"}
        )
        t0 = datetime(2026, 1, 1, 8, 0)
        meter.record(1000, date=t0)
        meter.record(1500, date=t0 + timedelta(days=1))
        meter.invalidate_recordset()
        self.assertEqual(meter.value, 1500)
        self.assertEqual(truck.get_meter("odometer"), meter)
        self.assertEqual(meter._value_at(t0 + timedelta(hours=1)), 1000)
        with self.assertRaises(ValidationError):
            meter.record(1200, date=t0 + timedelta(days=2))
        with self.assertRaises(ValidationError):
            meter.record(1600, date=t0 + timedelta(hours=12))
        meter.monotonic = False
        meter.record(900, date=t0 + timedelta(days=3))
        meter.invalidate_recordset()
        self.assertEqual(meter.value, 900)

    def test_identifier_columns_read_and_write_the_identifier_rows(self):
        truck = self._truck(license_plate="ABC-123", vin_sn="1HGCM82633A004352")
        self.assertEqual(truck.get_identifier("plate"), "ABC-123")
        self.assertFalse(truck.missing_identifier_type_ids)
        truck.license_plate = "XYZ-987"
        self.assertEqual(truck.get_identifier("plate"), "XYZ-987")
        truck.vin_sn = False
        self.assertEqual(truck.missing_identifier_type_ids, self.vin)
        self.assertEqual(self.Asset.search([("license_plate", "=", "XYZ-987")]), truck)

    def test_the_odometer_is_the_odometer_meter_latest_reading(self):
        truck = self._truck()
        self.assertFalse(truck.odometer_meter_id)
        self.assertEqual(truck.odometer, 0.0)
        self.env["resource.asset.meter"].create(
            {"asset_id": truck.id, "name": "Hours", "kind": "hours"}
        ).record(40)
        meter = self.env["resource.asset.meter"].create(
            {"asset_id": truck.id, "name": "Odometer", "kind": "odometer"}
        )
        meter.record(1200, date=datetime(2026, 1, 1, 8, 0))
        meter.record(1350, date=datetime(2026, 1, 2, 8, 0))
        self.assertEqual(truck.odometer_meter_id, meter)
        self.assertEqual(truck.odometer, 1350)
        self.assertEqual(
            self.Asset.search([("id", "=", truck.id), ("odometer", ">", 1300)]), truck
        )

    def test_custody_through_the_resource(self):
        truck = self._truck()
        self.assertFalse(truck.holder_id)
        assignment = self.env["resource.assignment"].create(
            {
                "resource_id": truck.resource_id.id,
                "assignee_id": self.driver.id,
                "custody_role": "operator",
                "date_start": datetime.now() - timedelta(days=1),
            }
        )
        truck.invalidate_recordset()
        self.assertEqual(truck.holder_id, self.driver)
        self.assertEqual(truck._get_holder(custody_role="operator"), self.driver)
        self.assertIn(assignment, truck.assignment_ids)
        self.assertIn(truck, self.Asset.search([("holder_id", "=", self.driver.id)]))

    def test_archiving_ends_open_custody(self):
        truck = self._truck()
        assignment = self.env["resource.assignment"].create(
            {
                "resource_id": truck.resource_id.id,
                "assignee_id": self.driver.id,
                "date_start": datetime.now() - timedelta(days=1),
            }
        )
        truck.action_archive()
        self.assertFalse(truck.resource_id.active)
        self.assertTrue(assignment.date_end)
        self.assertEqual(assignment.state, "ended")

    def test_an_asset_user_manages_asset_custody_and_no_one_elses(self):
        asset_user = new_test_user(
            self.env, login="asset_user", groups="resource_asset.group_asset_user"
        )
        truck = self._truck()
        office = self.env["resource.resource"].create(
            {"name": "Office", "resource_type": "user", "tz": "UTC"}
        )
        Assignment = self.env["resource.assignment"].with_user(asset_user)
        custody = Assignment.create(
            {"resource_id": truck.resource_id.id, "assignee_id": self.driver.id}
        )
        custody.note = "keys in the glovebox"
        custody.unlink()

        human = self.env["resource.assignment"].create(
            {"resource_id": office.id, "assignee_id": self.driver.id}
        )
        self.assertEqual(human.with_user(asset_user).assignee_id, self.driver)
        with self.assertRaises(AccessError):
            human.with_user(asset_user).note = "edited"
        with self.assertRaises(AccessError):
            human.with_user(asset_user).unlink()
        with self.assertRaises(AccessError):
            Assignment.create({"resource_id": office.id, "assignee_id": self.driver.id})

        admin = self.env.ref("base.user_admin")
        self.assertTrue(admin.has_group("resource_asset.group_asset_user"))
        human.with_user(admin).note = "edited by an administrator"
        human.with_user(admin).unlink()

    def test_disposal_voids_a_planned_hand_over(self):
        truck = self._truck()
        now = datetime.now()
        current = self.env["resource.assignment"].create(
            {
                "resource_id": truck.resource_id.id,
                "assignee_id": self.driver.id,
                "custody_role": "operator",
                "date_start": now - timedelta(days=1),
            }
        )
        successor = self.env["resource.resource"].create(
            {"name": "Successor", "resource_type": "user", "tz": "UTC"}
        )
        planned = self.env["resource.assignment"].create(
            {
                "resource_id": truck.resource_id.id,
                "assignee_id": successor.id,
                "custody_role": "operator",
                "date_start": now + timedelta(days=3),
            }
        )
        truck.action_dispose()
        self.env.flush_all()
        self.assertEqual(current.state, "ended")
        self.assertEqual(planned.date_end, planned.date_start)
        self.assertFalse(
            truck._get_holder(
                custody_role="operator", at=planned.date_start + timedelta(hours=1)
            )
        )

    def test_disposal(self):
        truck = self._truck(date_acquisition="2020-01-01")
        with self.assertRaises(ValidationError):
            truck.state = "disposed"
        truck.action_dispose()
        self.assertEqual(truck.state, "disposed")
        self.assertTrue(truck.date_disposal)
        self.assertFalse(truck.active)

    def test_every_state_has_a_way_in(self):
        truck = self._truck()
        truck.action_set_in_service()
        self.assertEqual(truck.state, "in_service")
        truck.action_set_maintenance()
        self.assertEqual(truck.state, "maintenance")
        truck.action_set_out_of_service()
        self.assertEqual(truck.state, "out_of_service")
        truck.action_set_in_service()
        self.assertEqual(truck.state, "in_service")

    def test_restoring_a_disposed_asset_reverses_the_disposal(self):
        truck = self._truck()
        truck.action_dispose()
        truck.action_unarchive()
        self.assertTrue(truck.active)
        self.assertEqual(truck.state, "out_of_service")
        self.assertFalse(truck.date_disposal)
        truck.action_dispose()
        truck.write({"active": True, "state": "in_service"})
        self.assertEqual(truck.state, "in_service")

    def test_a_component_cannot_contain_its_whole(self):
        tractor = self._truck("Tractor")
        engine = self.Asset.create(
            {"name": "Engine", "kind_id": self.machinery.id, "parent_id": tractor.id}
        )
        self.assertIn(engine, tractor.child_ids)
        with self.assertRaises(ValidationError):
            tractor.parent_id = engine

    def test_a_resource_is_one_asset_at_most(self):
        truck = self._truck()
        with self.assertRaises(Exception), mute_logger("odoo.sql_db", "odoo.db.cursor"):
            with self.env.cr.savepoint():
                self.Asset.create(
                    {
                        "name": "Twin",
                        "kind_id": self.vehicle.id,
                        "resource_id": truck.resource_id.id,
                    }
                )

    def test_asset_books_like_any_resource(self):
        truck = self._truck()
        reservation = self.env["resource.reservation"].create(
            {
                "name": "Delivery run",
                "resource_id": truck.resource_id.id,
                "date_start": datetime(2026, 3, 2, 8, 0),
                "date_end": datetime(2026, 3, 2, 12, 0),
                "enforcement_mode": "hard",
            }
        )
        self.assertEqual(reservation.resource_id.asset_id, truck)
        unavailable = truck.resource_id._get_unavailable_intervals(
            datetime(2026, 3, 2, tzinfo=UTC),
            datetime(2026, 3, 3, tzinfo=UTC),
        )[truck.resource_id.id]
        self.assertEqual(len(unavailable), 1)

    def test_every_asset_group_by_is_groupable(self):
        views = self.env["ir.ui.view"].search(
            [
                ("model", "=", "resource.asset"),
                ("type", "=", "search"),
                ("mode", "=", "primary"),
            ]
        )
        checked = 0
        for view in views:
            search_view = self.Asset.get_views([(view.id, "search")])["views"]["search"]
            for node in etree.fromstring(search_view["arch"]).iter("filter"):
                for group_by in re.findall(
                    r"""["']group_by["']\s*:\s*["']([^"']+)["']""",
                    node.get("context") or "",
                ):
                    checked += 1
                    with self.subTest(view=view.xml_id, filter=node.get("name")):
                        self.assertTrue(
                            self.Asset._is_field_groupable(group_by.split(":")[0])
                        )
        self.assertGreater(checked, 0)

    def test_an_asset_records_where_it_was_bought_and_for_how_much(self):
        vendor = self.env["res.partner"].create({"name": "Tractor dealer"})
        truck = self._truck(
            partner_id=vendor.id,
            partner_ref="PO-7781",
            value_original=48000.0,
            warranty_date="2028-06-30",
            model="T7.245",
            company_id=self.env.company.id,
        )
        self.assertEqual(truck.currency_id, self.env.company.currency_id)
        self.assertRecordValues(
            truck,
            [
                {
                    "partner_id": vendor.id,
                    "partner_ref": "PO-7781",
                    "value_original": 48000.0,
                    "model": "T7.245",
                }
            ],
        )
        self.assertFalse(truck.copy().value_original)

    def test_a_shared_asset_counts_in_the_current_company_currency(self):
        truck = self._truck(company_id=False)
        self.assertEqual(truck.currency_id, self.env.company.currency_id)

    def test_a_vendor_of_another_company_is_refused(self):
        foreign = self.env["res.partner"].create(
            {"name": "Foreign dealer", "company_id": self.company_b.id}
        )
        with self.assertRaises(UserError):
            self._truck(partner_id=foreign.id, company_id=self.env.company.id)

    def test_each_kind_defines_the_properties_its_assets_carry(self):
        self.vehicle.asset_properties_definition = [
            {"name": "axles", "string": "Axles", "type": "integer"}
        ]
        truck = self._truck()
        truck.asset_properties = {"axles": 3}
        self.assertEqual(truck.asset_properties, {"axles": 3})
        press = self.Asset.create({"name": "Press", "kind_id": self.machinery.id})
        self.assertFalse(press.asset_properties)
