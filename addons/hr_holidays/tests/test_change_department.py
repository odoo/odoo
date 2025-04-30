# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta, MO, FR

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestChangeDepartment(TestHrHolidaysCommon):
    def test_employee_change_department_request_change_department(self):
        self.HolidaysEmployeeGroup = self.env['hr.leave'].with_user(self.user_employee_id)

        HolidayStatusManagerGroup = self.env['hr.leave.type'].with_user(self.user_hrmanager_id)
        self.holidays_status_1 = HolidayStatusManagerGroup.create({
            'name': 'NotLimitedHR',
            'requires_allocation': False,
        })

        def create_holiday(name, start, end):
            return self.HolidaysEmployeeGroup.create({
                'name': name,
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_status_1.id,
                'request_date_from': date.today() + relativedelta(weekday=(MO(2) if start > 0 else FR(-1))) + relativedelta(days=start),
                'request_date_to': date.today() + relativedelta(weekday=(MO(2) if start > 0 else FR(-1))) + relativedelta(days=end),
            })

        # Non approved leave request change department
        self.employee_emp.department_id = self.rd_dept
        hol1_employee_group = create_holiday("hol1", 1, 1)
        self.employee_emp.department_id = self.hr_dept
        self.assertEqual(hol1_employee_group.department_id, self.hr_dept, 'hr_holidays: non approved leave request should change department if employee change department')

        # flushing is needed after approving because the hr.leave.department_id
        # is not yet recomputed

        # Approved passed leave request change department
        self.employee_emp.department_id = self.hr_dept
        hol2_employee_group = create_holiday("hol2", -1, -1)
        hol2_user_group = hol2_employee_group.with_user(self.user_hruser_id)
        hol2_user_group.action_approve()
        self.env.flush_all()
        self.employee_emp.department_id = self.rd_dept
        self.assertEqual(hol2_employee_group.department_id, self.hr_dept, 'hr_holidays: approved passed leave request should stay in previous department if employee change department')

        # Approved future leave request change department
        self.employee_emp.department_id = self.hr_dept
        hol22_employee_group = create_holiday("hol22", 2, 2)
        hol22_user_group = hol22_employee_group.with_user(self.user_hruser_id)
        hol22_user_group.action_approve()
        self.env.flush_all()
        self.employee_emp.department_id = self.rd_dept
        self.assertEqual(hol22_employee_group.department_id, self.rd_dept, 'hr_holidays: approved future leave request should change department if employee change department')

        # Refused passed leave request change department
        self.employee_emp.department_id = self.rd_dept
        hol3_employee_group = create_holiday("hol3", -2, -2)
        hol3_user_group = hol3_employee_group.with_user(self.user_hruser_id)
        hol3_user_group.action_refuse()
        self.env.flush_all()
        self.employee_emp.department_id = self.hr_dept # Change department
        self.assertEqual(hol3_user_group.department_id, self.rd_dept, 'hr_holidays: refused passed leave request should stay in previous department if employee change department')

        # Refused future leave request change department
        self.employee_emp.department_id = self.rd_dept
        hol32_employee_group = create_holiday("hol32", 10, 10)
        hol32_user_group = hol32_employee_group.with_user(self.user_hruser_id)
        hol32_user_group.action_refuse()
        self.env.flush_all()
        self.employee_emp.department_id = self.hr_dept # Change department
        self.assertEqual(hol32_employee_group.department_id, self.hr_dept, 'hr_holidays: refused future leave request should change department if employee change department')
