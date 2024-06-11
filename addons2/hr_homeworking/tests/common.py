# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import common


class TestHrHomeworkingCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestHrHomeworkingCommon, cls).setUpClass()
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
