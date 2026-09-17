from odoo import fields
from odoo.tests import Form
from odoo.tests.common import TransactionCase, tagged


class TestMaintenanceCommon(TransactionCase):
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
        self.asset = self.env["resource.asset"]
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

        self.monitor_kind = self.env["resource.asset.kind"].create(
            {"name": "Monitors - Test", "code": "monitor_test"}
        )


class TestMaintenance(TestMaintenanceCommon):
    def test_10_asset_order(self):
        monitor = self.asset.with_user(self.manager).create(
            {
                "name": 'Samsung Monitor "15',
                "kind_id": self.monitor_kind.id,
                "technician_user_id": self.ref("base.user_root"),
                "model": "NP355E5X",
                "color": 3,
            }
        )

        # Create new maintenance order
        maintenance_order_01 = self.maintenance_order.with_user(self.user).create(
            {
                "name": "Resolution is bad",
                "user_id": self.user.id,
                "resource_ids": monitor.resource_id.ids,
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
class TestMaintenancePostInstall(TestMaintenanceCommon):
    def test_a_maintenance_manager_creates_an_asset_an_employee_opens(self):
        with self.with_user("hm"):
            form = Form(self.env["resource.asset"])
            form.name = "Super Equipment"
            form.kind_id = self.monitor_kind
            asset = form.save()

        with self.with_user("emp"):
            form = Form(self.env["resource.asset"].browse(asset.id))
            self.assertEqual(form.name, "Super Equipment")

    def test_done_maintenance_no_date_done_or_date_confirmed(self):
        """
        Ensure an asset with done maintenance orders that have
        `date_done` or `date_confirmed` set to False can still be opened.
        In theory this should never happen, but we should fail gracefully
        in case these dates are forced set to False.
        """

        form = Form(self.env["resource.asset"].with_user(self.manager))
        form.name = "brain"
        form.kind_id = self.monitor_kind
        equipment = form.save()
        form = Form(self.env["maintenance.order"].with_user(self.manager))
        form.name = "improve efficiency"
        form.resource_ids.add(equipment.resource_id)
        form.maintenance_type = "corrective"
        maintenance = form.save()
        self.assertFalse(maintenance.date_confirmed)
        self.assertFalse(maintenance.date_done)

        maintenance.action_confirm()
        maintenance.action_done()
        self.assertTrue(maintenance.date_confirmed)
        self.assertTrue(maintenance.date_done)
        form = Form(equipment)

        # this shouldn't happen unless it's forced
        maintenance.date_done = False
        form = Form(equipment)
        maintenance.date_done = fields.Date.today()
        maintenance.date_confirmed = False
        form = Form(equipment)
        maintenance.date_done = False
        form = Form(equipment)
