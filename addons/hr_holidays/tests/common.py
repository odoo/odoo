# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, bundles


@bundles('hr_holidays.common')
class TestHrHolidaysCommon(common.TransactionCase):

    @classmethod
    def quick_ref(cls, xmlid):
        """Find the matching record, without an existence check."""
        model, id = cls.env['ir.model.data']._xmlid_to_res_model_res_id(xmlid)
        return cls.env[model].browse(id)

    @classmethod
    def setUpClass(cls):
        super(TestHrHolidaysCommon, cls).setUpClass()
        cls.env.user.tz = 'Europe/Brussels'
        cls.env.user.company_id.resource_calendar_id.tz = "Europe/Brussels"

        cls.company = cls.quick_ref('hr_holidays.test_company')
        cls.env.user.company_id = cls.company

        # The available time off types are the ones whose:
        # 1. Company is one of the selected companies.
        # 2. Company is false but whose country is one the countries of the selected companies.
        # 3. Company is false and country is false
        # Thus, a time off type is defined to be available for `Test company`
        # For example, the tour 'time_off_request_calendar_view' would succeed (false positive) without this leave type.
        # However, the tour won't create a time-off request (as expected)because no time-off type is available to be selected on the leave
        # This would cause the test case that uses the tour to fail.
        # MANAGED THROUGH TEST DATA BUNDLE
        # cls.env['hr.leave.type'].create({
        #     'name': 'Test Leave Type',
        #     'requires_allocation': 'no',
        #     'request_unit': 'day',
        #     'company_id': cls.company.id,
        # })

        # Test users to use through the various tests
        cls.user_hruser = cls.quick_ref('hr_holidays.test_user_hruser')
        cls.user_hruser_id = cls.user_hruser.id

        cls.user_hrmanager = cls.quick_ref('hr_holidays.test_user_hrmanager')
        cls.user_hrmanager_id = cls.user_hrmanager.id

        cls.user_employee = cls.quick_ref('hr_holidays.test_user_employee')
        cls.user_employee_id = cls.user_employee.id

        # Hr Data
        cls.hr_dept = cls.quick_ref('hr_holidays.hr_dept')
        cls.rd_dept = cls.quick_ref('hr_holidays.rd_dept')
        cls.employee_emp = cls.quick_ref('hr_holidays.employee_emp')
        cls.employee_emp_id = cls.employee_emp.id

        cls.employee_hruser = cls.quick_ref('hr_holidays.employee_hruser')
        cls.employee_hruser_id = cls.employee_hruser.id

        cls.employee_hrmanager = cls.quick_ref('hr_holidays.employee_hrmanager')
        cls.employee_hrmanager_id = cls.employee_hrmanager.id

        cls.hours_per_day = cls.employee_emp.resource_id.calendar_id.hours_per_day or 8
