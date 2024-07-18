# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo.exceptions import ValidationError
from odoo.addons.hr_contract.tests.common import TestContractCommon
from odoo.tests import tagged
from odoo.tests import Form

@tagged('test_contracts')
class TestHrContracts(TestContractCommon):

    @classmethod
    def setUpClass(cls):
        super(TestHrContracts, cls).setUpClass()
        cls.contracts = cls.env['hr.contract'].with_context(tracking_disable=True)

    def create_contract(self, state, kanban_state, start, end=None):
        return self.env['hr.contract'].create({
            'name': 'Contract',
            'employee_id': self.employee.id,
            'state': state,
            'kanban_state': kanban_state,
            'wage': 1,
            'date_start': start,
            'date_end': end,
        })

    def test_incoming_overlapping_contract(self):
        start = datetime.strptime('2015-11-01', '%Y-%m-%d').date()
        end = datetime.strptime('2015-11-30', '%Y-%m-%d').date()
        self.create_contract('open', 'normal', start, end)

        # Incoming contract
        with self.assertRaises(ValidationError, msg="It should not create two contract in state open or incoming"):
            start = datetime.strptime('2015-11-15', '%Y-%m-%d').date()
            end = datetime.strptime('2015-12-30', '%Y-%m-%d').date()
            self.create_contract('draft', 'done', start, end)

    def test_pending_overlapping_contract(self):
        start = datetime.strptime('2015-11-01', '%Y-%m-%d').date()
        end = datetime.strptime('2015-11-30', '%Y-%m-%d').date()
        self.create_contract('open', 'normal', start, end)

        # Pending contract
        with self.assertRaises(ValidationError, msg="It should not create two contract in state open or pending"):
            start = datetime.strptime('2015-11-15', '%Y-%m-%d').date()
            end = datetime.strptime('2015-12-30', '%Y-%m-%d').date()
            self.create_contract('open', 'blocked', start, end)

        # Draft contract -> should not raise
        start = datetime.strptime('2015-11-15', '%Y-%m-%d').date()
        end = datetime.strptime('2015-12-30', '%Y-%m-%d').date()
        self.create_contract('draft', 'normal', start, end)

    def test_draft_overlapping_contract(self):
        start = datetime.strptime('2015-11-01', '%Y-%m-%d').date()
        end = datetime.strptime('2015-11-30', '%Y-%m-%d').date()
        self.create_contract('open', 'normal', start, end)

        # Draft contract -> should not raise even if overlapping
        start = datetime.strptime('2015-11-15', '%Y-%m-%d').date()
        end = datetime.strptime('2015-12-30', '%Y-%m-%d').date()
        self.create_contract('draft', 'normal', start, end)

    def test_overlapping_contract_no_end(self):

        # No end date
        self.create_contract('open', 'normal', datetime.strptime('2015-11-01', '%Y-%m-%d').date())

        with self.assertRaises(ValidationError):
            start = datetime.strptime('2015-11-15', '%Y-%m-%d').date()
            end = datetime.strptime('2015-12-30', '%Y-%m-%d').date()
            self.create_contract('draft', 'done', start, end)

    def test_overlapping_contract_no_end2(self):

        start = datetime.strptime('2015-11-01', '%Y-%m-%d').date()
        end = datetime.strptime('2015-12-30', '%Y-%m-%d').date()
        self.create_contract('open', 'normal', start, end)

        with self.assertRaises(ValidationError):
            # No end
            self.create_contract('draft', 'done', datetime.strptime('2015-01-01', '%Y-%m-%d').date())

    def test_set_employee_contract_create(self):
        contract = self.create_contract('open', 'normal', date(2018, 1, 1), date(2018, 1, 2))
        self.assertEqual(self.employee.contract_id, contract)

    def test_set_employee_contract_write(self):
        contract = self.create_contract('draft', 'normal', date(2018, 1, 1), date(2018, 1, 2))
        contract.state = 'open'
        self.assertEqual(self.employee.contract_id, contract)

    def test_first_contract_date(self):
        self.create_contract('open', 'normal', date(2018, 1, 1), date(2018, 1, 31))
        self.assertEqual(self.employee.first_contract_date, date(2018, 1, 1))

        # New contract, no gap
        self.create_contract('open', 'normal', date(2017, 1, 1), date(2017, 12, 31))
        self.assertEqual(self.employee.first_contract_date, date(2017, 1, 1))

        # New contract, with gap
        self.create_contract('open', 'normal', date(2016, 1, 1), date(2016, 1, 31))
        self.assertEqual(self.employee.first_contract_date, date(2017, 1, 1))

    def test_current_contract_stage_change(self):
        today = date.today()
        contract = self.create_contract('open', 'normal', today + relativedelta(day=1), today + relativedelta(day=31))
        self.assertEqual(self.employee.contract_id, contract)

        draft_contract = self.create_contract('draft', 'normal', today + relativedelta(months=1, day=1), today + relativedelta(months=1, day=31))
        draft_contract.state = 'open'
        self.assertEqual(self.employee.contract_id, draft_contract)

        draft_contract.state = 'draft'
        self.assertEqual(self.employee.contract_id, contract)

    def test_copy_employee_contract_create(self):
        contract = self.create_contract('open', 'normal', date(2018, 1, 1), date(2018, 1, 2))
        duplicate_employee = self.employee.copy()
        self.assertNotEqual(duplicate_employee.contract_id, contract)

    def test_contract_calendar_update(self):
        """
        Ensure the employee's working schedule updates after modifying them on
        their contract, as well as well as the working schedule linked to the
        employee's leaves iff they fall under the active contract duration.
        """
        contract1 = self.create_contract('close', 'done', date(2024, 1, 1), date(2024, 5, 31))
        contract2 = self.create_contract('open', 'normal', date(2024, 6, 1))

        calendar1 = contract1.resource_calendar_id
        calendar2 = self.env['resource.calendar'].create({'name': 'Test Schedule'})

        leave1 = self.env['resource.calendar.leaves'].create({
            'name': 'Sick day',
            'resource_id': self.employee.resource_id.id,
            'calendar_id': calendar1.id,
            'date_from': datetime(2024, 5, 2, 8, 0),
            'date_to': datetime(2024, 5, 2, 17, 0),
        })
        leave2 = self.env['resource.calendar.leaves'].create({
            'name': 'Sick again',
            'resource_id': self.employee.resource_id.id,
            'calendar_id': calendar1.id,
            'date_from': datetime(2024, 7, 5, 8, 0),
            'date_to': datetime(2024, 7, 5, 17, 0),
        })

        contract2.resource_calendar_id = calendar2

        self.assertEqual(
            self.employee.resource_calendar_id,
            calendar2,
            "Employee calendar should update",
        )
        self.assertEqual(
            leave1.calendar_id,
            calendar1,
            "Leave under previous calendar should not update",
        )
        self.assertEqual(
            leave2.calendar_id,
            calendar2,
            "Leave under active contract should update",
        )

    def test_running_contract_updates_employee_job_info(self):
        employee = self.env['hr.employee'].create({
            'name': 'John Doe'
        })
        job = self.env['hr.job'].create({
            'name': 'Software dev'
        })
        department = self.env['hr.department'].create({
            'name': 'R&D'
        })

        contract_form = Form(self.env['hr.contract'].create({
            'name': 'Contract',
            'employee_id': employee.id,
            'hr_responsible_id': self.env.uid,
            'job_id': job.id,
            'department_id': department.id,
            'wage': 1,
        }))

        contract_form.save()
        self.assertFalse(employee.job_id)
        self.assertFalse(employee.job_title)
        self.assertFalse(employee.department_id)

        contract_form.state = 'open'
        contract_form.save()
        self.assertEqual(contract_form.job_id, employee.job_id)
        self.assertEqual(contract_form.job_id.name, employee.job_title)
        self.assertEqual(contract_form.department_id, employee.department_id)
