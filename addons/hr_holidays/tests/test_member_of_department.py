# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from freezegun import freeze_time

from odoo import tests
from odoo.tests import TransactionCase


@tests.tagged('access_rights', 'post_install', '-at_install')
class TestMemberOfDepartment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.duck_guy = cls.env["res.users"].create({
            'name': 'Duck Guy',
            'login': 'duck_guy',
            'group_ids': cls.env.ref('hr.group_hr_manager').ids,
        })

        cls.duck_department, cls.other_department = cls.env["hr.department"].create([
            {"name": "DUCK"},
            {"name": "OTHER"},
        ])

        cls.duck_guy_emp, cls.other_dep_emp = cls.env["hr.employee"].create([
            {
                "name": "DUCK GUY",
                "department_id": cls.duck_department.id,
                "date_version": date(2026, 1, 1),
                "user_id": cls.duck_guy.id,
            },
            {
                "name": "OTHER GUY",
                "department_id": cls.duck_department.id,
                "date_version": date(2026, 1, 1),
            },
        ])
        cls.env["hr.version"].create({
            "employee_id": cls.other_dep_emp.id,
            "department_id": cls.other_department.id,
            "date_version": date(2026, 2, 1),
        })

    @freeze_time('2026-03-01')
    def test_other_dep_visibility(self):
        dep_emps = self.env["hr.employee"].with_user(self.duck_guy).search([("member_of_department", "=", True)])
        self.assertTrue(self.duck_guy_emp in dep_emps.employee_id)
        self.assertFalse(self.other_dep_emp in dep_emps.employee_id)
