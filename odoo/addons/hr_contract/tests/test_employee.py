# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

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
