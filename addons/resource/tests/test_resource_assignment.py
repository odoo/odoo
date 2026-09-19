from datetime import datetime, timedelta

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestResourceAssignment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Assignment = cls.env["resource.assignment"]
        cls.Reservation = cls.env["resource.reservation"]
        cls.truck = cls.env["resource.resource"].create(
            {"name": "Truck 12", "resource_type": "material", "tz": "UTC"}
        )
        cls.driver = cls.env["resource.resource"].create(
            {"name": "Ana", "resource_type": "user", "tz": "UTC"}
        )
        cls.other_driver = cls.env["resource.resource"].create(
            {"name": "Bo", "resource_type": "user", "tz": "UTC"}
        )
        cls.now = datetime.now().replace(microsecond=0)

    def _assign(self, assignee=None, **vals):
        return self.Assignment.create(
            {
                "resource_id": self.truck.id,
                "assignee_id": (assignee or self.driver).id,
                "custody_role": "operator",
                "date_start": self.now - timedelta(days=1),
                **vals,
            }
        )

    def test_name_and_state(self):
        assignment = self._assign()
        self.assertEqual(assignment.name, "Ana, Operator of Truck 12")
        self.assertEqual(assignment.state, "active")
        assignment.date_end = self.now - timedelta(hours=1)
        self.assertEqual(assignment.state, "ended")
        assignment.write(
            {"date_start": self.now + timedelta(days=1), "date_end": False}
        )
        self.assertEqual(assignment.state, "planned")

    def test_state_is_searchable(self):
        active = self._assign()
        ended = self._assign(
            assignee=self.other_driver, date_end=self.now - timedelta(hours=1)
        )
        planned = self._assign(
            assignee=self.other_driver, date_start=self.now + timedelta(days=2)
        )
        found = self.Assignment.search([("resource_id", "=", self.truck.id)])
        self.assertEqual(found.filtered(lambda a: a.state == "active"), active)
        self.assertEqual(
            self.Assignment.search(
                [("resource_id", "=", self.truck.id), ("state", "=", "active")]
            ),
            active,
        )
        self.assertEqual(
            self.Assignment.search(
                [
                    ("resource_id", "=", self.truck.id),
                    ("state", "in", ["ended", "planned"]),
                ]
            ),
            ended | planned,
        )
        self.assertEqual(
            self.Assignment.search(
                [("resource_id", "=", self.truck.id), ("state", "!=", "active")]
            ),
            ended | planned,
        )

    def test_holder_is_the_current_assignee(self):
        self.assertFalse(self.truck.holder_id)
        self._assign(assignee=self.other_driver, date_end=self.now - timedelta(hours=1))
        self.assertFalse(self.truck.holder_id)
        self._assign()
        self.truck.invalidate_recordset(["holder_id"])
        self.assertEqual(self.truck.holder_id, self.driver)
        self.assertIn(
            self.truck,
            self.env["resource.resource"].search([("holder_id", "=", self.driver.id)]),
        )
        self.assertNotIn(
            self.truck,
            self.env["resource.resource"].search(
                [("holder_id", "=", self.other_driver.id)]
            ),
        )

    def test_holder_search_negative_operators(self):
        idle = self.env["resource.resource"].create(
            {"name": "Idle", "resource_type": "material", "tz": "UTC"}
        )
        self._assign()
        Resource = self.env["resource.resource"]
        self.assertEqual(
            Resource.search(
                [("id", "in", (self.truck | idle).ids), ("holder_id", "=", False)]
            ),
            idle,
        )
        self.assertEqual(
            Resource.search(
                [
                    ("id", "in", (self.truck | idle).ids),
                    ("holder_id", "!=", self.driver.id),
                ]
            ),
            idle,
        )
        self.assertEqual(
            Resource.search(
                [
                    ("id", "in", (self.truck | idle).ids),
                    ("holder_id", "not in", [self.driver.id]),
                ]
            ),
            idle,
        )

    def test_holder_search_agrees_with_the_compute(self):
        self._assign(
            custody_role="manager",
            assignee=self.other_driver,
            date_start=self.now - timedelta(days=10),
        )
        self._assign(custody_role="operator", date_start=self.now - timedelta(days=1))
        self.truck.invalidate_recordset(["holder_id"])
        self.assertEqual(self.truck.holder_id, self.driver)
        Resource = self.env["resource.resource"]
        self.assertNotIn(
            self.truck,
            Resource.search(
                [("id", "=", self.truck.id), ("holder_id", "=", self.other_driver.id)]
            ),
        )
        self.assertIn(
            self.truck,
            Resource.search(
                [("id", "=", self.truck.id), ("holder_id", "=", self.driver.id)]
            ),
        )

    def test_holder_by_role_and_moment(self):
        self._assign(custody_role="manager", assignee=self.other_driver)
        self._assign(custody_role="operator")
        self.assertEqual(
            self.Assignment._get_holder(self.truck, custody_role="manager"),
            self.other_driver,
        )
        self.assertEqual(
            self.Assignment._get_holder(self.truck, custody_role="operator"),
            self.driver,
        )
        self.assertFalse(
            self.Assignment._get_holder(self.truck, at=self.now - timedelta(days=5))
        )

    def test_the_operator_and_manager_are_fields_of_the_resource(self):
        self.truck.operator_id = self.driver
        self.truck.manager_id = self.other_driver
        live = self.Assignment._search_custody(self.truck)
        self.assertEqual(len(live), 2)
        self.assertEqual(
            {(a.custody_role, a.assignee_id) for a in live},
            {("operator", self.driver), ("manager", self.other_driver)},
        )
        self.truck.invalidate_recordset()
        self.assertEqual(self.truck.operator_id, self.driver)
        self.assertEqual(self.truck.manager_id, self.other_driver)
        self.assertIn(
            self.truck,
            self.truck.search([("operator_id", "=", self.driver.id)]),
        )
        self.assertIn(self.truck, self.truck.search([("manager_id", "ilike", "Bo")]))

    def test_a_new_operator_supersedes_the_live_one(self):
        first = self._assign()
        second = self._assign(assignee=self.other_driver, date_start=self.now)
        self.assertEqual(first.state, "ended")
        self.assertEqual(second.state, "active")
        self.truck.invalidate_recordset()
        self.assertEqual(self.truck.operator_id, self.other_driver)

    def test_a_technician_does_not_supersede_another(self):
        first = self._assign(custody_role="technician")
        self._assign(
            custody_role="technician", assignee=self.other_driver, date_start=self.now
        )
        self.assertEqual(first.state, "active")

    def test_clearing_the_operator_ends_custody_without_a_successor(self):
        assignment = self._assign()
        self.truck.operator_id = False
        self.assertEqual(assignment.state, "ended")
        self.assertFalse(self.Assignment._search_custody(self.truck))

    def test_a_future_operator_is_a_planned_assignment(self):
        self.truck.write(
            {
                "future_operator_id": self.other_driver.id,
                "date_future_operator": self.now + timedelta(days=3),
            }
        )
        planned = self.Assignment._search_custody(self.truck, when="planned")
        self.assertEqual(planned.assignee_id, self.other_driver)
        self.assertEqual(planned.state, "planned")
        self.truck.invalidate_recordset()
        self.assertEqual(self.truck.future_operator_id, self.other_driver)
        self.assertEqual(self.truck.date_future_operator, self.now + timedelta(days=3))
        self.assertIn(
            self.truck,
            self.truck.search([("future_operator_id", "=", self.other_driver.id)]),
        )
        with self.assertRaises(UserError):
            self.truck.write(
                {
                    "future_operator_id": self.driver.id,
                    "date_future_operator": self.now - timedelta(days=1),
                }
            )

    def test_ending_custody_ends_the_live_and_voids_the_planned(self):
        live = self._assign()
        planned = self._assign(
            assignee=self.other_driver, date_start=self.now + timedelta(days=3)
        )
        self.truck._end_custody(self.now)
        self.assertEqual(live.date_end, self.now)
        self.assertEqual(planned.date_end, planned.date_start)
        self.assertFalse(self.Assignment._search_custody(self.truck))
        self.assertFalse(self.Assignment._search_custody(self.truck, when="planned"))

    def test_open_ended_custody_books_nothing(self):
        assignment = self._assign()
        self.assertFalse(assignment.reservation_ids)

    def test_bounded_custody_books_the_resource(self):
        assignment = self._assign(date_end=self.now + timedelta(days=3))
        self.assertRecordValues(
            assignment.reservation_ids,
            [
                {
                    "resource_id": self.truck.id,
                    "date_start": self.now - timedelta(days=1),
                    "date_end": self.now + timedelta(days=3),
                    "allocated_percentage": 100.0,
                    "enforcement_mode": "soft",
                    "res_model": "resource.assignment",
                }
            ],
        )
        assignment.date_end = False
        self.assertFalse(assignment.reservation_ids)

    def test_two_bounded_custodies_overlap_as_a_warning(self):
        first = self._assign(date_end=self.now + timedelta(days=3))
        second = self._assign(
            assignee=self.other_driver, date_end=self.now + timedelta(days=2)
        )
        (first | second).invalidate_recordset(["schedule_overlap_count"])
        self.assertEqual(first.schedule_overlap_count, 1)
        self.assertEqual(second.schedule_overlap_count, 1)

    def test_capacity_above_one_divides_the_booked_share(self):
        room = self.env["resource.resource"].create(
            {"name": "Room 4", "resource_type": "material", "tz": "UTC", "capacity": 4}
        )
        assignments = self.Assignment.create(
            [
                {
                    "resource_id": room.id,
                    "assignee_id": assignee.id,
                    "custody_role": "custodian",
                    "date_start": self.now - timedelta(days=1),
                    "date_end": self.now + timedelta(days=3),
                }
                for assignee in (self.driver, self.other_driver)
            ]
        )
        self.assertEqual(
            assignments.reservation_ids.mapped("allocated_percentage"), [25.0, 25.0]
        )
        assignments.invalidate_recordset(["schedule_overlap_count"])
        self.assertEqual(assignments.mapped("schedule_overlap_count"), [0, 0])

    def test_a_loan_conflicts_with_a_planned_shift_on_the_ledger(self):
        loan = self._assign(date_end=self.now + timedelta(days=3))
        self.Reservation.create(
            {
                "name": "Shift",
                "resource_id": self.truck.id,
                "date_start": self.now,
                "date_end": self.now + timedelta(hours=8),
                "res_model": "res.partner",
                "res_id": 1,
            }
        )
        loan.invalidate_recordset(["schedule_overlap_count"])
        self.assertEqual(loan.schedule_overlap_count, 1)

    def test_only_a_human_can_hold(self):
        machine = self.env["resource.resource"].create(
            {"name": "Press", "resource_type": "material", "tz": "UTC"}
        )
        with self.assertRaises(ValidationError):
            self._assign(assignee=machine)
        with self.assertRaises(ValidationError):
            self.Assignment.create(
                {
                    "resource_id": self.driver.id,
                    "assignee_id": self.driver.id,
                    "date_start": self.now,
                }
            )

    def test_cross_company_assignee_is_rejected(self):
        other_company = self.env["res.company"].create({"name": "Other Co"})
        foreign_driver = (
            self.env["resource.resource"]
            .with_company(other_company)
            .create(
                {
                    "name": "Foreign",
                    "resource_type": "user",
                    "tz": "UTC",
                    "company_id": other_company.id,
                }
            )
        )
        with self.assertRaises(UserError):
            self._assign(assignee=foreign_driver)

    def test_end_before_start_is_rejected(self):
        from odoo.tools import mute_logger

        with self.assertRaises(Exception), mute_logger("odoo.sql_db", "odoo.db.cursor"):
            with self.env.cr.savepoint():
                self._assign(date_end=self.now - timedelta(days=2))

    def test_archiving_releases_the_booking(self):
        assignment = self._assign(date_end=self.now + timedelta(days=3))
        assignment.action_archive()
        self.assertFalse(self.Reservation.search([("resource_id", "=", self.truck.id)]))
        assignment.action_unarchive()
        self.assertEqual(
            self.Reservation.search_count([("resource_id", "=", self.truck.id)]), 1
        )

    def test_a_held_resource_cannot_be_deleted(self):
        from odoo.tools import mute_logger

        self._assign(date_end=self.now + timedelta(days=3))
        with (
            self.assertRaises(Exception),
            mute_logger("odoo.sql_db", "odoo.db.cursor"),
            self.env.cr.savepoint(),
        ):
            self.truck.unlink()

    def test_deleting_the_assignment_releases_the_booking(self):
        assignment = self._assign(date_end=self.now + timedelta(days=3))
        assignment_id = assignment.id
        assignment.unlink()
        self.assertFalse(
            self.Reservation.search(
                [
                    ("res_model", "=", "resource.assignment"),
                    ("res_id", "=", assignment_id),
                ]
            )
        )

    def test_anyone_can_hold_by_their_contact(self):
        contractor = self.env["res.partner"].create({"name": "Outside Mechanic"})
        assignment = self.Assignment.create(
            {
                "resource_id": self.truck.id,
                "assignee_partner_id": contractor.id,
                "custody_role": "technician",
            }
        )
        self.assertEqual(assignment.assignee_partner_id, contractor)
        self.assertEqual(assignment.assignee_id.partner_id, contractor)
        self.assertEqual(assignment.assignee_id.resource_type, "user")
        self.assertEqual(assignment.assignee_id.company_id, self.truck.company_id)
        self.assertEqual(self.truck.holder_id, assignment.assignee_id)

    def test_a_contact_who_is_a_resource_holds_with_that_resource(self):
        assignment = self.Assignment.create(
            {
                "resource_id": self.truck.id,
                "assignee_partner_id": self.driver.partner_id.id,
            }
        )
        self.assertEqual(assignment.assignee_id, self.driver)

    def test_one_person_twice_in_a_batch_is_one_resource(self):
        renter = self.env["res.partner"].create({"name": "Weekend Renter"})
        van = self.env["resource.resource"].create(
            {"name": "Van 3", "resource_type": "material", "tz": "UTC"}
        )
        first, second = self.Assignment.create(
            [
                {"resource_id": self.truck.id, "assignee_partner_id": renter.id},
                {"resource_id": van.id, "assignee_partner_id": renter.id},
            ]
        )
        self.assertEqual(first.assignee_id, second.assignee_id)
        self.assertEqual(renter.resource_ids, first.assignee_id)

    def test_changing_the_holder_by_contact(self):
        assignment = self._assign()
        assignment.assignee_partner_id = self.other_driver.partner_id
        self.assertEqual(assignment.assignee_id, self.other_driver)
        newcomer = self.env["res.partner"].create({"name": "Newcomer"})
        assignment.assignee_partner_id = newcomer
        self.assertEqual(assignment.assignee_id.partner_id, newcomer)
