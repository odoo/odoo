# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo.addons.hr_contract.tests.common import TestContractCommon


class TestHrContracts(TestContractCommon):

    @classmethod
    def setUpClass(cls):
        super(TestHrContracts, cls).setUpClass()
        cls.contracts = cls.env['hr.contract'].with_context(tracking_disable=True)
        cls.test_contract = dict(name='Test', wage=1, employee_id=cls.employee.id, state='open')

    def test_employee_contractwarning(self):
        self.assertEqual(self.employee.contract_warning, True)

    def apply_cron(self):
        self.env.ref('hr_contract.ir_cron_data_contract_update_state').method_direct_trigger()

    def test_contract_enddate(self):
        self.test_contract.update(dict(date_end=datetime.now() + relativedelta(days=100)))
        self.contract = self.contracts.create(self.test_contract)
        self.apply_cron()
        self.assertEqual(self.contract.state, 'open')
        self.assertEqual(self.contract.kanban_state, 'normal')
        self.assertEqual(self.employee.contract_warning, False)

        self.test_contract.update(dict(date_end=datetime.now() + relativedelta(days=5)))
        self.contract.write(self.test_contract)
        self.apply_cron()
        self.assertEqual(self.contract.state, 'open')
        self.assertEqual(self.contract.kanban_state, 'blocked')

        self.test_contract.update({
            'date_start': datetime.now() + relativedelta(days=-50),
            'date_end': datetime.now() + relativedelta(days=-1),
            'state': 'open',
            'kanban_state': 'blocked',
        })
        self.contract.write(self.test_contract)
        self.apply_cron()
        self.assertEqual(self.contract.state, 'close')

    def test_contract_pending_visa_expire(self):
        self.employee.visa_expire = date.today() + relativedelta(days=30)
        self.test_contract.update(dict(date_end=False))
        self.contract = self.contracts.create(self.test_contract)
        self.apply_cron()
        self.assertEqual(self.contract.state, 'open')
        self.assertEqual(self.contract.kanban_state, 'blocked')

        self.employee.visa_expire = date.today() + relativedelta(days=-5)
        self.test_contract.update({
            'date_start': datetime.now() + relativedelta(days=-50),
            'state': 'open',
            'kanban_state': 'blocked',
        })
        self.contract.write(self.test_contract)
        self.apply_cron()
        self.assertEqual(self.contract.state, 'close')

    def test_contract_start_date(self):
        self.test_contract.update(dict(date_start=datetime.now(), state='draft', kanban_state='done'))
        self.contract = self.contracts.create(self.test_contract)
        self.apply_cron()
        self.assertEqual(self.contract.state, 'open')

    def test_contract_auto_expire(self):
        self.test_contract.update(dict(date_start=date.today() - relativedelta(days=10), state='open'))
        self.contract = self.contracts.create(self.test_contract)
        self.apply_cron()
        self.assertEqual(self.contract.state, 'open')

        self.contract.date_end = date.today() - relativedelta(days=3)
        self.assertEqual(self.contract.state, 'close')
