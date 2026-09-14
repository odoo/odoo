from datetime import date, datetime

from odoo.exceptions import ValidationError
from odoo.tests import Form, TransactionCase
from odoo.tools.safe_eval import safe_eval

ACTIVITY = "maintenance.mail_act_maintenance_request"


class TestMaintenanceRequestLifecycle(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Request = cls.env["maintenance.request"]
        cls.stage_new = cls.env.ref("maintenance.stage_0")
        cls.stage_progress = cls.env.ref("maintenance.stage_1")
        cls.stage_repaired = cls.env.ref("maintenance.stage_3")
        cls.stage_scrap = cls.env.ref("maintenance.stage_4")
        cls.technician = cls.env["res.users"].create(
            {
                "name": "Lifecycle Technician",
                "login": "lifecycle_technician",
                "tz": "America/Mexico_City",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

    def _recurring(self, **vals):
        return self.Request.create(
            {
                "name": "Recurring probe",
                "maintenance_type": "preventive",
                "recurring_maintenance": True,
                "repeat_interval": 1,
                "repeat_unit": "week",
                "schedule_date": datetime(2026, 9, 1, 10),
                **vals,
            }
        )

    def _successors(self, request):
        return self.Request.search(
            [("name", "=", request.name), ("id", "!=", request.id)]
        )

    def _activities(self, request):
        return request.activity_ids.filtered(
            lambda activity: activity.activity_type_id == self.env.ref(ACTIVITY)
        )

    def test_only_the_first_closing_stage_creates_the_next_occurrence(self):
        request = self._recurring()
        request.stage_id = self.stage_repaired
        request.stage_id = self.stage_scrap
        request.write({"stage_id": self.stage_scrap.id})
        successor = self._successors(request)
        self.assertEqual(len(successor), 1)
        self.assertRecordValues(
            successor,
            [
                {
                    "stage_id": self.stage_new.id,
                    "schedule_date": datetime(2026, 9, 8, 10),
                    "close_date": False,
                }
            ],
        )

    def test_a_closing_write_that_stops_the_recurrence_creates_nothing(self):
        request = self._recurring()
        request.write(
            {"stage_id": self.stage_repaired.id, "recurring_maintenance": False}
        )
        self.assertFalse(self._successors(request))

    def test_an_until_recurrence_stops_after_its_end_date(self):
        request = self._recurring(repeat_type="until", repeat_until=date(2026, 9, 5))
        request.stage_id = self.stage_repaired
        self.assertFalse(self._successors(request))

    def test_an_until_recurrence_needs_its_end_date(self):
        with self.assertRaises(ValidationError):
            self._recurring(repeat_type="until")

    def test_the_close_date_follows_the_stage_and_keeps_an_explicit_value(self):
        request = self.Request.create({"name": "Close date probe"})
        self.assertFalse(request.close_date)
        request.write(
            {"stage_id": self.stage_repaired.id, "close_date": date(2025, 5, 5)}
        )
        self.assertEqual(request.close_date, date(2025, 5, 5))
        request.stage_id = self.stage_scrap
        self.assertEqual(request.close_date, date(2025, 5, 5))
        request.stage_id = self.stage_progress
        self.assertFalse(request.close_date)
        created_done = self.Request.create(
            {"name": "Created done", "stage_id": self.stage_repaired.id}
        )
        self.assertTrue(created_done.close_date)

    def test_a_stage_write_leaves_the_caller_vals_alone(self):
        request = self.Request.create({"name": "Vals probe"})
        vals = {"stage_id": self.stage_progress.id}
        request.write(vals)
        self.assertEqual(vals, {"stage_id": self.stage_progress.id})
        self.assertEqual(request.kanban_state, "normal")

    def test_a_finished_or_cancelled_request_has_no_pending_activity(self):
        request = self.Request.create(
            {"name": "Activity probe", "schedule_date": datetime(2026, 9, 20, 10)}
        )
        self.assertEqual(len(self._activities(request)), 1)
        request.stage_id = self.stage_progress
        self.assertEqual(len(self._activities(request)), 1)
        self.assertFalse(
            request.message_ids.filtered("mail_activity_type_id"),
            "moving between open stages does not complete the planned activity",
        )
        request.stage_id = self.stage_repaired
        self.assertFalse(self._activities(request))
        self.assertTrue(request.message_ids.filtered("mail_activity_type_id"))
        request.stage_id = self.stage_new
        self.assertEqual(len(self._activities(request)), 1)
        request.archive_equipment_request()
        self.assertFalse(self._activities(request))

    def test_clearing_the_schedule_or_the_technician_updates_the_activity(self):
        owner = self.env.ref("base.user_admin")
        request = self.Request.create(
            {
                "name": "Activity probe",
                "owner_user_id": owner.id,
                "user_id": self.technician.id,
                "schedule_date": datetime(2026, 9, 20, 10),
            }
        )
        request.user_id = False
        self.assertEqual(self._activities(request).user_id, owner)
        request.schedule_date = False
        self.assertFalse(self._activities(request))

    def test_the_activity_deadline_is_the_assignee_local_day(self):
        request = self.Request.create(
            {
                "name": "Timezone probe",
                "user_id": self.technician.id,
                "schedule_date": datetime(2026, 9, 21, 2, 0),
            }
        )
        self.assertEqual(self._activities(request).date_deadline, date(2026, 9, 20))

    def test_closing_several_requests_at_once_completes_their_activities(self):
        requests = self.Request.create(
            [
                {"name": f"Batch {index}", "schedule_date": datetime(2026, 9, 20, 10)}
                for index in range(5)
            ]
        )
        requests.write({"stage_id": self.stage_repaired.id})
        self.assertEqual(set(requests.mapped("done")), {True})
        self.assertFalse(requests.activity_ids)


class TestMaintenanceDefaultTeam(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["maintenance.team"].search([]).action_archive()
        cls.company_a = cls.env["res.company"].create({"name": "Team probe A"})
        cls.company_b = cls.env["res.company"].create({"name": "Team probe B"})
        cls.team_a = cls.env["maintenance.team"].create(
            {"name": "Team A", "company_id": cls.company_a.id}
        )
        cls.shared_team = cls.env["maintenance.team"].create(
            {"name": "Shared team", "company_id": False}
        )

    def _create_for(self, company):
        return (
            self.env["maintenance.request"]
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
        self.env["maintenance.request"].create(
            [
                {
                    "name": "Done",
                    "equipment_id": equipment.id,
                    "stage_id": self.env.ref("maintenance.stage_3").id,
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
        domain = safe_eval(
            self.env["maintenance.team"]._fields["member_ids"].domain,
            {"company_id": False},
        )
        self.assertIn(self.technician, self.env["res.users"].search(domain))

    def test_the_dashboard_links_name_filters_that_exist(self):
        search_arch = self.env.ref("maintenance.hr_equipment_request_view_search").arch
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

    def _request(self, **vals):
        return self.env["maintenance.request"].create(
            {
                "name": "Schedule probe",
                "equipment_id": self.equipment.id,
                "schedule_date": datetime(2026, 9, 20, 10),
                "schedule_end": datetime(2026, 9, 20, 14),
                **vals,
            }
        )

    def test_moving_the_start_keeps_the_planned_duration(self):
        request = self._request()
        self.assertEqual(request.duration, 4)
        request.schedule_date = datetime(2026, 9, 21, 10)
        self.assertEqual(request.schedule_end, datetime(2026, 9, 21, 14))
        with Form(request) as form:
            form.schedule_date = datetime(2026, 9, 22, 8)
            self.assertEqual(form.schedule_end, datetime(2026, 9, 22, 12))
        self.assertEqual(request.duration, 4)

    def test_moving_the_end_changes_the_duration(self):
        request = self._request()
        request.schedule_end = datetime(2026, 9, 20, 11, 30)
        self.assertEqual(request.duration, 1.5)
        request.write(
            {
                "schedule_date": datetime(2026, 9, 25, 9),
                "schedule_end": datetime(2026, 9, 25, 17),
            }
        )
        self.assertEqual(request.duration, 8)

    def test_a_start_alone_plans_one_hour(self):
        request = self.env["maintenance.request"].create(
            {"name": "One hour", "schedule_date": datetime(2026, 9, 20, 10)}
        )
        self.assertEqual(request.schedule_end, datetime(2026, 9, 20, 11))
        self.assertEqual(request.duration, 1)

    def test_the_next_occurrence_keeps_the_duration(self):
        request = self._request(
            maintenance_type="preventive",
            recurring_maintenance=True,
            repeat_interval=1,
            repeat_unit="day",
        )
        request.stage_id = self.env.ref("maintenance.stage_3")
        successor = self.env["maintenance.request"].search(
            [("name", "=", request.name), ("id", "!=", request.id)]
        )
        self.assertRecordValues(
            successor,
            [
                {
                    "schedule_date": datetime(2026, 9, 21, 10),
                    "schedule_end": datetime(2026, 9, 21, 14),
                    "duration": 4,
                }
            ],
        )


class TestMaintenanceReliabilityFigures(TransactionCase):
    def _equipment_with_failures(self, date_effective, failures):
        equipment = self.env["maintenance.equipment"].create(
            {"name": "Reliability probe", "date_effective": date_effective}
        )
        repaired = self.env.ref("maintenance.stage_3")
        for request_date, close_date in failures:
            self.env["maintenance.request"].create(
                {
                    "name": "Failure",
                    "equipment_id": equipment.id,
                    "maintenance_type": "corrective",
                    "request_date": request_date,
                    "stage_id": repaired.id,
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
    def test_a_mail_to_a_company_team_creates_the_request_in_that_company(self):
        company = self.env["res.company"].create({"name": "Alias company"})
        team = self.env["maintenance.team"].create(
            {"name": "Alias team", "company_id": company.id, "alias_name": "alias-team"}
        )
        request = self.env["maintenance.request"].message_new(
            {
                "from": "reporter@example.com",
                "email_from": "reporter@example.com",
                "to": "alias-team@example.com",
                "cc": "",
                "subject": "Pump leaking",
                "body": "<p>It leaks.</p>",
                "message_id": "<maintenance-team-alias@example.com>",
            },
            custom_values=team.alias_id._get_alias_defaults(),
        )
        self.assertRecordValues(
            request,
            [{"company_id": company.id, "maintenance_team_id": team.id}],
        )
