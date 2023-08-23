# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_homeworking.tests.common import TestHrHomeworkingCommon
from odoo.tests import tagged
from freezegun import freeze_time
from datetime import datetime

@tagged('post_install', '-at_install', "homeworking_tests")
class TestHrHomeworkingHrEmployee(TestHrHomeworkingCommon):
    @classmethod
    def setUpClass(cls):
        super(TestHrHomeworkingHrEmployee, cls).setUpClass()
        cls.HrEmployeeLocation = cls.env['hr.employee.location']

    def test_register_via_employee(self):
        self.employee_hruser.write({"monday_location_id": self.work_office_1.id})
        location_for_hruser = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_hruser_id),
        ])
        self.assertEqual(len(location_for_hruser.ids), 1)
        self.assertTrue(location_for_hruser.weekly)
        self.assertEqual(location_for_hruser.weekday, 0)

        self.employee_hruser.write({"monday_location_id": False})
        location_for_hruser = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_hruser_id),
        ])
        self.assertEqual(len(location_for_hruser.ids), 0)

    @freeze_time('2023-05-16')
    def test_delete_from_employee_old_location(self):
        with freeze_time('2023-05-01'):
            self.HrEmployeeLocation.create({
                # tuesday
                'start_date': '2023-05-02',
                'end_date_create': '2023-05-02',
                'work_location_id': self.work_office_1.id,
                'employee_id': self.employee_hruser_id,
                'weekly': True,
            })
        self.employee_hruser.write({"tuesday_location_id": False})
        location_for_hruser = self.HrEmployeeLocation.search([
            ("employee_id", "=", self.employee_hruser_id),
        ])
        self.assertEqual(len(location_for_hruser.ids), 1)
        self.assertEqual(location_for_hruser.start_date, datetime(2023, 5, 2).date())
        self.assertEqual(location_for_hruser.end_date, datetime(2023, 5, 15).date())

    def test_data_worklocation(self):
        # 1 exception location
        self.HrEmployeeLocation.create({
            # tuesday
            'start_date': '2023-05-16',
            'end_date_create': '2023-05-16',
            'work_location_id': self.work_office_1.id,
            'employee_id': self.employee_hruser_id,
        })
        res = self.employee_hruser._get_worklocation(datetime(2023, 5, 1).date(), datetime(2023, 5, 30).date())
        arr = res[self.employee_hruser_id]
        self.assertEqual(arr[0]['location_id'], self.work_office_1.id)
        self.assertEqual(arr[0]['date'], datetime(2023, 5, 16).date())
        self.assertFalse(self.employee_hruser.tuesday_location_id)
        # 1 exception location
        # 1 weekly
        with freeze_time('2023-05-01'):
            record_weekly = self.HrEmployeeLocation.create({
                # tuesday
                'start_date': '2023-05-09',
                'end_date_create': '2023-05-09',
                'work_location_id': self.work_office_2.id,
                'employee_id': self.employee_hruser_id,
                'weekly': True
            })
        res = self.employee_hruser._get_worklocation(datetime(2023, 5, 1).date(), datetime(2023, 5, 30).date())
        arr = res[self.employee_hruser_id]
        self.assertEqual(arr[0]['location_id'], self.work_office_1.id)
        self.assertEqual(arr[0]['date'], datetime(2023, 5, 16).date())
        self.assertEqual(arr[1]['location_id'], self.work_office_2.id)
        self.assertEqual(arr[1]['date'], datetime(2023, 5, 9).date())
        self.assertEqual(arr[2]['location_id'], self.work_office_2.id)
        self.assertEqual(arr[2]['date'], datetime(2023, 5, 23).date())
        self.assertEqual(arr[3]['location_id'], self.work_office_2.id)
        self.assertEqual(arr[3]['date'], datetime(2023, 5, 30).date())

        # 1 exception location
        # 1 weekly
        # 1 removed
        record_weekly.add_removed_work_location(datetime(2023, 5, 23))
        res = self.employee_hruser._get_worklocation(datetime(2023, 5, 1).date(), datetime(2023, 5, 30).date())
        arr = res[self.employee_hruser_id]
        self.assertEqual(arr[0]['location_id'], self.work_office_1.id)
        self.assertEqual(arr[0]['date'], datetime(2023, 5, 16).date())
        self.assertEqual(arr[1]['location_id'], self.work_office_2.id)
        self.assertEqual(arr[1]['date'], datetime(2023, 5, 9).date())
        self.assertEqual(arr[2]['location_id'], self.work_office_2.id)
        self.assertEqual(arr[2]['date'], datetime(2023, 5, 30).date())

    def test_data_worklocation_2_partners(self):
        # 1 exception location fo each
        self.HrEmployeeLocation.create({
            # tuesday
            'start_date': '2023-05-16',
            'end_date_create': '2023-05-16',
            'work_location_id': self.work_office_1.id,
            'employee_id': self.employee_hruser_id,
        })
        self.HrEmployeeLocation.create({
            # tuesday
            'start_date': '2023-05-23',
            'end_date_create': '2023-05-23',
            'work_location_id': self.work_office_2.id,
            'employee_id': self.employee_hrmanager_id,
        })
        res_hruser = self.employee_hruser._get_worklocation(datetime(2023, 5, 1).date(), datetime(2023, 5, 30).date())
        arr_hruser = res_hruser[self.employee_hruser_id]
        res_hrmanager = self.employee_hrmanager._get_worklocation(datetime(2023, 5, 1).date(), datetime(2023, 5, 30).date())
        arr_hrmanager = res_hrmanager[self.employee_hrmanager_id]
        self.assertEqual(arr_hruser[0]['location_id'], self.work_office_1.id)
        self.assertEqual(arr_hruser[0]['date'], datetime(2023, 5, 16).date())
        self.assertEqual(arr_hrmanager[0]['location_id'], self.work_office_2.id)
        self.assertEqual(arr_hrmanager[0]['date'], datetime(2023, 5, 23).date())

    @freeze_time('2023-05-16')
    def test_data_worklocation_with_old_worklocation(self):
        with freeze_time('2023-05-01'):
            self.HrEmployeeLocation.create({
                # tuesday
                'start_date': '2023-05-09',
                'end_date_create': '2023-05-09',
                'work_location_id': self.work_office_2.id,
                'employee_id': self.employee_hruser_id,
                'weekly': True
            })
        self.HrEmployeeLocation.create({
            # tuesday
            'start_date': '2023-05-16',
            'end_date_create': '2023-05-16',
            'work_location_id': self.work_home.id,
            'employee_id': self.employee_hruser_id,
            'weekly': True
        })
        res_hruser = self.employee_hruser._get_worklocation(datetime(2023, 5, 1).date(), datetime(2023, 5, 30).date())
        arr_hruser = res_hruser[self.employee_hruser_id]
        self.assertEqual(arr_hruser[0]['location_id'], self.work_office_2.id)
        self.assertEqual(arr_hruser[0]['date'], datetime(2023, 5, 9).date())
        self.assertEqual(arr_hruser[1]['location_id'], self.work_home.id)
        self.assertEqual(arr_hruser[1]['date'], datetime(2023, 5, 16).date())
        self.assertEqual(arr_hruser[2]['location_id'], self.work_home.id)
        self.assertEqual(arr_hruser[2]['date'], datetime(2023, 5, 23).date())
        self.assertEqual(arr_hruser[3]['location_id'], self.work_home.id)
        self.assertEqual(arr_hruser[3]['date'], datetime(2023, 5, 30).date())
