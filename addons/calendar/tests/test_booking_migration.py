"""Stored booking data retains its values and schema ownership across upgrades."""

import runpy
from datetime import datetime
from pathlib import Path

from odoo import Command
from odoo.db.schema import column_exists, create_column
from odoo.tests import TransactionCase, tagged
from odoo.tools import SQL


@tagged("post_install", "-at_install")
class TestBookingAdapterMigration(TransactionCase):
    def test_transferred_timeline_activates_available_adapters(self):
        migrate = runpy.run_path(
            str(Path(__file__).parents[1] / "migrations/2.2/pre-booking-adapters.py")
        )["migrate"]
        module_model = self.env["ir.module.module"]
        modules = {}
        for name in (
            "web_gantt",
            "calendar_gantt",
            "appointment_hr",
            "calendar_gantt_hr",
        ):
            modules[name] = module_model.search(
                [("name", "=", name)]
            ) or module_model.create({"name": name})
        data_model = self.env["ir.model.data"]
        data_model.search(
            [("module", "=", "calendar_gantt"), ("model", "=", "ir.ui.view")]
        ).unlink()
        scenarios = (
            # transferred, web Gantt, HR, adapter state, expected Gantt, expected HR
            (True, "installed", "installed", "uninstalled", "to install", "to install"),
            (
                True,
                "to upgrade",
                "to upgrade",
                "uninstalled",
                "to install",
                "to install",
            ),
            (
                True,
                "installed",
                "uninstalled",
                "uninstalled",
                "to install",
                "uninstalled",
            ),
            (
                False,
                "installed",
                "installed",
                "uninstalled",
                "uninstalled",
                "uninstalled",
            ),
            (
                True,
                "uninstalled",
                "installed",
                "uninstalled",
                "uninstalled",
                "uninstalled",
            ),
            (True, "installed", "installed", "installed", "installed", "to install"),
            (True, "installed", "installed", "to remove", "to remove", "uninstalled"),
        )
        for transferred, gantt, hr, adapter, expected, expected_hr in scenarios:
            with (
                self.subTest(
                    transferred=transferred, gantt=gantt, hr=hr, adapter=adapter
                ),
                self.cr.savepoint(),
            ):
                modules["web_gantt"].state = gantt
                modules["appointment_hr"].state = hr
                modules["calendar_gantt"].state = adapter
                modules["calendar_gantt_hr"].state = "uninstalled"
                data = data_model.browse()
                if transferred:
                    data = data_model.create(
                        {
                            "module": "calendar_gantt",
                            "name": "migration_timeline",
                            "model": "ir.ui.view",
                            "res_id": self.env.ref(
                                "calendar.calendar_event_view_form"
                            ).id,
                        }
                    )
                self.env.flush_all()
                migrate(self.cr, "19.0.2.1")
                migrate(self.cr, "19.0.2.1")
                module_model.invalidate_model(["state"])
                self.assertEqual(modules["calendar_gantt"].state, expected)
                self.assertEqual(modules["calendar_gantt_hr"].state, expected_hr)
                data.unlink()


@tagged("post_install", "-at_install")
class TestBookingMenuMigration(TransactionCase):
    def test_duplicate_menu_is_retired_but_customizations_are_preserved(self):
        migrate = runpy.run_path(
            str(Path(__file__).parents[1] / "migrations/2.1/pre-booking-menu.py")
        )["migrate"]
        data_model = self.env["ir.model.data"]
        data_model.search(
            [
                ("module", "=", "calendar"),
                ("name", "=", "appointment_menu_calendar"),
            ]
        ).unlink()
        for customization in (
            None,
            "child",
            "name",
            "groups",
            "parent",
            "action",
            "protected",
            "sequence",
            "translation",
            "icon",
            "uploaded_icon",
            "keywords",
            "legacy_schema",
        ):
            with self.subTest(customization=customization), self.cr.savepoint():
                menu = self.env["ir.ui.menu"].create(
                    {
                        "name": "Appointments",
                        "parent_id": self.env.ref("calendar.mail_menu_calendar").id,
                        "action": "ir.actions.act_window,%s"
                        % self.env.ref("calendar.appointment_type_action").id,
                    }
                )
                if customization == "child":
                    self.env["ir.ui.menu"].create(
                        {"name": "Custom booking workflow", "parent_id": menu.id}
                    )
                elif customization == "name":
                    menu.name = "My bookings"
                elif customization == "groups":
                    menu.group_ids = self.env.ref("base.group_system")
                elif customization == "parent":
                    menu.parent_id = False
                elif customization == "action":
                    menu.action = (
                        "ir.actions.act_window,%s"
                        % self.env.ref("calendar.action_calendar_event").id
                    )
                elif customization == "sequence":
                    menu.sequence = 73
                elif customization == "translation":
                    self.env["res.lang"]._activate_lang("fr_FR")
                    menu.with_context(lang="fr_FR").name = "Mon planning"
                elif customization == "icon":
                    menu.web_icon = "fa-calendar,#ffffff,#000000"
                elif customization == "uploaded_icon":
                    menu.web_icon_data = b"aWNvbg=="
                elif customization == "keywords":
                    menu.web_keywords = "reservations, bookings"
                data = data_model.create(
                    {
                        "module": "calendar",
                        "name": "appointment_menu_calendar",
                        "model": "ir.ui.menu",
                        "res_id": menu.id,
                        "noupdate": customization == "protected",
                    }
                )
                self.env.flush_all()
                if customization == "legacy_schema":
                    self.cr.execute(
                        "ALTER TABLE ir_ui_menu RENAME COLUMN web_keywords TO upgrade_test_keywords"
                    )
                migrate(self.cr, "19.0.2.0")
                migrate(self.cr, "19.0.2.0")
                if customization == "legacy_schema":
                    self.cr.execute(
                        "ALTER TABLE ir_ui_menu RENAME COLUMN upgrade_test_keywords TO web_keywords"
                    )
                menu.invalidate_recordset()
                data.invalidate_recordset()
                self.assertEqual(
                    menu.active, customization not in (None, "legacy_schema")
                )
                self.assertTrue(data.noupdate)
                self.assertEqual(data.res_id, menu.id)
                self.assertTrue(menu.exists())
                data.unlink()


