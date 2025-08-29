# Copyright (C) 2019 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestFSMOrder(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Order = cls.env["fsm.order"]
        cls.test_location = cls.env.ref("fieldservice.test_location")
        cls.stage1 = cls.env.ref("fieldservice.fsm_stage_completed")
        cls.stage2 = cls.env.ref("fieldservice.fsm_stage_cancelled")
        cls.init_values = {
            "stage_id": cls.env.ref("fieldservice.fsm_stage_completed").id
        }
        cls.init_values_2 = {
            "stage_id": cls.env.ref("fieldservice.fsm_stage_cancelled").id
        }
        today = fields.Datetime.today()
        start_date = today + timedelta(days=1)
        date_end = start_date.replace(hour=23, minute=59, second=59)
        cls.location_1 = cls.env.ref("fieldservice.location_1")
        cls.p_leave = cls.env["resource.calendar.leaves"].create(
            {
                "date_from": start_date,
                "date_to": date_end,
            }
        )
        cls.tag = cls.env["fsm.tag"].create({"name": "Test Tag"})
        cls.tag1 = cls.env["fsm.tag"].create(
            {"name": "Test Tag1", "parent_id": cls.tag.id}
        )

    def test_fsm_order_default_stage(self):
        view_id = "fieldservice.fsm_order_form"
        stage_ids = self.env["fsm.stage"].search(
            [
                ("stage_type", "=", "order"),
                ("is_default", "=", True),
                ("company_id", "in", (self.env.user.company_id.id, False)),
            ],
            order="sequence asc",
        )
        for stage in stage_ids:
            stage.unlink()
        with self.assertRaises(ValidationError):
            Form(self.Order, view=view_id)

    def test_fsm_order_default_team(self):
        view_id = "fieldservice.fsm_order_form"
        with self.assertRaises(ValidationError):
            team_ids = self.env["fsm.team"].search(
                [("company_id", "in", (self.env.user.company_id.id, False))],
                order="sequence asc",
            )
            for team in team_ids:
                team.unlink()
            Form(self.Order, view=view_id)

    def test_fsm_order_create(self):
        priority_vs_late_days = {"0": 3, "1": 2, "2": 1, "3": 1 / 3}
        vals = {
            "location_id": self.test_location.id,
            "stage_id": self.stage1.id,
        }
        for priority, _late_days in priority_vs_late_days.items():
            vals.update({"priority": priority})
            self.env["fsm.order"].create(vals)
            vals2 = {
                "request_early": fields.Datetime.today(),
                "location_id": self.test_location.id,
                "priority": priority,
                "scheduled_date_start": fields.Datetime.today().replace(
                    hour=0, minute=0, second=0
                ),
            }
            order_vals = {
                "request_early": fields.Datetime.today(),
                "location_id": self.test_location.id,
                "priority": priority,
                "scheduled_date_start": fields.Datetime.today().replace(
                    hour=0, minute=0, second=0
                ),
            }
            self.env["fsm.order"].create(order_vals)
            order = self.env["fsm.order"].create(vals2)
            order.write(
                {
                    "scheduled_date_start": order.request_early.replace(
                        hour=0, minute=0, second=0
                    ),
                    "scheduled_date_end": order.scheduled_date_start
                    + timedelta(hours=10),
                }
            )
            with self.assertRaises(ValidationError):
                order.write(
                    {
                        "scheduled_date_start": order.request_early.replace(
                            hour=0, minute=0, second=0
                        ),
                        "scheduled_date_end": order.scheduled_date_start
                        + timedelta(hours=100),
                    }
                )
            # report
            res = self.env["ir.actions.report"]._render_qweb_text(
                "fieldservice.report_fsm_order", order.ids
            )
            self.assertRegex(str(res[0]), order.name)

    def test_fsm_order(self):
        """Test creating new workorders, and test following functions,
        - _compute_duration() in hrs
        - _compute_request_late()
        - Set scheduled_date_start using request_early w/o time
        - scheduled_date_end = scheduled_date_start + duration (hrs)
        """
        # Create an Orders
        view_id = "fieldservice.fsm_order_form"
        hours_diff = 100
        with Form(self.Order, view=view_id) as f:
            f.location_id = self.test_location
            f.date_start = fields.Datetime.today()
            f.date_end = f.date_start + timedelta(hours=hours_diff)
            f.request_early = fields.Datetime.today()
        order = f.save()
        with Form(self.Order, view=view_id) as f:
            f.location_id = self.test_location
            f.date_start = fields.Datetime.today()
            f.date_end = f.date_start + timedelta(hours=80)
            f.request_early = fields.Datetime.today()
        order2 = f.save()
        order._get_stage_color()
        view_id = "fieldservice.fsm_equipment_form_view"
        with Form(self.env["fsm.equipment"], view=view_id) as f:
            f.name = "Equipment 1"
            f.current_location_id = self.test_location
            f.location_id = self.test_location
            f.notes = "test"
        equipment = f.save()
        order3 = self.Order.create(
            {
                "location_id": self.test_location.id,
                "stage_id": self.stage1.id,
            }
        )
        order4 = self.Order.create(
            {
                "location_id": self.test_location.id,
                "stage_id": self.stage2.id,
            }
        )
        self.init_values2 = {}
        self.tag._compute_full_name()
        self.tag1._compute_full_name()
        config = self.env["res.config.settings"].create({})
        config.module_fieldservice_repair = True
        config._onchange_group_fsm_equipment()
        config._onchange_module_fieldservice_repair()
        order3._track_subtype(self.init_values)
        order4._track_subtype(self.init_values)
        order3._track_subtype(self.init_values_2)
        order4._track_subtype(self.init_values_2)
        order4._track_subtype(self.init_values2)
        order4.action_complete()
        order3.action_cancel()
        self.env.user.company_id.auto_populate_equipments_on_order = True
        self.assertEqual(order.custom_color, order.stage_id.custom_color)
        # Test _compute_duration
        self.assertEqual(order.duration, hours_diff)
        # Test request_late
        priority_vs_late_days = {"0": 3, "1": 2, "2": 1, "3": 1 / 3}
        for priority, late_days in priority_vs_late_days.items():
            order_test = self.Order.create(
                {
                    "location_id": self.test_location.id,
                    "request_early": fields.Datetime.today(),
                    "priority": priority,
                }
            )
            self.assertEqual(
                order_test.request_late, order.request_early + timedelta(days=late_days)
            )
        # Test scheduled_date_start is not automatically set
        self.assertEqual(order.scheduled_date_start, False)
        # Test scheduled_date_end = scheduled_date_start + duration (hrs)
        # Set date start
        order.scheduled_date_start = fields.Datetime.now().replace(
            hour=0, minute=0, second=0
        )

        # Set duration
        duration = 10
        order.scheduled_duration = duration
        order.onchange_scheduled_duration()
        # Check date end
        self.assertEqual(
            order.scheduled_date_end,
            order.scheduled_date_start + timedelta(hours=duration),
        )
        # Set new date end
        order.scheduled_date_end = order.scheduled_date_end.replace(
            hour=1, minute=1, second=0
        )
        order.onchange_scheduled_date_end()
        # Check date start
        self.assertEqual(
            order.scheduled_date_start,
            order.scheduled_date_end - timedelta(hours=duration),
        )
        view_id = "fieldservice.fsm_location_form_view"
        with Form(self.env["fsm.location"], view=view_id) as f:
            f.name = "Child Location"
            f.fsm_parent_id = self.test_location
        location = f.save()
        self.test_team = self.env["fsm.team"].create({"name": "Test Team"})
        order_type = self.env["fsm.order.type"].create(
            {"name": "Test Type", "internal_type": "fsm"}
        )
        order.type = order_type.id
        stage = self.env["fsm.stage"]
        stage.get_color_information()
        with self.assertRaises(ValidationError):
            self.stage2.custom_color = "ECF0F1"
        with self.assertRaises(ValidationError):
            stage.create(
                {
                    "name": "Test",
                    "stage_type": "order",
                    "sequence": 10,
                }
            )
        order.description = "description"
        order.equipment_ids = equipment
        self.assertEqual(order.description, "description", "Shouldn't have changed")
        order.description = False
        equipment.notes = "equipment notes"
        order.equipment_ids = equipment
        self.assertEqual(
            order.description,
            equipment.notes,
            "Description should be set from equipment",
        )
        order.type = False
        order.description = False
        self.location_1.direction = "Test Direction"
        order2.location_id.fsm_parent_id = self.location_1.id
        data = (
            self.env["fsm.order"]
            .with_context(**{"default_team_id": self.test_team.id})
            .with_user(self.env.user)
            .read_group(
                [("id", "=", location.id)],
                fields=["stage_id"],
                groupby="stage_id",
            )
        )
        self.assertTrue(data, "It should be able to read group")
        self.Order.write(
            {
                "location_id": self.test_location.id,
                "stage_id": self.stage1.id,
                "is_button": True,
            }
        )
        with self.assertRaises(UserError):
            self.Order.write(
                {
                    "location_id": self.test_location.id,
                    "stage_id": self.stage1.id,
                }
            )
        order.can_unlink()
        order.unlink()

    def test_order_unlink(self):
        with self.assertRaises(ValidationError):
            order = self.Order.create(
                {
                    "location_id": self.test_location.id,
                    "stage_id": self.stage1.id,
                }
            )
            order.stage_id.stage_type = "location"
            order.can_unlink()
            order.unlink()
