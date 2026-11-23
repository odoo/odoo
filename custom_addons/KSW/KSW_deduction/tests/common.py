# -*- coding: utf-8 -*-
"""Common test setup for KSW_deduction tests."""
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.tests.common import TransactionCase
class DeductionCommon(TransactionCase):
    """Shared fixtures for deduction tests."""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.dept_a = cls.env['hr.department'].create({'name': 'KSWDED Dept A'})
        cls.dept_b = cls.env['hr.department'].create({'name': 'KSWDED Dept B'})
        cls.manager_emp = cls.env['hr.employee'].create({
            'name': 'KSWDED Manager A',
            'department_id': cls.dept_a.id,
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'KSWDED Employee',
            'department_id': cls.dept_a.id,
            'parent_id': cls.manager_emp.id,
        })
        cls.employee_b = cls.env['hr.employee'].create({
            'name': 'KSWDED Employee B',
            'department_id': cls.dept_b.id,
        })
        cls.type_loan = cls.env.ref('KSW_deduction.type_loan')
        cls.type_advance = cls.env.ref('KSW_deduction.type_advance')
        cls.type_gov_pen = cls.env.ref('KSW_deduction.type_gov_penalty')
        cls.type_internal_pen = cls.env.ref('KSW_deduction.type_internal_penalty')
        cls.this_month = date.today().replace(day=1)
        cls.next_month = cls.this_month + relativedelta(months=1)
    def _make_deduction(self, ded_type=None, employee=None,
                        amount=1000.0, installments=4, start_month=None,
                        reason='Test'):
        return self.env['ksw.deduction'].create({
            'employee_id': (employee or self.employee).id,
            'type_id': (ded_type or self.type_advance).id,
            'amount': amount,
            'installments': installments,
            'start_month': start_month or self.this_month,
            'reason': reason,
        })
    def _walk_loan_to_pending_gm(self, ded):
        ded.action_submit()
        ded.action_dm_approve()
        ded.x_hr_no_penalties_confirmed = True
        ded.action_hr_approve()
        ded.x_acc_budget_confirmed = True
        ded.action_acc_approve()
        return ded
