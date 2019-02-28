
import os
from datetime import datetime
from odoo.tools import config, test_reports
from odoo.tests.common import tagged
from odoo.addons.hr_payroll.tests.common import TestPayslipContractBase

class TestPayslipCalendars(TestPayslipContractBase):


    def test_contract_state_incoming_to_open(self):
        # Employee's calendar should change
        self.assertEqual(self.richard_emp.resource_calendar_id, self.calendar_richard)
        self.contract_cdd.state = 'open'
        self.assertEqual(self.richard_emp.resource_calendar_id, self.contract_cdd.resource_calendar_id, "The employee should have the calendar of its contract.")

    def test_contract_transfer_leaves(self):

        def create_calendar_leave(start, end, resource=None):
            return self.env['resource.calendar.leaves'].create({
                'name': 'leave name',
                'date_from': start,
                'date_to': end,
                'resource_id': resource.id if resource else None,
                'calendar_id': self.richard_emp.resource_calendar_id.id,
                'work_entry_type_id': self.work_entry_type_leave.id,
                'time_type': 'leave',
            })

        start = datetime.strptime('2015-11-17 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-11-20 18:00:00', '%Y-%m-%d %H:%M:%S')
        leave1 = create_calendar_leave(start, end, resource=self.richard_emp.resource_id)

        start = datetime.strptime('2015-11-25 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-11-28 18:00:00', '%Y-%m-%d %H:%M:%S')
        leave2 = create_calendar_leave(start, end, resource=self.richard_emp.resource_id)

        # global leave
        start = datetime.strptime('2015-11-25 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-11-28 18:00:00', '%Y-%m-%d %H:%M:%S')
        leave3 = create_calendar_leave(start, end)

        self.calendar_richard.transfer_leaves_to(self.calendar_35h, resources=self.richard_emp.resource_id, from_date=datetime.strptime('2015-11-21', '%Y-%m-%d').date())

        self.assertEqual(leave1.calendar_id, self.calendar_richard, "It should stay in Richard's calendar")
        self.assertEqual(leave3.calendar_id, self.calendar_richard, "Global leave should stay in original calendar")
        self.assertEqual(leave2.calendar_id, self.calendar_35h, "It should be transfered to the other calendar")

        # Transfer global leaves
        self.calendar_richard.transfer_leaves_to(self.calendar_35h, resources=None, from_date=datetime.strptime('2015-11-21', '%Y-%m-%d').date())

        self.assertEqual(leave3.calendar_id, self.calendar_35h, "Global leave should be transfered")