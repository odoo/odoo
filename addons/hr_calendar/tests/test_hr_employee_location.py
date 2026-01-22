# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import common, tagged
from datetime import datetime


@tagged('post_install', '-at_install', "homeworking_tests")
class TestHrHomeworkingHrEmployeeLocation(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.tz = 'Europe/Brussels'

        cls.user_employee = mail_new_test_user(cls.env, login='david', groups='base.group_user')

        # Hr Data
        Department = cls.env['hr.department'].with_context(tracking_disable=True)
        WorkLocation = cls.env['hr.work.location'].with_context(tracking_disable=True)
        main_partner_id = cls.env.ref('base.main_partner')

        cls.rd_dept = Department.create({
            'name': 'Research and devlopment',
        })

        cls.work_office_1 = WorkLocation.create({
            'name': "Bureau 1",
            'location_type': "office",
            'address_id': main_partner_id.id,
        })

        cls.work_office_2 = WorkLocation.create({
            'name': "Bureau 2",
            'location_type': "office",
            'address_id': main_partner_id.id,
        })

        cls.work_home = WorkLocation.create({
            'name': "Maison",
            'location_type': "home",
            'address_id': main_partner_id.id,
        })

        cls.employee_emp = cls.env['hr.employee'].create({
            'name': 'David Employee',
            'user_id': cls.user_employee.id,
            'department_id': cls.rd_dept.id,
            'monday_location_id': cls.work_home.id,
            'tuesday_location_id': cls.work_home.id,
            'wednesday_location_id': cls.work_office_1.id,
            'thursday_location_id': cls.work_office_1.id,
            'friday_location_id': cls.work_office_1.id,
            'saturday_location_id': cls.work_home.id,
            'sunday_location_id': cls.work_home.id,
        })

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

    def test_get_views_replace_hw_location_by_date(self):
        view = self.env["ir.ui.view"].create({
            "arch": """<list><field name="work_location_name" /></list>""",
            "model": "hr.employee",
            "type": "list",
        })
        # Wednesday January 28 2026
        with freeze_time("2026-01-28"):
            got_view = self.env["hr.employee"].get_views([(view.id, "list")])
        self.assertTrue("work_location_name" in got_view["models"]["hr.employee"]["fields"])
        self.assertTrue("wednesday_location_id" in got_view["models"]["hr.employee"]["fields"])
        self.assertEqual(got_view["views"]["list"]["arch"], """<list><field name="wednesday_location_id"/></list>""")
