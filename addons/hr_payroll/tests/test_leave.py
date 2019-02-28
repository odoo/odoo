# # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import pytz
from dateutil.relativedelta import relativedelta
from odoo import exceptions
from odoo.tests.common import tagged
from odoo.addons.hr_payroll.tests.common import TestPayslipBase


class TestPayrollLeave(TestPayslipBase):

    def create_leave(self):
        return self.env['hr.leave'].create({
            'name': 'Holiday !!!',
            'employee_id': self.richard_emp.id,
            'holiday_status_id': self.leave_type.id,
            'date_to': datetime.today() + relativedelta(days=1),
            'date_from': datetime.today(),
            'number_of_days': 1,
        })

    def test_resource_leave_has_work_entry_type(self):
        leave = self.create_leave()

        resource_leave = leave._create_resource_leave()
        self.assertEqual(resource_leave.work_entry_type_id, self.leave_type.work_entry_type_id, "it should have the corresponding work_entry type")

    def test_resource_leave_in_contract_calendar(self):
        other_calendar = self.env['resource.calendar'].create({'name': 'New calendar'})
        contract = self.richard_emp.contract_ids[0]
        contract.resource_calendar_id = other_calendar
        contract.state = 'open'  # this set richard's calendar to New calendar
        leave = self.create_leave()

        resource_leave = leave._create_resource_leave()
        self.assertEqual(len(resource_leave), 1, "it should have created only one resource leave")
        self.assertEqual(resource_leave.work_entry_type_id, self.leave_type.work_entry_type_id, "it should have the corresponding work_entry type")

    def test_resource_leave_different_calendars(self):
        other_calendar = self.env['resource.calendar'].create({'name': 'New calendar'})
        contract = self.richard_emp.contract_ids[0]
        contract.resource_calendar_id = other_calendar
        contract.state = 'open'  # this set richard's calendar to New calendar

        # set another calendar
        self.richard_emp.resource_calendar_id = self.env['resource.calendar'].create({'name': 'Other calendar'})

        leave = self.create_leave()
        resource_leave = leave._create_resource_leave()
        self.assertEqual(len(resource_leave), 2, "it should have created one resource leave per calendar")
        self.assertEqual(resource_leave.mapped('work_entry_type_id'), self.leave_type.work_entry_type_id, "they should have the corresponding work_entry type")
