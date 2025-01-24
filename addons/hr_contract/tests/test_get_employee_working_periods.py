# Part of Odoo. See LICENSE file for full copyright and licensing details
from datetime import datetime
import json

from odoo import fields

from .common import TestContractCommon


class TestEmployeeWorkingPeriods(TestContractCommon):
    """
        The goal is check if the method correctly filters contracts.
        Test Goals -
        1). Contract in State "draft" is only chosen if its kanban_state is in "done"
        2). Contracts in States "open" and "close" are chosen regardless of the kanban_state
        3). Any other type of combination is not accepted and takes its working period as default scale time
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.tz = 'UTC'

        cls.contract_start_date = "2024-08-15 00:00:00"
        cls.contract_end_date = "2024-08-16 23:59:59"

        cls.calendar_bali = cls.env['resource.calendar'].create({'name': 'Bali\'s Calendar'})

        cls.dates_inside_contracts = {
            "start": "2024-08-11 10:00:00",
            "end": "2024-08-17 19:00:00",
        }
        cls.dates_outside_contracts = {
            "start": "2024-08-18 10:00:00",
            "end": "2024-08-24 19:00:00",
        }

        cls.employee_bali = cls.env['hr.employee'].create({
            'name': 'Richard',
            'gender': 'male',
            'country_id': cls.env.ref('base.be').id,
        })

        cls.employee_bali.contract_id = cls.env["hr.contract"].create({
            "date_start": fields.Date.to_date(cls.contract_start_date),
            "date_end": fields.Date.to_date(cls.contract_end_date),
            "name": "contract for Joseph",
            "resource_calendar_id": cls.calendar_bali.id,
            "wage": 5000.0,
            "employee_id": cls.employee_bali.id,
            "state": "draft",
            "kanban_state": "normal",
        })

    def get_employee_working_periods(self, employee_ids, start, stop):
        return self.env["hr.contract"].get_employee_working_periods(employee_ids, start, stop)

    def test_case_no_contract(self):
        """ Check the calendar set on the employee will be given as working days when the resource has no contract. """
        employee_rows = self.get_employee_working_periods(self.employee.ids, self.dates_inside_contracts["start"], self.dates_inside_contracts["end"])
        working_periods = employee_rows[self.employee.id]["working_periods"]

        self.assertEqual(len(working_periods), 1)
        self.assertDictEqual(
            working_periods[0],
            {'start': self.dates_inside_contracts['start'], 'end': self.dates_inside_contracts['end']},
            "The working period for that resource should be the whole gantt periods displayed."
        )

    def test_with_draft_contract(self):
        """ Check the working schedule defined on the calendar set to the resource will be taken into account when the
            resource has not yet a contract running/ready

            Create contract in draft and the kanban state set to "in progress"
        """
        employee_rows = self.get_employee_working_periods(self.employee_bali.ids, self.dates_inside_contracts["start"], self.dates_inside_contracts["end"])
        working_periods = employee_rows[self.employee_bali.id]['working_periods']
        self.assertEqual(len(working_periods), 1)
        self.assertDictEqual(
            working_periods[0],
            {'start': self.dates_inside_contracts['start'], 'end': self.dates_inside_contracts['end']},
            "The working period for that resource should be the whole gantt periods displayed."
        )

    def test_with_draft_contract_blocked(self):
        """ Check the working schedule defined on the calendar set to the resource will be taken into account when the
            resource has not yet a contract running/ready

            Create contract in draft and the kanban state set to "blocked"
        """
        self.employee_bali.contract_id.kanban_state = "blocked"
        self.assertEqual(self.employee_bali.contract_id.state, "draft")
        employee_rows = self.get_employee_working_periods(self.employee_bali.ids, self.dates_inside_contracts["start"], self.dates_inside_contracts["end"])
        working_periods = employee_rows[self.employee_bali.id]['working_periods']
        self.assertEqual(len(working_periods), 1)
        self.assertDictEqual(
            working_periods[0],
            {'start': self.dates_inside_contracts['start'], 'end': self.dates_inside_contracts['end']},
            "The working period for that resource should be the whole gantt periods displayed."
        )

    def test_with_draft_contract_ready(self):
        """ Check the working period is only inside the contract created for the resource

            Create a contract in draft but ready in a certain period.
        """
        self.employee_bali.contract_id.kanban_state = "done"
        self.assertEqual(self.employee_bali.contract_id.state, "draft")

        employee_rows = self.get_employee_working_periods(self.employee_bali.ids, self.dates_inside_contracts["start"], self.dates_inside_contracts["end"])
        working_periods = employee_rows[self.employee_bali.id]['working_periods']
        self.assertEqual(len(working_periods), 1)
        self.assertDictEqual(
            working_periods[0],
            {'start': self.contract_start_date, 'end': self.contract_end_date},
            "The working period for that resource should be the contract period only."
        )

        employee_rows = self.get_employee_working_periods(self.employee_bali.ids, self.dates_outside_contracts["start"], self.dates_outside_contracts["end"])
        working_periods = employee_rows[self.employee_bali.id]['working_periods']
        self.assertFalse(working_periods, "No working period should be found since the contract period is before the period displayed in the gantt view.")

        self.employee_bali.contract_id.date_end = False
        employee_rows = self.get_employee_working_periods(self.employee_bali.ids, self.dates_outside_contracts["start"], self.dates_outside_contracts["end"])
        working_periods = employee_rows[self.employee_bali.id]['working_periods']
        self.assertDictEqual(
            working_periods[0],
            {'start': self.contract_start_date, 'end': False},
            "The working period for that resource should be the whole gantt periods displayed since it is inside the contract period."
        )

    def test_with_running_contract(self):
        """ Check the working period is only inside the contract running of the resource

            Create a running contract (state = "open")
        """
        self.employee_bali.contract_id.state = "open"
        employee_rows = self.get_employee_working_periods(self.employee_bali.ids, self.dates_inside_contracts["start"], self.dates_inside_contracts["end"])
        working_periods = employee_rows[self.employee_bali.id]['working_periods']
        self.assertEqual(len(working_periods), 1)
        self.assertDictEqual(
            working_periods[0],
            {'start': self.contract_start_date, 'end': self.contract_end_date},
            "The working period for that resource should be the contract period only."
        )

        employee_rows = self.get_employee_working_periods(self.employee_bali.ids, self.dates_outside_contracts["start"], self.dates_outside_contracts["end"])
        working_periods = employee_rows[self.employee_bali.id]['working_periods']
        self.assertFalse(working_periods, "No working period should be found since the period displayed in the gantt view is after the contract period.")

        self.assertEqual(
            employee_rows[self.employee_bali.id]["working_periods"],
            [],
            "The resource working_periods should be empty with a contract in open state outside contract period in context date",
        )

        self.employee_bali.contract_id.date_end = False
        employee_rows = self.get_employee_working_periods(self.employee_bali.ids, self.dates_outside_contracts["start"], self.dates_outside_contracts["end"])
        working_periods = employee_rows[self.employee_bali.id]['working_periods']
        self.assertDictEqual(
            working_periods[0],
            {'start': self.contract_start_date, 'end': False},
            "The working period for that resource should be the whole gantt periods displayed since it is inside the contract period."
        )

    def test_with_contract_closed(self):
        """ Check the working period is only inside the contract period of the resource

            Create contract with state "close"
        """
        self.employee_bali.contract_id.state = "close"

        # If context dates are in contract start and end then we get working_periods as
        # contract start and end date
        employee_rows = self.get_employee_working_periods(self.employee_bali.ids, self.dates_inside_contracts["start"], self.dates_inside_contracts["end"])
        working_periods = employee_rows[self.employee_bali.id]['working_periods']
        self.assertEqual(len(working_periods), 1)
        self.assertDictEqual(
            working_periods[0],
            {'start': self.contract_start_date, 'end': self.contract_end_date},
            "The working period for that resource should be the contract period only."
        )

        # If context dates are not in contract start and end then we get working_periods as
        # contract start and end date
        employee_rows = self.get_employee_working_periods(self.employee_bali.ids, self.dates_outside_contracts["start"], self.dates_outside_contracts["end"])
        working_periods = employee_rows[self.employee_bali.id]['working_periods']
        self.assertFalse(working_periods, "No working period should be found since the gantt period is outside ")
        self.employee_bali.contract_id.date_end = False
        employee_rows = self.get_employee_working_periods(self.employee_bali.ids, self.dates_outside_contracts["start"], self.dates_outside_contracts["end"])
        working_periods = employee_rows[self.employee_bali.id]['working_periods']
        self.assertDictEqual(
            working_periods[0],
            {'start': self.contract_start_date, 'end': False},
            "The working period for that resource should be the whole gantt periods displayed since it is inside the contract period."
        )

    def test_with_cancelled_contract(self):
        self.employee_bali.contract_id.state = "cancel"

        employee_rows = self.get_employee_working_periods(self.employee_bali.ids, self.dates_inside_contracts["start"], self.dates_inside_contracts["end"])
        working_periods = employee_rows[self.employee_bali.id]['working_periods']
        self.assertEqual(len(working_periods), 1)
        self.assertDictEqual(
            working_periods[0],
            {'start': self.dates_inside_contracts['start'], 'end': self.dates_inside_contracts['end']},
            "The working period for that resource should be the whole gantt periods displayed."
        )

        self.env['hr.contract'].create({
            "date_start": datetime(2024, 1, 1).date(),
            "date_end": datetime(2024, 7, 31).date(),
            "name": "contract for Joseph",
            "resource_calendar_id": self.calendar_bali.id,
            "wage": 4500.0,
            "employee_id": self.employee_bali.id,
            "state": "close",
            "kanban_state": "normal",
        })

        employee_rows = self.get_employee_working_periods(self.employee_bali.ids, self.dates_outside_contracts["start"], self.dates_outside_contracts["end"])
        working_periods = employee_rows[self.employee_bali.id]['working_periods']
        self.assertFalse(working_periods)
