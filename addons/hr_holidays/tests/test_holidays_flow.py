import time
from datetime import date, datetime

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from psycopg import IntegrityError

from odoo import Command
from odoo.tools import date_utils, mute_logger

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestHolidaysFlow(TestHrHolidaysCommon):
    @mute_logger("odoo.addons.base.models.ir_model", "odoo.models")
    def test_00_leave_request_flow_unlimited(self):
        Requests = self.env["hr.leave"]
        HolidaysStatus = self.env["hr.leave.type"]

        HolidayStatusManagerGroup = HolidaysStatus.with_user(self.user_hrmanager_id)
        HolidayStatusManagerGroup.create(
            {
                "name": "WithMeetingType",
                "requires_allocation": False,
            }
        )
        self.holidays_status_hr = HolidayStatusManagerGroup.create(
            {
                "name": "NotLimitedHR",
                "requires_allocation": False,
                "leave_validation_type": "hr",
            }
        )
        self.holidays_status_manager = HolidayStatusManagerGroup.create(
            {
                "name": "NotLimitedManager",
                "requires_allocation": False,
                "leave_validation_type": "manager",
            }
        )

        HolidaysEmployeeGroup = Requests.with_user(self.user_employee_id)

        leave_date = date_utils.start_of((date.today() - relativedelta(days=1)), "week")
        hol1_employee_group = HolidaysEmployeeGroup.create(
            {
                "name": "Hol11",
                "employee_id": self.employee_emp_id,
                "holiday_status_id": self.holidays_status_hr.id,
                "request_date_from": leave_date,
                "request_date_to": leave_date,
            }
        )
        hol1_user_group = hol1_employee_group.with_user(self.user_hruser_id)
        hol1_manager_group = hol1_employee_group.with_user(self.user_hrmanager_id)
        self.assertEqual(
            hol1_user_group.state,
            "confirm",
            "hr_holidays: newly created leave request should be in confirm state",
        )

        hol1_user_group.action_approve()
        self.assertEqual(
            hol1_manager_group.state,
            "validate",
            "hr_holidays: validated leave request should be in validate state",
        )

        leave_date = date_utils.start_of(date.today() + relativedelta(days=11), "week")
        hol12_employee_group = HolidaysEmployeeGroup.create(
            {
                "name": "Hol12",
                "employee_id": self.employee_emp_id,
                "holiday_status_id": self.holidays_status_manager.id,
                "request_date_from": leave_date,
                "request_date_to": leave_date,
            }
        )
        hol12_user_group = hol12_employee_group.with_user(self.user_hruser_id)
        hol12_manager_group = hol12_employee_group.with_user(self.user_hrmanager_id)
        self.assertEqual(
            hol12_user_group.state,
            "confirm",
            "hr_holidays: newly created leave request should be in confirm state",
        )

        hol12_manager_group.action_approve()
        self.assertEqual(
            hol1_user_group.state,
            "validate",
            "hr_holidays: validates leave request should be in validate state",
        )

    @mute_logger("odoo.addons.base.models.ir_model", "odoo.models")
    def test_01_leave_request_flow_limited(self):
        with freeze_time("2022-01-15"):
            Requests = self.env["hr.leave"]
            Allocations = self.env["hr.leave.allocation"]
            HolidaysStatus = self.env["hr.leave.type"]

            self.env.ref("hr.employee_admin").tz = "Europe/Brussels"

            holiday_status_paid_time_off = self.env["hr.leave.type"].create(
                {
                    "name": "Paid Time Off",
                    "requires_allocation": True,
                    "employee_requests": False,
                    "allocation_validation_type": "hr",
                    "leave_validation_type": "both",
                    "responsible_ids": [
                        Command.link(self.env.ref("base.user_admin").id)
                    ],
                }
            )

            self.env["hr.leave.allocation"].create(
                [
                    {
                        "name": "Paid Time off for David",
                        "holiday_status_id": holiday_status_paid_time_off.id,
                        "number_of_days": 20,
                        "employee_id": self.employee_emp_id,
                        "state": "confirm",
                        "date_from": time.strftime("%Y-%m-01"),
                    },
                    {
                        "name": "Paid Time off for Admin",
                        "holiday_status_id": holiday_status_paid_time_off.id,
                        "number_of_days": 20,
                        "employee_id": self.ref("hr.employee_admin"),
                        "state": "confirm",
                        "date_from": time.strftime("%Y-%m-01"),
                    },
                ]
            ).action_approve()

            def _check_holidays_status(holiday_status, employee, ml, lt, rl, vrl):
                result = holiday_status.get_allocation_data(employee)[employee][0][1]
                self.assertEqual(
                    result["max_leaves"], ml, "hr_holidays: wrong type days computation"
                )
                self.assertEqual(
                    result["leaves_taken"],
                    lt,
                    "hr_holidays: wrong type days computation",
                )
                self.assertEqual(
                    result["remaining_leaves"],
                    rl,
                    "hr_holidays: wrong type days computation",
                )
                self.assertEqual(
                    result["virtual_remaining_leaves"],
                    vrl,
                    "hr_holidays: wrong type days computation",
                )

            HolidayStatusManagerGroup = HolidaysStatus.with_user(self.user_hrmanager_id)
            HolidayStatusManagerGroup.create(
                {
                    "name": "WithMeetingType",
                    "requires_allocation": False,
                }
            )

            self.holidays_status_limited = HolidayStatusManagerGroup.create(
                {
                    "name": "Limited",
                    "requires_allocation": True,
                    "employee_requests": False,
                    "allocation_validation_type": "hr",
                    "leave_validation_type": "both",
                    "responsible_ids": [
                        Command.link(self.env.ref("base.user_admin").id)
                    ],
                }
            )
            HolidaysEmployeeGroup = Requests.with_user(self.user_employee_id)

            aloc1_user_group = Allocations.with_user(self.user_hruser_id).create(
                {
                    "name": "Days for limited category",
                    "employee_id": self.employee_emp_id,
                    "holiday_status_id": self.holidays_status_limited.id,
                    "number_of_days": 2,
                    "state": "confirm",
                    "date_from": time.strftime("%Y-%m-01"),
                }
            )
            self.env.flush_all()

            aloc1_user_group.with_user(self.user_hrmanager_id).action_approve()
            hol_status_2_employee_group = self.holidays_status_limited.with_user(
                self.user_employee_id
            )
            _check_holidays_status(
                hol_status_2_employee_group, self.employee_emp, 2.0, 0.0, 2.0, 2.0
            )

            hol2 = HolidaysEmployeeGroup.create(
                {
                    "name": "Hol22",
                    "employee_id": self.employee_emp_id,
                    "holiday_status_id": self.holidays_status_limited.id,
                    "request_date_from": (date.today() + relativedelta(days=2)),
                    "request_date_to": (date.today() + relativedelta(days=2)),
                }
            )
            self.env.flush_all()
            hol2_user_group = hol2.with_user(self.user_hruser_id)
            hol_status_2_employee_group.invalidate_model()
            _check_holidays_status(
                hol_status_2_employee_group, self.employee_emp, 2.0, 0.0, 2.0, 1.0
            )

            hol2_user_group.with_user(self.user_hrmanager_id).action_approve()
            self.assertEqual(
                hol2.state,
                "validate",
                "hr_holidays: second validation should lead to validate state",
            )
            hol_status_2_employee_group.invalidate_model(["max_leaves", "leaves_taken"])
            _check_holidays_status(
                hol_status_2_employee_group, self.employee_emp, 2.0, 1.0, 1.0, 1.0
            )

            hol2.with_user(self.user_hrmanager_id).action_refuse()
            self.assertEqual(
                hol2.state, "refuse", "hr_holidays: refuse should lead to refuse state"
            )

            hol_status_2_employee_group.invalidate_model(["max_leaves"])
            _check_holidays_status(
                hol_status_2_employee_group, self.employee_emp, 2.0, 0.0, 2.0, 2.0
            )

            self.assertEqual(
                hol2.state,
                "refuse",
                "hr_holidays: hr_user should not be able to reset a refused leave request",
            )

            employee_id = self.ref("hr.employee_admin")
            hol3_status = holiday_status_paid_time_off.with_context(
                employee_id=employee_id
            )
            hol3 = Requests.create(
                {
                    "name": "Sick Time Off",
                    "holiday_status_id": hol3_status.id,
                    "request_date_from": date.today() + relativedelta(day=10),
                    "request_date_to": date.today() + relativedelta(day=10),
                    "employee_id": employee_id,
                    "number_of_days": 1,
                }
            )
            hol3.action_refuse()
            self.assertEqual(
                hol3.state, "refuse", "hr_holidays: refuse should lead to refuse state"
            )
            hol3.action_approve()
            self.assertEqual(
                hol3.state,
                "validate",
                "hr_holidays: validation should lead to validate state",
            )
            _check_holidays_status(
                hol3_status,
                self.env["hr.employee"].browse(employee_id),
                20.0,
                1.0,
                19.0,
                19.0,
            )

    def test_10_leave_summary_reports(self):
        admin_emp = self.env.ref("hr.employee_admin")
        self.env.company.report_config_id.external_report_layout_id = self.env.ref(
            "web.external_layout_standard"
        ).id

        wizard = (
            self.env["hr.holidays.summary.employee"]
            .with_context(
                active_ids=admin_emp.ids,
                active_model="hr.employee",
            )
            .create(
                {
                    "date_from": datetime.today().strftime("%Y-%m-01"),
                    "emp": [Command.set(admin_emp.ids)],
                    "holiday_type": "Approved",
                }
            )
        )

        action = wizard.print_report()

        self.assertEqual(action["type"], "ir.actions.report")
        self.assertEqual(action["report_name"], "hr_holidays.report_holidayssummary")
        self.assertEqual(action["report_type"], "qweb-pdf")
        self.assertIn("form", action["data"])
        self.assertEqual(action["data"]["form"]["holiday_type"], "Approved")
        self.assertEqual(action["data"]["form"]["emp"], admin_emp.ids)

    def test_sql_constraint_dates(self):

        holiday_status_paid_time_off = self.env["hr.leave.type"].create(
            {
                "name": "Paid Time Off",
                "requires_allocation": True,
                "employee_requests": False,
                "allocation_validation_type": "hr",
                "leave_validation_type": "both",
                "responsible_ids": [Command.link(self.env.ref("base.user_admin").id)],
            }
        )

        self.env["hr.leave.allocation"].create(
            {
                "name": "Paid Time off for David",
                "holiday_status_id": holiday_status_paid_time_off.id,
                "number_of_days": 20,
                "employee_id": self.ref("hr.employee_admin"),
                "state": "confirm",
                "date_from": time.strftime("%Y-%m-01"),
                "date_to": time.strftime("%Y-12-31"),
            }
        ).action_approve()

        leave_vals = {
            "name": "Sick Time Off",
            "holiday_status_id": holiday_status_paid_time_off.id,
            "request_date_from": date.today() + relativedelta(day=11),
            "request_date_to": date.today() + relativedelta(day=10),
            "employee_id": self.ref("hr.employee_admin"),
        }
        with mute_logger("odoo.db"), self.assertRaises(IntegrityError):
            self.env["hr.leave"].create(leave_vals)

        leave_vals = {
            "name": "Sick Time Off",
            "holiday_status_id": holiday_status_paid_time_off.id,
            "request_date_from": date.today() + relativedelta(day=10),
            "request_date_to": date.today() + relativedelta(day=11),
            "employee_id": self.ref("hr.employee_admin"),
        }
        leave = self.env["hr.leave"].create(leave_vals)

        with mute_logger("odoo.db"), self.assertRaises(IntegrityError):
            leave.write(
                {
                    "request_date_from": date.today() + relativedelta(day=11),
                    "request_date_to": date.today() + relativedelta(day=10),
                }
            )
