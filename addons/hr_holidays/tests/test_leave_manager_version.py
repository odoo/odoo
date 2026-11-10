# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import freeze_time, new_test_user

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestLeaveManagerVersion(TestHrHolidaysCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager_user_1 = new_test_user(cls.env, login='manager_1', groups='base.group_user')
        cls.manager_user_2 = new_test_user(cls.env, login='manager_2', groups='base.group_user')
        cls.manager_1, cls.manager_2 = cls.env['hr.employee'].create([
            {'name': 'Manager 1', 'user_id': cls.manager_user_1.id},
            {'name': 'Manager 2', 'user_id': cls.manager_user_2.id},
        ])

    def test_leave_manager_is_versioned(self):
        employee = self.env['hr.employee'].create({
            'name': 'Employee', 'parent_id': self.manager_1.id, 'date_version': '2020-01-01',
        })
        old_version = employee.version_id
        self.assertEqual(old_version.leave_manager_id, self.manager_user_1)

        new_version = employee.create_version({'date_version': '2021-01-01'})
        self.assertEqual(employee.current_version_id, new_version)
        employee.parent_id = self.manager_2

        self.assertEqual(old_version.leave_manager_id, self.manager_user_1, "Past versions keep their approver")
        self.assertEqual(new_version.leave_manager_id, self.manager_user_2)
        self.assertEqual(employee.leave_manager_id, self.manager_user_2, "The current version drives the employee's approver")
        self.assertEqual(
            employee.with_context(version_id=old_version.id).leave_manager_id, self.manager_user_1,
        )
        self.assertEqual(self.env['hr.employee'].search([('leave_manager_id', '=', self.manager_user_1.id)]).ids, [])
        self.assertIn(employee, self.env['hr.employee'].search([('leave_manager_id', '=', self.manager_user_2.id)]))

    @freeze_time('2026-06-01')
    def test_archive_approver_keeps_past_versions(self):
        employee = self.env['hr.employee'].create({
            'name': 'Employee', 'parent_id': self.manager_1.id, 'date_version': '2020-01-01',
        })
        past_version = employee.version_id
        current_version = employee.create_version({'date_version': '2026-01-01'})
        future_version = employee.create_version({'date_version': '2030-01-01'})
        self.assertEqual(employee.current_version_id, current_version)
        self.assertEqual((past_version | current_version | future_version).leave_manager_id, self.manager_user_1)

        self.manager_1.action_archive()
        self.assertEqual(past_version.leave_manager_id, self.manager_user_1, "Past versions keep their approver history")
        self.assertFalse((current_version | future_version).leave_manager_id)
