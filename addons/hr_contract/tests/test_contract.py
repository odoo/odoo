# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.exceptions import ValidationError
from odoo.addons.hr_contract.tests.common import TestContractCommon
from odoo.tests import tagged

@tagged('test_contracts')
class TestHrContracts(TestContractCommon):

    @classmethod
    def setUpClass(cls):
        super(TestHrContracts, cls).setUpClass()
        cls.contracts = cls.env['hr.contract'].with_context(tracking_disable=True)

        cls.main_company = cls.env.ref('base.main_company')
        cls.main_company.contract_expiration_notice_period = 10
        cls.main_company.work_permit_expiration_notice_period = 10

        cls.company_2 = cls.env['res.company'].create({
            'name': 'TestCompany2',
            'contract_expiration_notice_period' : 5,
            'work_permit_expiration_notice_period': 10,
        })

        cls.employee2 = cls.env['hr.employee'].create({
            'name': 'Jane Smith',
            'work_permit_expiration_date': date(2015, 11, 1) + relativedelta(days=25),
            'company_id': cls.company_2.id,
        })

    def create_contract(self, state, kanban_state, start, end=None, employee_id=None):
        return self.env['hr.contract'].create({
            'name': 'Contract',
            'employee_id': employee_id or self.employee.id,
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

    def test_check_multi_company_contract_expiration(self):
        """
            Check that the expiration warnings for contracts and work permits are posted based on the res settings.

           Test flow:
            - Set contract end day and work permit end days in the main company
            - Create a John Doe employee in the main company
            - Create a John Doe's contract
            - Create a TestCompany2 company and set contract end days and work permit end days
            - Create a John Smith employee in the TestCompany2 company
            - Create a John Smith's contract
            - Run automated actions (HR Contract: update state)
            - Check if the expiration activity is scheduled or not
            - A few days after run automated actions (HR Contract: update state)
            - Again check if the expiration activity is scheduled or not
        """

        self.employee.work_permit_expiration_date = date(2015, 11, 1) + relativedelta(days=10)

        contract_1 = self.create_contract('open', 'normal', date(2015, 11, 1), date(2015, 11, 20), self.employee.id)
        contract_2 = self.create_contract('open', 'normal', date(2015, 11, 1), date(2015, 11, 13), self.employee2.id)

        with freeze_time('2015-11-01'):
            self.env['hr.contract'].update_state()

            mail_activity = self.env['mail.activity'].search([('res_id', '=', contract_1.id), ('res_model', '=', 'hr.contract')])
            self.assertTrue(mail_activity.exists(), "There should be reminder activity as employee work permit going to end soon")
            mail_activity.unlink()

            mail_activity2 = self.env['mail.activity'].search([('res_id', '=', contract_2.id), ('res_model', '=', 'hr.contract')])
            self.assertFalse(mail_activity2.exists(), "There should be no reminder as the contract is not yet about to expire.")

        with freeze_time('2015-11-10'):

            contract_1.kanban_state = 'normal'
            self.env['hr.contract'].update_state()

            mail_activity2 = self.env['mail.activity'].search([('res_id', '=', contract_2.id), ('res_model', '=', 'hr.contract')])
            self.assertTrue(mail_activity2.exists(), "There should be reminder activity as employee contract going to end soon")

        with freeze_time('2015-11-15'):
            self.env['hr.contract'].update_state()

            mail_activity = self.env['mail.activity'].search([('res_id', '=', contract_1.id), ('res_model', '=', 'hr.contract')])
            self.assertTrue(len(mail_activity) == 2, "There should be reminder activity as employee contract and work permit going to end soon")

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
            'name': "Sick day",
            'resource_id': self.employee.resource_id.id,
            'calendar_id': calendar1.id,
            'date_from': datetime(2024, 5, 2, 8, 0),
            'date_to': datetime(2024, 5, 2, 17, 0),
        })
        leave2 = self.env['resource.calendar.leaves'].create({
            'name': "Sick again",
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