@tagged("post_install", "-at_install")
class TestBookingRelationOwnership(TransactionCase):
    def test_stale_relation_metadata_cleanup_preserves_booking_payload(self):
        resource = self.env["resource.resource"].create(
            {
                "resource_type": "material",
                "name": "Upgrade payload resource",
                "capacity": 4,
            }
        )
        offer = self.env["appointment.type"].create(
            {
                "name": "Upgrade payload offer",
                "schedule_based_on": "resources",
                "resource_ids": [Command.set(resource.ids)],
            }
        )
        event = self.env["calendar.event"].create(
            {
                "name": "Upgrade payload booking",
                "appointment_type_id": offer.id,
                "start": datetime(2050, 1, 3, 10),
                "stop": datetime(2050, 1, 3, 11),
                "booking_line_ids": [
                    Command.create(
                        {
                            "resource_id": resource.id,
                            "capacity_reserved": 2,
                        }
                    )
                ],
            }
        )
        line = event.booking_line_ids
        relations = self.env["ir.model.relation"]
        legacy = relations.create(
            {
                "name": line._table,
                "model": self.env["ir.model"]._get_id("calendar.event"),
                "module": self.env.ref("base.module_calendar").id,
            }
        )
        relations._reflect_relations([], model_tables={line._table})
        self.assertFalse(legacy.exists())
        line.invalidate_recordset()
        self.assertEqual(line.capacity_reserved, 2)
        self.assertEqual(line.resource_id, resource)
        self.assertEqual(line.calendar_event_id, event)


@tagged("post_install", "-at_install")
class TestBookingCapacityMigration(TransactionCase):
    def test_legacy_capacity_does_not_overwrite_current_capacity(self):
        migrate = runpy.run_path(
            str(Path(__file__).parents[1] / "migrations/2.0/pre-05-capacity.py")
        )["migrate"]
        module = self.env["ir.module.module"].search([("name", "=", "appointment")])
        if not module:
            module = self.env["ir.module.module"].create({"name": "appointment"})
        module.write({"db_version": "19.0.1.3", "state": "installed"})
        resource = self.env["resource.resource"].create(
            {"resource_type": "material", "name": "Historical capacity", "capacity": 3}
        )
        self.env.flush_all()
        # The retired table outlives the merge on an upgraded database, so build
        # it only where this is a fresh one.
        self.cr.execute("""
            CREATE TABLE IF NOT EXISTS appointment_resource (
                id serial PRIMARY KEY,
                resource_id integer,
                capacity integer
            )
        """)
        if not column_exists(self.cr, "appointment_resource", "capacity"):
            create_column(self.cr, "appointment_resource", "capacity", "integer")
        # An upgraded database keeps the legacy table with its own NOT NULL
        # columns; fill whichever of them are still there.
        legacy = {"resource_id": resource.id, "capacity": 7}
        legacy.update(
            (column, value)
            for column, value in (("name", "Historical capacity"), ("sequence", 1))
            if column_exists(self.cr, "appointment_resource", column)
        )
        self.cr.execute(
            SQL(
                "INSERT INTO appointment_resource (%s) VALUES (%s)",
                SQL(", ").join(SQL.identifier(column) for column in legacy),
                SQL(", ").join(SQL("%s", value) for value in legacy.values()),
            )
        )
        self.addCleanup(
            self.cr.execute,
            SQL(
                "DELETE FROM appointment_resource WHERE resource_id = %s",
                resource.id,
            ),
        )
        for installed, expected in (("19.0.1.3", 7), ("19.0.1.4", 3), ("19.0.1.6", 3)):
            with self.subTest(installed=installed):
                module.db_version = installed
                resource.capacity = 3
                self.env.flush_all()
                migrate(self.cr, "19.0.1.1")
                resource.invalidate_recordset(["capacity"])
                self.assertEqual(resource.capacity, expected)
