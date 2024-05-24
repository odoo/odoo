# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import pytz

from .common import TestContractCommon


class TestHrEmployee(TestContractCommon):

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

    def test_employee_first_contract_date_base_case(self):
        '''
        Test if when a contract is attached to an employee, the
        first_contract_date is updated accordingly.
        '''
        start = datetime.strptime('2015-11-01', '%Y-%m-%d').date()
        self.create_contract('open', 'normal', start)
        self.assertEqual(
            self.employee.first_contract_date, start,
            'The first_contract_date should be the start date of the contract.'
        )

    def test_employee_first_contract_date_archived_contract(self):
        '''
        Test if when a contract is attached to an employee, the
        first_contract_date is updated accordingly when archived.
        '''
        start = datetime.strptime('2015-11-01', '%Y-%m-%d').date()
        contract = self.create_contract('open', 'normal', start)
        self.assertEqual(
            self.employee.first_contract_date, start,
            'The first_contract_date should be the start date of the contract.',
        )
        contract.action_archive()
        self.assertEqual(
            self.employee.first_contract_date, False,
            'The first_contract_date should be False when the contract is archived. '
            'Because no active contract is attached to the employee.',
        )

    def test_employee_first_contract_date_multiple_contracts(self):
        '''
        Test if when multiple contracts are attached to an employee, the
        first_contract_date is updated accordingly.
        '''
        start1 = datetime.strptime('2015-11-01', '%Y-%m-%d').date()
        start2 = datetime.strptime('2016-11-01', '%Y-%m-%d').date()
        contract1 = self.create_contract('open', 'normal', start1)
        self.create_contract('draft', 'normal', start2)
        self.assertEqual(
            self.employee.first_contract_date, start1,
            'The first_contract_date should be the start date of the first contract.',
        )
        contract1.action_archive()
        self.assertEqual(
            self.employee.first_contract_date, start2,
            'The first_contract_date should be the start date of the second contract.',
        )

    def test_get_employee_calendar(self):
        result = self.employee._get_employee_calendar()
        self.assertEqual(result, [{
            'from': None,
            'to': None,
            'calendar': self.employee.resource_calendar_id,
        }])

        date_from = datetime(2022, 1, 1, tzinfo=pytz.utc)
        date_to = datetime(2022, 12, 31, tzinfo=pytz.utc)
        result = self.employee._get_employee_calendar(date_from, date_to)
        self.assertEqual(result, [{
            'from': date_from,
            'to': date_to,
            'calendar': self.employee.resource_calendar_id,
        }])

        date_from = datetime(2022, 1, 1, tzinfo=pytz.timezone('Europe/Berlin'))
        date_to = datetime(2022, 12, 31, tzinfo=pytz.timezone('Europe/Berlin'))
        with self.assertRaises(RuntimeError):
            self.employee._get_employee_calendar(date_from, date_to)  # should raise an error because dates are not in utc

        contract1 = self.create_contract('draft', 'normal', datetime(2022, 1, 1), datetime(2022, 6, 30))
        contract2 = self.create_contract('draft', 'normal', datetime(2022, 7, 1), datetime(2022, 12, 31))
        result = self.employee._get_employee_calendar(datetime(2022, 6, 1), datetime(2022, 6, 30))
        self.assertEqual(result, [{'from': datetime(2022, 1, 1, tzinfo=pytz.UTC), 'to': datetime(2022, 6, 30, 23, 59, 59, 999999, tzinfo=pytz.UTC), 'calendar': contract1.resource_calendar_id}])

        result = self.employee._get_employee_calendar(datetime(2022, 1, 1), datetime(2022, 12, 31))
        self.assertEqual(result, [
            {'from': datetime(2022, 1, 1, tzinfo=pytz.UTC), 'to': datetime(2022, 6, 30, 23, 59, 59, 999999, tzinfo=pytz.UTC), 'calendar': contract1.resource_calendar_id},
            {'from': datetime(2022, 7, 1, tzinfo=pytz.UTC), 'to': datetime(2022, 12, 31, 23, 59, 59, 999999, tzinfo=pytz.UTC), 'calendar': contract2.resource_calendar_id},
        ])
