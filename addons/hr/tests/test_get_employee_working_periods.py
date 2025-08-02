# Part of Odoo. See LICENSE file for full copyright and licensing details
from odoo import fields

from .common import TestHrCommon


class TestPlanningGanttResourceEmployeeWorkingPeriods(TestHrCommon):
    """
        Currently _get_employee_working_periods method supplies data to Gantt Model.
        The goal is check if the method correctly filters contracts.
        Test Goals -
        1). Contract in State "draft" is only chosen if its kanban_state is in "done"
        2). Contracts in States "open" and "close" are chosen regardless of the kanban_state
        3). Any other type of combination is not accepted and takes its working period as default scale time
        Here the context dates refer to dates we from gantt view through the RPC request sent. These refer to
        start date and end dates of the scale. If the scale is week, the starting date of week is default_start_datetime
        and end date if weeek is default_end_datetime.
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.tz = 'UTC'

        cls.contract_start_date = "2024-08-15 00:00:00"
        cls.contract_end_date = "2024-08-16 23:59:59"

        cls.context_dates_inside_contracts = {
            "start": fields.Datetime.to_datetime("2024-08-11 10:00:00"),
            "stop": fields.Datetime.to_datetime("2024-08-17 19:00:00"),
        }
        cls.context_dates_outside_contract = {
            "start": fields.Datetime.to_datetime("2024-08-18 10:00:00"),
            "stop": fields.Datetime.to_datetime("2024-08-24 19:00:00"),
        }

        cls.employee.version_id.write({
            "date_version": fields.Date.to_date(cls.contract_start_date),
            "contract_date_start": fields.Date.to_date(cls.contract_start_date),
            "contract_date_end": fields.Date.to_date(cls.contract_end_date),
            "name": "contract for Joseph",
            "wage": 5000.0,
        })

    def test_with_future_contract(self):
        """ Check the working period is only inside the contract created for the resource

            Create a contract in draft but ready in a certain period.
        """
        employee_rows = self.employee._get_employee_working_periods(**self.context_dates_inside_contracts)
        working_periods = employee_rows[self.employee.id]['working_periods']
        self.assertEqual(len(working_periods), 1)
        self.assertDictEqual(
            working_periods[0],
            {'start': self.contract_start_date, 'end': self.contract_end_date},
            "The working period for that resource should be the contract period only."
        )

        employee_rows = self.employee._get_employee_working_periods(**self.context_dates_outside_contract)
        working_periods = employee_rows[self.employee.id]['working_periods']
        self.assertFalse(working_periods, "No working period should be found since the contract period is before the period displayed in the gantt view.")

        self.employee.version_id.contract_date_end = False
        employee_rows = self.employee._get_employee_working_periods(**self.context_dates_outside_contract)
        working_periods = employee_rows[self.employee.id]['working_periods']
        self.assertDictEqual(
            working_periods[0],
            {'start': self.contract_start_date, 'end': False},
            "The working period for that resource should be the whole gantt periods displayed since it is inside the contract period."
        )

    def test_with_running_contract(self):
        """ Check the working period is only inside the contract running of the resource

            Create a running contract
        """
        employee_rows = self.employee._get_employee_working_periods(**self.context_dates_inside_contracts)
        working_periods = employee_rows[self.employee.id]['working_periods']
        self.assertEqual(len(working_periods), 1)
        self.assertDictEqual(
            working_periods[0],
            {'start': self.contract_start_date, 'end': self.contract_end_date},
            "The working period for that resource should be the contract period only."
        )

        employee_rows = self.employee._get_employee_working_periods(**self.context_dates_outside_contract)
        working_periods = employee_rows[self.employee.id]['working_periods']
        self.assertFalse(working_periods, "No working period should be found since the period displayed in the gantt view is after the contract period.")

        self.assertEqual(
            employee_rows[self.employee.id]["working_periods"],
            [],
            "The resource working_periods should be empty with a contract in open state outside contract period in context date",
        )

        self.employee.version_id.contract_date_end = False
        employee_rows = self.employee._get_employee_working_periods(**self.context_dates_outside_contract)
        working_periods = employee_rows[self.employee.id]['working_periods']
        self.assertDictEqual(
            working_periods[0],
            {'start': self.contract_start_date, 'end': False},
            "The working period for that resource should be the whole gantt periods displayed since it is inside the contract period."
        )
