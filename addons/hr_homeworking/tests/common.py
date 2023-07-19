# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import common


class TestHrHomeworkingCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestHrHomeworkingCommon, cls).setUpClass()
        cls.env.user.tz = 'Europe/Brussels'

        # Test users to use through the various tests
        cls.user_hruser = mail_new_test_user(cls.env, login='armande', groups='base.group_user,hr.group_hr_user')
        cls.user_hruser_id = cls.user_hruser.id

        cls.user_hrmanager = mail_new_test_user(cls.env, login='bastien', groups='base.group_user,hr.group_hr_manager')
        cls.user_hrmanager_id = cls.user_hrmanager.id
        cls.user_hrmanager.tz = 'Europe/Brussels'

        cls.user_employee = mail_new_test_user(cls.env, login='david', groups='base.group_user')
        cls.user_employee_id = cls.user_employee.id

        # Hr Data
        Department = cls.env['hr.department'].with_context(tracking_disable=True)
        WorkLocation = cls.env['hr.work.location'].with_context(tracking_disable=True)
        main_partner_id = cls.env.ref('base.main_partner')
        cls.hr_dept = Department.create({
            'name': 'Human Resources',
        })
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
            'user_id': cls.user_employee_id,
            'department_id': cls.rd_dept.id,
        })
        cls.employee_emp_id = cls.employee_emp.id

        cls.employee_hruser = cls.env['hr.employee'].create({
            'name': 'Armande HrUser',
            'user_id': cls.user_hruser_id,
            'department_id': cls.rd_dept.id,
        })
        cls.employee_hruser_id = cls.employee_hruser.id

        cls.employee_hrmanager = cls.env['hr.employee'].create({
            'name': 'Bastien HrManager',
            'user_id': cls.user_hrmanager_id,
            'department_id': cls.hr_dept.id,
            'parent_id': cls.employee_hruser_id,
        })
        cls.employee_hrmanager_id = cls.employee_hrmanager.id

        cls.rd_dept.write({'manager_id': cls.employee_hruser_id})
