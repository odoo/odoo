from datetime import date, datetime

from odoo.exceptions import UserError
from odoo.tests import Form, TransactionCase
from odoo.tools.safe_eval import safe_eval

ACTIVITY = "maintenance.mail_act_maintenance_order"


class TestMaintenanceOrderLifecycle(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Order = cls.env["maintenance.order"]
        cls.technician = cls.env["res.users"].create(
            {
                "name": "Lifecycle Technician",
                "login": "lifecycle_technician",
                "tz": "America/Mexico_City",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

    def _activities(self, order):
        return order.activity_ids.filtered(
            lambda activity: activity.activity_type_id == self.env.ref(ACTIVITY)
        )

    def test_an_order_moves_draft_confirmed_in_progress_done(self):
        order = self.Order.create({"name": "Lifecycle probe"})
        self.assertEqual(order.state, "draft")
        order.action_confirm()
        self.assertEqual(order.state, "confirmed")
        order.action_start()
        self.assertEqual(order.state, "in_progress")
        order.action_done()
        self.assertEqual(order.state, "done")
        self.assertTrue(order.close_date)

    def test_a_state_the_lifecycle_does_not_allow_is_refused(self):
        order = self.Order.create({"name": "Transition probe"})
        with self.assertRaises(UserError):
            order.action_start()
        order.action_confirm()
        order.action_done()
        with self.assertRaises(UserError):
            order.action_draft()
        with self.assertRaises(UserError):
            order.action_cancel()

    def test_a_cancelled_order_goes_back_to_draft(self):
        order = self.Order.create({"name": "Cancel probe"})
        order.action_confirm()
        order.action_cancel()
        self.assertEqual(order.state, "cancel")
        order.action_draft()
        self.assertEqual(order.state, "draft")

    def test_an_order_past_draft_is_not_deleted(self):
        order = self.Order.create({"name": "Unlink probe"})
        order.action_confirm()
        with self.assertRaises(UserError):
            order.unlink()
        order.action_cancel()
        order.unlink()
        self.assertFalse(order.exists())

    def test_the_close_date_follows_the_state_and_keeps_an_explicit_value(self):
        order = self.Order.create({"name": "Close date probe"})
        self.assertFalse(order.close_date)
        order.action_confirm()
        order.write({"state": "done", "close_date": date(2025, 5, 5)})
        self.assertEqual(order.close_date, date(2025, 5, 5))
        created_done = self.Order.create({"name": "Created done", "state": "done"})
        self.assertTrue(created_done.close_date)

    def test_a_state_write_leaves_the_caller_vals_alone(self):
        order = self.Order.create({"name": "Vals probe", "kanban_state": "blocked"})
        vals = {"state": "confirmed"}
        order.write(vals)
        self.assertEqual(vals, {"state": "confirmed"})
        self.assertEqual(order.kanban_state, "normal")

    def test_a_finished_or_cancelled_order_has_no_pending_activity(self):
        order = self.Order.create(
            {"name": "Activity probe", "schedule_date": datetime(2026, 9, 20, 10)}
        )
        self.assertEqual(len(self._activities(order)), 1)
        order.action_confirm()
        order.action_start()
        self.assertEqual(len(self._activities(order)), 1)
        self.assertFalse(
            order.message_ids.filtered("mail_activity_type_id"),
            "moving between open states does not complete the planned activity",
        )
        order.action_done()
        self.assertFalse(self._activities(order))
        self.assertTrue(order.message_ids.filtered("mail_activity_type_id"))
        other = self.Order.create(
            {"name": "Cancelled probe", "schedule_date": datetime(2026, 9, 20, 10)}
        )
        self.assertEqual(len(self._activities(other)), 1)
        other.action_cancel()
        self.assertFalse(self._activities(other))

    def test_clearing_the_schedule_or_the_technician_updates_the_activity(self):
        owner = self.env.ref("base.user_admin")
        order = self.Order.create(
            {
                "name": "Activity probe",
                "owner_user_id": owner.id,
                "user_id": self.technician.id,
                "schedule_date": datetime(2026, 9, 20, 10),
            }
        )
        order.user_id = False
        self.assertEqual(self._activities(order).user_id, owner)
        order.schedule_date = False
        self.assertFalse(self._activities(order))

    def test_the_activity_deadline_is_the_assignee_local_day(self):
        order = self.Order.create(
            {
                "name": "Timezone probe",
                "user_id": self.technician.id,
                "schedule_date": datetime(2026, 9, 21, 2, 0),
            }
        )
        self.assertEqual(self._activities(order).date_deadline, date(2026, 9, 20))

    def test_closing_several_orders_at_once_completes_their_activities(self):
        orders = self.Order.create(
            [
                {"name": f"Batch {index}", "schedule_date": datetime(2026, 9, 20, 10)}
                for index in range(5)
            ]
        )
        orders.action_confirm()
        orders.action_done()
        self.assertEqual(set(orders.mapped("state")), {"done"})
        self.assertFalse(orders.activity_ids)


class TestMaintenanceDefaultTeam(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["team.team"].search([]).action_archive()
        cls.company_a = cls.env["res.company"].create({"name": "Team probe A"})
        cls.company_b = cls.env["res.company"].create({"name": "Team probe B"})
        cls.team_a = cls.env["team.team"].create(
            {"use_maintenance": True, "name": "Team A", "company_id": cls.company_a.id}
        )
        cls.shared_team = cls.env["team.team"].create(
            {"use_maintenance": True, "name": "Shared team", "company_id": False}
        )

    def _create_for(self, company):
        return (
            self.env["maintenance.order"]
            .with_context(allowed_company_ids=[self.company_a.id, self.company_b.id])
            .with_company(company)
            .create({"name": "Team probe", "company_id": company.id})
        )

    def test_a_company_without_its_own_team_takes_a_shared_one(self):
        self.assertEqual(
            self._create_for(self.company_b).maintenance_team_id, self.shared_team
        )

    def test_the_company_team_wins_over_the_shared_one(self):
        self.assertEqual(
            self._create_for(self.company_a).maintenance_team_id, self.team_a
        )


class TestMaintenanceEquipmentAndDashboards(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.technician = cls.env["res.users"].create(
            {"name": "Category Technician", "login": "category_technician"}
        )
        cls.category = cls.env["maintenance.equipment.category"].create(
            {"name": "Probe category", "technician_user_id": cls.technician.id}
        )

    def test_an_equipment_created_in_code_takes_its_category_technician(self):
        equipment = self.env["maintenance.equipment"].create(
            {"name": "Probe equipment", "category_id": self.category.id}
        )
        self.assertEqual(equipment.technician_user_id, self.technician)
        other = self.env.ref("base.user_admin")
        explicit = self.env["maintenance.equipment"].create(
            {
                "name": "Explicit technician",
                "category_id": self.category.id,
                "technician_user_id": other.id,
            }
        )
        self.assertEqual(explicit.technician_user_id, other)
        with Form(self.env["maintenance.equipment"]) as form:
            form.name = "Form equipment"
            form.category_id = self.category
            self.assertEqual(form.technician_user_id, self.technician)

    def test_the_category_fold_and_counts_follow_its_equipment(self):
        self.assertTrue(self.category.fold)
        equipment = self.env["maintenance.equipment"].create(
            {"name": "Probe equipment", "category_id": self.category.id}
        )
        self.assertFalse(self.category.fold)
        self.env["maintenance.order"].create(
            [
                {
                    "name": "Done",
                    "equipment_id": equipment.id,
                    "state": "done",
                },
                {"name": "Open", "equipment_id": equipment.id},
            ]
        )
        self.category.invalidate_recordset()
        self.assertEqual(self.category.maintenance_count, 2)
        self.assertEqual(self.category.maintenance_open_count, 1)
        self.assertEqual(
            self.category.maintenance_open_count, equipment.maintenance_open_count
        )
        equipment.action_archive()
        self.assertTrue(self.category.fold)

    def test_a_shared_team_offers_every_internal_user_as_member(self):
        shared = self.env["team.team"].new({"use_maintenance": True, "name": "Shared"})
        domain = safe_eval(
            self.env["team.team"]._fields["member_ids"].domain,
            {"member_company_ids": shared.member_company_ids.ids},
        )
        self.assertIn(self.technician, self.env["res.users"].search(domain))

    def test_the_dashboard_links_name_filters_that_exist(self):
        search_arch = self.env.ref("maintenance.maintenance_order_view_search").arch
        dashboard_arch = self.env.ref("maintenance.maintenance_team_kanban").arch
        for name in (
            "todo",
            "progress",
            "done",
            "high_priority",
            "kanban_state_block",
            "unscheduled",
        ):
            with self.subTest(filter=name):
                self.assertIn(f"search_default_{name}", dashboard_arch)
                self.assertIn(f'name="{name}"', search_arch)


class TestMaintenanceSchedule(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.equipment = cls.env["maintenance.equipment"].create(
            {"name": "Schedule probe equipment"}
        )

    def _order(self, **vals):
        return self.env["maintenance.order"].create(
            {
                "name": "Schedule probe",
                "equipment_id": self.equipment.id,
                "schedule_date": datetime(2026, 9, 20, 10),
                "schedule_end": datetime(2026, 9, 20, 14),
                **vals,
            }
        )

    def test_moving_the_start_keeps_the_planned_duration(self):
        order = self._order()
        self.assertEqual(order.duration, 4)
        order.schedule_date = datetime(2026, 9, 21, 10)
        self.assertEqual(order.schedule_end, datetime(2026, 9, 21, 14))
        with Form(order) as form:
            form.schedule_date = datetime(2026, 9, 22, 8)
            self.assertEqual(form.schedule_end, datetime(2026, 9, 22, 12))
        self.assertEqual(order.duration, 4)

    def test_moving_the_end_changes_the_duration(self):
        order = self._order()
        order.schedule_end = datetime(2026, 9, 20, 11, 30)
        self.assertEqual(order.duration, 1.5)
        order.write(
            {
                "schedule_date": datetime(2026, 9, 25, 9),
                "schedule_end": datetime(2026, 9, 25, 17),
            }
        )
        self.assertEqual(order.duration, 8)

    def test_a_start_alone_plans_one_hour(self):
        order = self.env["maintenance.order"].create(
            {"name": "One hour", "schedule_date": datetime(2026, 9, 20, 10)}
        )
        self.assertEqual(order.schedule_end, datetime(2026, 9, 20, 11))
        self.assertEqual(order.duration, 1)


class TestMaintenanceReliabilityFigures(TransactionCase):
    def _equipment_with_failures(self, date_effective, failures):
        equipment = self.env["maintenance.equipment"].create(
            {"name": "Reliability probe", "date_effective": date_effective}
        )
        for date_order, close_date in failures:
            self.env["maintenance.order"].create(
                {
                    "name": "Failure",
                    "equipment_id": equipment.id,
                    "maintenance_type": "corrective",
                    "date_order": date_order,
                    "state": "done",
                    "close_date": close_date,
                }
            )
        return equipment

    def test_failures_before_the_effective_date_give_no_negative_mtbf(self):
        equipment = self._equipment_with_failures(
            date(2026, 9, 10), [(date(2026, 9, 1), date(2026, 9, 3))]
        )
        self.assertEqual(equipment.mtbf, 0)
        self.assertFalse(equipment.estimated_next_failure)

    def test_mttr_averages_only_the_repairs_with_both_dates(self):
        equipment = self._equipment_with_failures(
            date(2026, 1, 1),
            [(date(2026, 3, 1), date(2026, 3, 5)), (date(2026, 4, 1), False)],
        )
        self.assertEqual(equipment.mttr, 4)
        self.assertEqual(
            equipment.mtbf, (date(2026, 4, 1) - date(2026, 1, 1)).days // 2
        )


class TestMaintenanceTeamAlias(TransactionCase):
    def test_a_mail_to_a_company_team_creates_the_order_in_that_company(self):
        company = self.env["res.company"].create({"name": "Alias company"})
        team = self.env["team.team"].create(
            {
                "use_maintenance": True,
                "name": "Alias team",
                "company_id": company.id,
                "maintenance_alias_name": "alias-team",
            }
        )
        order = self.env["maintenance.order"].message_new(
            {
                "from": "reporter@example.com",
                "email_from": "reporter@example.com",
                "to": "alias-team@example.com",
                "cc": "",
                "subject": "Pump leaking",
                "body": "<p>It leaks.</p>",
                "message_id": "<maintenance-team-alias@example.com>",
            },
            custom_values=team.maintenance_alias_id.alias_id._get_alias_defaults(),
        )
        self.assertRecordValues(
            order,
            [{"company_id": company.id, "maintenance_team_id": team.id}],
        )


class TestMaintenanceEquipmentAccess(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group_user = cls.env.ref("base.group_user")
        cls.technician, cls.category_technician = cls.env["res.users"].create(
            [
                {
                    "name": "Equipment technician",
                    "login": "equipment_technician",
                    "group_ids": [(6, 0, [group_user.id])],
                },
                {
                    "name": "Category technician",
                    "login": "equipment_category_technician",
                    "group_ids": [(6, 0, [group_user.id])],
                },
            ]
        )

    def _visible_to(self, user, equipment):
        return bool(
            self.env["maintenance.equipment"]
            .with_user(user)
            .search_count([("id", "=", equipment.id)])
        )

    def test_the_technician_can_read_the_equipment_they_maintain(self):
        equipment = self.env["maintenance.equipment"].create(
            {"name": "Compressor", "technician_user_id": self.technician.id}
        )
        self.assertTrue(self._visible_to(self.technician, equipment))
        order = self.env["maintenance.order"].create(
            {"name": "Noise", "equipment_id": equipment.id}
        )
        read = order.with_user(self.technician).web_read(
            {"equipment_id": {"fields": {"display_name": {}}}}
        )
        self.assertEqual(read[0]["equipment_id"]["display_name"], "Compressor")

    def test_a_technician_from_a_new_category_follows_the_equipment(self):
        equipment = self.env["maintenance.equipment"].create({"name": "Lathe"})
        category = self.env["maintenance.equipment.category"].create(
            {"name": "Machines", "technician_user_id": self.category_technician.id}
        )
        equipment.category_id = category
        self.assertEqual(equipment.technician_user_id, self.category_technician)
        self.assertTrue(self._visible_to(self.category_technician, equipment))


class TestMaintenanceOrderApproval(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.approver = cls.env["res.users"].create(
            {
                "name": "Maintenance approver",
                "login": "maintenance_approver",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.category = cls.env["approval.category"].create(
            {
                "name": "Corrective maintenance",
                "approval_type": "maintenance_corrective",
                "approval_minimum": 1,
                "step_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Approver",
                            "minimum": 1,
                            "member_ids": [(0, 0, {"user_id": cls.approver.id})],
                        },
                    )
                ],
            }
        )

    def test_without_a_category_an_order_confirms_at_once(self):
        order = self.env["maintenance.order"].create(
            {"name": "Preventive", "maintenance_type": "preventive"}
        )
        self.assertFalse(order.approval_required)
        order.action_confirm()
        self.assertEqual(order.state, "confirmed")
        self.assertFalse(order.approval_request_id)

    def test_an_order_a_category_applies_to_confirms_on_approval(self):
        order = self.env["maintenance.order"].create(
            {"name": "Corrective", "maintenance_type": "corrective"}
        )
        self.assertTrue(order.approval_required)
        order.action_confirm()
        self.assertEqual(order.state, "draft")
        self.assertEqual(order.approval_state, "pending")
        with self.assertRaises(UserError):
            order.action_confirm()
        order.approval_request_id.with_user(self.approver).action_approve()
        self.assertEqual(order.approval_state, "approved")
        self.assertEqual(order.state, "confirmed")

    def test_cancelling_an_order_waiting_for_approval_refuses_the_request(self):
        order = self.env["maintenance.order"].create(
            {"name": "Corrective", "maintenance_type": "corrective"}
        )
        order.action_confirm()
        order.action_cancel()
        self.assertEqual(order.state, "cancel")
        self.assertIn(order.approval_state, ("refused", "cancelled"))
