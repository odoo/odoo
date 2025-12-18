# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestTimeoffEvent(TestHrHolidaysCommon):

    def test_no_videocall_url_in_timeoff_event(self):
        """ Test that the timeoff event does not need a video call """

        self.hr_work_entry_type = self.env['hr.work.entry.type'].with_user(self.user_hrmanager).create({
            'name': 'Time Off Type',
            'code': 'Time Off Type',
            'requires_allocation': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })
        self.holiday = self.env['hr.leave'].with_context(mail_create_nolog=True, mail_notrack=True).with_user(self.user_employee).create({
            'name': 'Time Off 1 sura',
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.hr_work_entry_type.id,
            'request_date_from': datetime(2020, 1, 15),
            'request_date_to': datetime(2020, 1, 15) + relativedelta(days=1),
        })
        self.holiday.with_user(self.user_hrmanager).action_approve()

        # Finding the event corresponding to the leave
        search_criteria = [
            ('name', 'like', self.holiday.employee_id.name),
            ('start_date', '>=', self.holiday.request_date_from),
            ('stop_date', '<=', self.holiday.request_date_to),
        ]
        timeoff_event = self.env['calendar.event'].search(search_criteria)
        self.assertTrue(timeoff_event, "The timeoff event should exist")
        self.assertFalse(timeoff_event._need_video_call(), "The timeoff event does not need a video call")
