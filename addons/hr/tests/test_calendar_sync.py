from psycopg import IntegrityError

from odoo.fields import Date, Datetime
from odoo.tests import Form

from odoo.addons.hr.tests.common import TestHrCommon


class TestContractCalendars(TestHrCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar_richard = cls.env["resource.calendar"].create(
            {"name": "Calendar of Richard"}
        )
        cls.employee.resource_calendar_id = cls.calendar_richard
        cls.employee.version_id.date_version = Date.to_date("2015-01-01")

        cls.calendar_35h = cls.env["resource.calendar"].create({"name": "35h calendar"})

        cls.contract_cdd_values = {
            "date_version": Date.to_date("2016-01-01"),
            "date_start": Date.to_date("2016-01-01"),
            "name": "First CDD Contract for Richard",
            "resource_calendar_id": cls.calendar_35h.id,
            "wage": 5000.0,
        }

        cls.contract_fully_flexible_values = {
            "date_version": Date.to_date("2017-01-01"),
            "date_start": Date.to_date("2017-01-01"),
            "name": "Fully Flexible Contract for Richard",
            "resource_calendar_id": False,
            "wage": 5000.0,
        }

    def test_contract_state_incoming_to_open(self):
        self.assertEqual(self.employee.resource_calendar_id, self.calendar_richard)
        cdd = self.employee.create_version(self.contract_cdd_values)
        self.assertEqual(
            self.employee.version_id.id,
            cdd.id,
            "The version of the employee should be updated to the last version.",
        )
        self.assertEqual(
            self.employee.resource_calendar_id,
            cdd.resource_calendar_id,
            "The employee should have the calendar of its contract.",
        )

    def test_set_fully_flexible_contract_should_change_resource_calendar(self):
        self.assertEqual(self.employee.resource_calendar_id, self.calendar_richard)
        flexijob = self.employee.create_version(self.contract_fully_flexible_values)
        self.assertEqual(
            self.employee.version_id.id,
            flexijob.id,
            "The version of the employee should be updated to the last version.",
        )
        self.assertFalse(
            self.employee.resource_calendar_id,
            "The employee should have a fully flexible calendar.",
        )

    def test_contract_transfer_leaves(self):

        def create_calendar_leave(start, end, resource=None):
            return self.env["resource.schedule.exception"].create(
                {
                    "name": "leave name",
                    "date_from": start,
                    "date_to": end,
                    "resource_id": resource.id if resource else None,
                    "calendar_id": self.employee.resource_calendar_id.id,
                }
            )

        start = Datetime.to_datetime("2015-11-17 07:00:00")
        end = Datetime.to_datetime("2015-11-20 18:00:00")
        leave1 = create_calendar_leave(start, end, resource=self.employee.resource_id)

        start = Datetime.to_datetime("2015-11-25 07:00:00")
        end = Datetime.to_datetime("2015-11-28 18:00:00")
        leave2 = create_calendar_leave(start, end, resource=self.employee.resource_id)

        start = Datetime.to_datetime("2015-11-25 07:00:00")
        end = Datetime.to_datetime("2015-11-28 18:00:00")
        leave3 = create_calendar_leave(start, end)

        self.calendar_richard._transfer_leaves_to_calendar(
            self.calendar_35h,
            resources=self.employee.resource_id,
            from_date=Date.to_date("2015-11-21"),
        )

        self.assertEqual(
            leave1.calendar_id,
            self.calendar_richard,
            "It should stay in Richard's calendar",
        )
        self.assertEqual(
            leave3.calendar_id,
            self.calendar_richard,
            "Global leave should stay in original calendar",
        )
        self.assertEqual(
            leave2.calendar_id,
            self.calendar_35h,
            "It should be transferred to the other calendar",
        )

        self.calendar_richard._transfer_leaves_to_calendar(
            self.calendar_35h, resources=None, from_date=Date.to_date("2015-11-21")
        )

        self.assertEqual(
            leave3.calendar_id, self.calendar_35h, "Global leave should be transfered"
        )

    def test_calendar_no_desync(self):
        self.employee.create_version(self.contract_cdd_values)
        self.assertEqual(self.employee.resource_calendar_id, self.calendar_35h)
        self.assertEqual(
            self.employee.version_id.resource_calendar_id, self.calendar_35h
        )
        self.assertEqual(
            self.employee.version_ids[0].resource_calendar_id, self.calendar_richard
        )
        calendar_38h = self.env["resource.calendar"].create({"name": "38h calendar"})
        self.employee.resource_calendar_id = calendar_38h
        self.assertEqual(self.employee.version_id.resource_calendar_id, calendar_38h)
        self.assertEqual(
            self.employee.version_ids[0].resource_calendar_id, self.calendar_richard
        )

    def test_the_resource_works_the_calendar_of_whichever_version_is_current(self):
        # the current version changes without any calendar being written: a
        # version is created and takes over, then goes away; the resource
        # follows each time, it is what every schedule reads
        resource = self.employee.resource_id
        self.assertEqual(resource.calendar_id, self.calendar_richard)
        cdd = self.employee.create_version(self.contract_cdd_values)
        self.assertEqual(self.employee.current_version_id, cdd)
        self.assertEqual(resource.calendar_id, self.calendar_35h)

        cdd.unlink()
        self.assertNotEqual(self.employee.current_version_id, cdd)
        self.assertEqual(
            self.employee.current_version_id.resource_calendar_id,
            self.calendar_richard,
        )
        self.assertEqual(
            resource.calendar_id,
            self.calendar_richard,
            "the resource works the calendar of the version that is current now",
        )

    def test_a_resource_is_never_shared_by_two_employees(self):
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.env["hr.employee"].create(
                {
                    "name": "Second employee on Richard's resource",
                    "resource_id": self.employee.resource_id.id,
                }
            )

    def test_employee_resource_contract_without_and_with_date_from(self):
        # The form collects a local day, not an instant: the exception's hours are
        # read in its own zone, so the field that carries a zone is not the one a
        # person types into.
        leave_form = Form(self.env["resource.schedule.exception"])
        leave_form.local_date_from = False

        leave_form.resource_id = self.employee.resource_id
        self.assertFalse(leave_form.calendar_id)

        leave_form.local_date_from = Date.to_date("2018-01-01")
        # Asserted on the saved record: the local day reaches `date_from` through an
        # inverse, which runs at save, so the contract covering the day is not known
        # while the form is still open. The form must therefore not offer the field
        # -- it would save the calendar it could not yet resolve.
        leave = leave_form.save()
        self.assertEqual(
            leave.calendar_id, self.employee.version_id.resource_calendar_id
        )
