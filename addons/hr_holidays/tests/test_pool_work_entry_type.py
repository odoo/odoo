# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged('pool_time_off')
class TestPoolWorkEntryType(TestHrHolidaysCommon):
    """ The employees request a pool instead of its pooled types, split into them on approval.
    The employee works 8:00-12:00 and 13:00-17:00 (8 hours a day). """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        country = cls.company.country_id
        cls.pool_type = cls.env['hr.work.entry.type'].create({
            'name': 'Paid Time Off', 'code': 'POOL', 'country_id': country.id, 'requires_allocation': False,
            'leave_validation_type': 'hr', 'request_unit': 'half_day', 'unit_of_measure': 'day', 'sequence': 1,
        })
        type_values = {
            'country_id': country.id, 'requires_allocation': True, 'leave_validation_type': 'hr',
            'request_unit': 'half_day', 'unit_of_measure': 'day', 'pool_id': cls.pool_type.id,
        }
        # legal is allocated in hours and validated twice, the others in days
        cls.legal_type = cls.env['hr.work.entry.type'].create({
            **type_values, 'name': 'Legal', 'code': 'LEGAL', 'unit_of_measure': 'hour', 'pool_sequence': 1,
            'leave_validation_type': 'both'})
        cls.extra_type = cls.env['hr.work.entry.type'].create({
            **type_values, 'name': 'Extra-legal', 'code': 'EXTRA', 'pool_sequence': 2})
        cls.seniority_type = cls.env['hr.work.entry.type'].create({
            **type_values, 'name': 'Seniority', 'code': 'SENIORITY', 'pool_sequence': 2})
        cls.european_type = cls.env['hr.work.entry.type'].create({
            **type_values, 'name': 'European', 'code': 'EUROPEAN', 'pool_sequence': 3})

    def _allocate(self, work_entry_type, amount, date_to=date(2030, 12, 31)):
        values = {
            'name': 'Pool test', 'employee_id': self.employee_emp_id, 'work_entry_type_id': work_entry_type.id,
            'date_from': date(2030, 1, 1), 'date_to': date_to,
        }
        if work_entry_type.unit_of_measure == 'hour':
            values.update(number_of_hours=amount, number_of_days=amount / 8)
        else:
            values['number_of_days'] = amount
        allocation = self.env['hr.leave.allocation'].create(values)
        if allocation.state != 'validate':
            allocation.action_approve()
        return allocation

    def _request(self, date_from, date_to):
        return self.env['hr.leave'].with_user(self.user_employee).create({
            'employee_id': self.employee_emp_id,
            'work_entry_type_id': self.pool_type.id,
            'request_date_from': date_from,
            'request_date_to': date_to,
        })

    def _approve(self, leave, check_state=True):
        leave.with_user(self.user_hruser).with_context(allowed_company_ids=self.company.ids).action_approve(check_state)

    def _remaining(self, work_entry_type):
        data = work_entry_type.get_allocation_data(self.employee_emp, date(2030, 1, 7))[self.employee_emp]
        return data[0][1]['virtual_remaining_leaves']

    def _pool_remaining(self):
        return self.pool_type.with_context(employee_id=self.employee_emp_id, leave_date_from=date(2030, 1, 7)).virtual_remaining_leaves

    def _employee_leaves(self):
        return self.env['hr.leave'].search([('employee_id', '=', self.employee_emp_id)], order='date_from')

    def test_pool_split_on_approval(self):
        """ The pooled types are consumed by order: legal, then extra-legal, then European. """
        self._allocate(self.legal_type, 16)  # 2 days
        self._allocate(self.extra_type, 1)
        self._allocate(self.european_type, 5)
        self.assertEqual(self._pool_remaining(), 8)
        # Monday 7 to Thursday 10 January 2030: 4 days
        leave = self._request(date(2030, 1, 7), date(2030, 1, 10))
        self.assertEqual(leave.state, 'confirm')
        # the request to approve reserves the balance of the pooled types
        self.assertEqual(self._remaining(self.legal_type), 0)
        self.assertEqual(self._remaining(self.extra_type), 0)
        self.assertEqual(self._remaining(self.european_type), 4)
        self.assertEqual(self._pool_remaining(), 4)

        self._approve(leave)
        split_leaves = self._employee_leaves()
        self.assertEqual(
            [(leave.work_entry_type_id, leave.request_date_from, leave.request_date_to, leave.number_of_hours, leave.state)
             for leave in split_leaves],
            [
                (self.legal_type, date(2030, 1, 7), date(2030, 1, 8), 16, 'validate'),
                (self.extra_type, date(2030, 1, 9), date(2030, 1, 9), 8, 'validate'),
                (self.european_type, date(2030, 1, 10), date(2030, 1, 10), 8, 'validate'),
            ])
        self.assertEqual(self._remaining(self.european_type), 4)

    def test_pool_split_within_a_day(self):
        """ The boundary between two pooled types falls on a half day. """
        self._allocate(self.legal_type, 12)  # 1.5 day
        self._allocate(self.european_type, 5)
        self._approve(self._request(date(2030, 1, 7), date(2030, 1, 8)))
        legal_leave, european_leave = self._employee_leaves()
        self.assertEqual(legal_leave.work_entry_type_id, self.legal_type)
        self.assertEqual(legal_leave.number_of_hours, 12)
        self.assertEqual(european_leave.work_entry_type_id, self.european_type)
        self.assertEqual(european_leave.number_of_days, 0.5)
        # legal until Tuesday noon, European from the end of the lunch break (Brussels time)
        self.assertEqual(legal_leave.date_to, datetime(2030, 1, 8, 11, 0))
        self.assertEqual(european_leave.date_from, datetime(2030, 1, 8, 12, 0))

    def test_pool_split_after_first_approval(self):
        """ A pool validated twice is split on its second approval. """
        self.pool_type.leave_validation_type = 'both'
        self._allocate(self.legal_type, 8)
        self._allocate(self.european_type, 5)
        leave = self._request(date(2030, 1, 7), date(2030, 1, 8))
        self._approve(leave, check_state=False)
        self.assertEqual((leave.state, leave.work_entry_type_id), ('validate1', self.pool_type))
        self._approve(leave)
        self.assertEqual(
            [(leave.work_entry_type_id, leave.state) for leave in self._employee_leaves()],
            [(self.legal_type, 'validate'), (self.european_type, 'validate')])

    def test_pool_balance_rounded_to_half_days(self):
        """ A balance that is not a whole number of half days stays on its type. """
        self._allocate(self.legal_type, 6)  # 0.75 day
        self._allocate(self.european_type, 5)
        self._approve(self._request(date(2030, 1, 7), date(2030, 1, 7)))
        self.assertEqual(self._employee_leaves().mapped('work_entry_type_id'), self.legal_type | self.european_type)
        self.assertEqual(self._remaining(self.legal_type), 2)

    def test_pool_same_order_earliest_end_date_first(self):
        """ Among types of the same order, the one whose allocation ends first is consumed first. """
        self._allocate(self.extra_type, 1, date_to=date(2031, 3, 31))
        self._allocate(self.seniority_type, 1, date_to=date(2030, 12, 31))
        self._approve(self._request(date(2030, 1, 7), date(2030, 1, 8)))
        self.assertEqual(self._employee_leaves().work_entry_type_id.ids, [self.seniority_type.id, self.extra_type.id])

    def test_pool_request_blocked_without_balance(self):
        self._allocate(self.legal_type, 8)
        self._allocate(self.european_type, 1)
        with self.assertRaises(ValidationError):
            self._request(date(2030, 1, 7), date(2030, 1, 9))

    def test_pool_requests_to_approve_consumed_in_order(self):
        """ A second request takes what the first one to approve leaves. """
        self._allocate(self.legal_type, 16)
        self._allocate(self.european_type, 5)
        first_leave = self._request(date(2030, 1, 7), date(2030, 1, 7))
        second_leave = self._request(date(2030, 1, 14), date(2030, 1, 15))
        self.assertEqual(self._remaining(self.legal_type), 0)
        self.assertEqual(self._remaining(self.european_type), 4)
        self._approve(second_leave)
        self.assertEqual((self._employee_leaves() - first_leave).work_entry_type_id, self.legal_type | self.european_type)

    def test_pooled_types_hidden_to_employees(self):
        self._allocate(self.legal_type, 16)
        employee_leave = self.env['hr.leave'].with_user(self.user_employee).new({
            'employee_id': self.employee_emp_id, 'company_id': self.company.id})
        employee_types = employee_leave.allowed_work_entry_type_ids._origin
        self.assertIn(self.pool_type, employee_types)
        self.assertNotIn(self.legal_type, employee_types)
        self.assertNotIn(self.european_type, employee_types)
        defaults = self.env['hr.leave'].with_user(self.user_employee).with_context(
            default_employee_id=self.employee_emp_id).default_get(['employee_id', 'work_entry_type_id'])
        self.assertEqual(defaults['work_entry_type_id'], self.pool_type.id)

        officer_leave = self.env['hr.leave'].with_user(self.user_hruser).new({
            'employee_id': self.employee_emp_id, 'company_id': self.company.id})
        self.assertIn(self.legal_type, officer_leave.allowed_work_entry_type_ids._origin)

    def test_pool_configuration(self):
        with self.assertRaises(ValidationError):
            self.legal_type.request_unit = 'day'
        with self.assertRaises(ValidationError):
            self.pool_type.requires_allocation = True
