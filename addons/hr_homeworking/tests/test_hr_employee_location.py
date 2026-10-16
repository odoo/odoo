# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo.addons.hr_homeworking.tests.common import TestHrHomeworkingCommon
from odoo.addons.mail.tests.common import mail_new_test_user

from odoo.tests import tagged
from datetime import datetime

@tagged('post_install', '-at_install', "homeworking_tests")
class TestHrHomeworkingHrEmployeeLocation(TestHrHomeworkingCommon):
    @classmethod
    def setUpClass(cls):
        super(TestHrHomeworkingHrEmployeeLocation, cls).setUpClass()
        cls.HrEmployeeLocation = cls.env['hr.employee.location']

    def test_set_location_with_weekly_option_changes_employee_location(self):
        wizard = self.env['homework.location.wizard'].create({
            'work_location_id': self.work_home.id,
            'date': datetime(2023, 10, 4),  # wednesday
            'employee_id': self.employee_emp.id,
            'weekly': True
        })
        wizard.set_employee_location()
        self.assertEqual(self.employee_emp.wednesday_location_id.id, self.work_home.id)
        created_worklocations = self.HrEmployeeLocation.search([
            ('employee_id', '=', self.employee_emp.id),
            ('date', '=', datetime(2023, 10, 4)),
        ])
        self.assertEqual(len(created_worklocations), 0, 'should have created 0 worklocation records')

    def test_set_location_without_weekly_option_should_create_an_exception(self):
        wizard = self.env['homework.location.wizard'].create({
            'work_location_id': self.work_home.id,
            'date': datetime(2023, 10, 4),  # wednesday
            'employee_id': self.employee_emp.id,
            'weekly': False
        })
        wizard.set_employee_location()
        created_worklocations = self.HrEmployeeLocation.search([
            ('employee_id', '=', self.employee_emp.id),
            ('date', '=', datetime(2023, 10, 4)),
        ])
        self.assertEqual(len(created_worklocations), 1, 'should have created 1 worklocation record')
        self.assertEqual(created_worklocations.work_location_id.id, self.work_home.id)

    def test_create_exception_on_top_of_exception_keeps_a_single_record(self):
        wizard = self.env['homework.location.wizard'].create({
            'work_location_id': self.work_home.id,
            'date': datetime(2023, 10, 4),  # wednesday
            'employee_id': self.employee_emp.id,
            'weekly': False
        })
        wizard.set_employee_location()
        created_worklocations = self.HrEmployeeLocation.search([
            ('employee_id', '=', self.employee_emp.id),
            ('date', '=', datetime(2023, 10, 4)),
        ])
        self.assertEqual(len(created_worklocations), 1, 'should have created 1 worklocation record')
        wizard.work_location_id = self.work_office_2
        wizard.set_employee_location()
        created_worklocations = self.HrEmployeeLocation.search([
            ('employee_id', '=', self.employee_emp.id),
            ('date', '=', datetime(2023, 10, 4)),
        ])
        self.assertEqual(len(created_worklocations), 1, 'should have created 1 worklocation record')
        self.assertEqual(created_worklocations.work_location_id.id, self.work_office_2.id)

    def test_set_same_location_as_default_one_should_not_create_exception(self):
        wizard = self.env['homework.location.wizard'].create({
            'work_location_id': self.work_office_1.id,
            'date': datetime(2023, 10, 4),  # wednesday
            'employee_id': self.employee_emp.id,
            'weekly': False
        })
        wizard.set_employee_location()
        created_worklocations = self.HrEmployeeLocation.search([
            ('employee_id', '=', self.employee_emp.id),
            ('date', '=', datetime(2023, 10, 4)),
        ])
        self.assertEqual(len(created_worklocations), 0, 'should have created 0 worklocation records')

    def test_set_default_day_location_as_exception_will_delete_exception(self):
        # create exception for a certain day
        wizard = self.env['homework.location.wizard'].create({
            'work_location_id': self.work_home.id,
            'date': datetime(2023, 10, 4),  # wednesday
            'employee_id': self.employee_emp.id,
            'weekly': False
        })
        wizard.set_employee_location()

        created_worklocations = self.HrEmployeeLocation.search([
            ('employee_id', '=', self.employee_emp.id),
            ('date', '=', datetime(2023, 10, 4)),
        ])

        self.assertEqual(len(created_worklocations), 1, 'should have created 1 worklocation records')

        # set default work location on day where an exception exists
        wizard.work_location_id = self.work_office_1
        wizard.set_employee_location()

        created_worklocations = self.HrEmployeeLocation.search([
            ('employee_id', '=', self.employee_emp.id),
            ('date', '=', datetime(2023, 10, 4)),
        ])

        # exception should be deleted
        self.assertEqual(len(created_worklocations), 0, 'should have deleted the worklocation record')

    @freeze_time("2023-10-04")
    def test_im_status_takes_exceptional_location_of_today(self):
        alice_user = mail_new_test_user(self.env, login="alice_user", groups="base.group_user")
        self.assertFalse(alice_user.has_group("hr.group_hr_user"))
        partner = self.user_employee.partner_id.with_user(alice_user)
        self.assertEqual(partner.im_status, "office_offline")
        self.env["homework.location.wizard"].create({
            "date": datetime(2023, 10, 4),
            "employee_id": self.employee_emp.id,
            "weekly": False,
            "work_location_id": self.work_home.id,
        }).set_employee_location()
        self.env.invalidate_all()
        self.assertEqual(partner.im_status, "home_offline")

    def test_get_views_replace_hw_location_by_date(self):
        view = self.env["ir.ui.view"].create({
            "arch": """<tree><field name="name_work_location_display" /></tree>""",
            "model": "hr.employee",
            "type": "tree",
        })
        # Wednesday January 28 2026
        with freeze_time("2026-01-28"):
            got_view = self.env["hr.employee"].get_views([(view.id, "tree")])
        self.assertTrue("name_work_location_display" in got_view["models"]["hr.employee"])
        self.assertTrue("wednesday_location_id" in got_view["models"]["hr.employee"])
        self.assertEqual(got_view["views"]["tree"]["arch"], """<tree><field name="wednesday_location_id"/></tree>""")
