import time

from odoo import fields
from odoo.tests import Form
from odoo.tests.common import TransactionCase, tagged


class TestEquipmentCommon(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env["approval.category"].search(
            [
                (
                    "approval_type",
                    "in",
                    ("maintenance_preventive", "maintenance_corrective"),
                )
            ]
        ).action_archive()
        self.equipment = self.env["maintenance.equipment"]
        self.maintenance_order = self.env["maintenance.order"]
        self.res_users = self.env["res.users"]
        self.maintenance_team = self.env["team.team"]
        self.main_company = self.env.ref("base.main_company")
        res_user = self.env.ref("base.group_user")
        res_manager = self.env.ref("maintenance.group_equipment_manager")

        self.user = self.res_users.create(
            {
                "name": "Normal User/Employee",
                "company_id": self.main_company.id,
                "login": "emp",
                "email": "empuser@yourcompany.example.com",
                "group_ids": [(6, 0, [res_user.id])],
            }
        )

        self.manager = self.res_users.create(
            {
                "name": "Equipment Manager",
                "company_id": self.main_company.id,
                "login": "hm",
                "email": "eqmanager@yourcompany.example.com",
                "group_ids": [(6, 0, [res_manager.id])],
            }
        )

        self.equipment_monitor = self.env["maintenance.equipment.category"].create(
            {
                "name": "Monitors - Test",
            }
        )


class TestEquipment(TestEquipmentCommon):
    def test_10_equipment_order_category(self):

        # Create a new equipment
        equipment_01 = self.equipment.with_user(self.manager).create(
            {
                "name": 'Samsung Monitor "15',
                "category_id": self.equipment_monitor.id,
                "technician_user_id": self.ref("base.user_root"),
                "owner_user_id": self.user.id,
                "assign_date": time.strftime("%Y-%m-%d"),
                "serial_no": "MT/127/18291015",
                "model": "NP355E5X",
                "color": 3,
            }
        )

        # Check that equipment is created or not
        assert equipment_01, "Equipment not created"

        # Create new maintenance order
        maintenance_order_01 = self.maintenance_order.with_user(self.user).create(
            {
                "name": "Resolution is bad",
                "user_id": self.user.id,
                "owner_user_id": self.user.id,
                "equipment_id": equipment_01.id,
                "color": 7,
                "maintenance_team_id": self.ref(
                    "maintenance.equipment_team_maintenance"
                ),
            }
        )

        # I check that maintenance_order is created or not
        assert maintenance_order_01, "Maintenance Order not created"

        # I check that Initially maintenance order is a draft
        self.assertEqual(maintenance_order_01.state, "draft")

        # I check that the user confirms and starts the maintenance order
        maintenance_order_01.with_user(self.user).action_confirm()
        maintenance_order_01.with_user(self.user).action_start()

        # I check that maintenance order is in progress
        self.assertEqual(maintenance_order_01.state, "in_progress")

    def test_a_forever_plan_opens_the_next_order_confirmed(self):
        plan = self.env["maintenance.plan"].create(
            {"name": "Test forever maintenance", "repeat_type": "forever"}
        )
        self.assertEqual(plan.order_ids.state, "confirmed")
        plan.order_ids.action_done()
        next_order = plan.order_ids.filtered(lambda order: order.state != "done")
        self.assertEqual(next_order.state, "confirmed")

    def test_update_multiple_maintenance_order_record(self):
        """
        Test that multiple records of the model 'maintenance.order' can be written simultaneously.
        """
        maintenance_orders = self.env["maintenance.order"].create(
            [
                {
                    "name": "m_1",
                    "maintenance_type": "preventive",
                    "kanban_state": "normal",
                },
                {
                    "name": "m_2",
                    "maintenance_type": "preventive",
                    "kanban_state": "normal",
                },
            ]
        )
        maintenance_orders.write({"kanban_state": "blocked", "priority": "3"})
        self.assertRecordValues(
            maintenance_orders,
            [
                {"kanban_state": "blocked", "priority": "3"},
                {"kanban_state": "blocked", "priority": "3"},
            ],
        )


@tagged("post_install", "-at_install")
class TestEquipmentPostInstall(TestEquipmentCommon):
    def test_basic_access_and_new_equipment(self):
        """
        Ensure that
        - a maintenance manager can create an equipment and assign it to a
        specific user
        - the user can open it
        """
        equipment_name = "Super Equipment"

        with self.with_user("hm"):
            form = Form(self.env["maintenance.equipment"])
            form.name = equipment_name
            equipment = form.save()

        self.assertTrue(equipment)
        equipment.owner_user_id = self.user

        with self.with_user("emp"):
            # Using browse to avoid the env of record `equipment`
            form = Form(self.env["maintenance.equipment"].browse(equipment.id))
            self.assertEqual(form.name, equipment_name)

    def test_done_maintenance_no_close_or_date_order(self):
        """
        Ensure equipment with done maintenance orders that have
        `close_date` or `date_order` set to False can still be opened.
        In theory this should never happen, but we should fail gracefully
        in case these dates are forced set to False.
        """

        form = Form(self.env["maintenance.equipment"].with_user(self.manager))
        form.name = "brain"
        equipment = form.save()
        form = Form(self.env["maintenance.order"].with_user(self.manager))
        form.name = "improve efficiency"
        form.equipment_id = equipment
        form.maintenance_type = "corrective"
        maintenance = form.save()
        self.assertTrue(maintenance.date_order)
        self.assertFalse(maintenance.close_date)

        maintenance.action_confirm()
        maintenance.action_done()
        self.assertTrue(maintenance.date_order)
        self.assertTrue(maintenance.close_date)
        form = Form(equipment)

        # this shouldn't happen unless it's forced
        maintenance.close_date = False
        form = Form(equipment)
        maintenance.close_date = fields.Date.today()
        maintenance.date_order = False
        form = Form(equipment)
        maintenance.close_date = False
        form = Form(equipment)
