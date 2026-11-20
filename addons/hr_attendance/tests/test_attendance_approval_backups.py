# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged('post_install', '-at_install')
class TestAttendanceApprovalBackups(BaseCommon):
    _test_user_groups = ('base.group_user', 'hr.group_hr_user', 'hr_attendance.group_hr_attendance_user')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.approver_user = new_test_user(cls.env, login='approver')
        cls.backup_user = new_test_user(cls.env, login='backup')
        cls.stranger_user = new_test_user(cls.env, login='stranger', groups='base.group_user,hr_attendance.group_hr_attendance_officer')
        cls.approver_employee, cls.backup_employee, cls.employee, cls.stranger_employee = cls.env['hr.employee'].create([
            {'name': 'Approver', 'user_id': cls.approver_user.id},
            {'name': 'Backup', 'user_id': cls.backup_user.id, 'attendance_manager_id': cls.approver_user.id},
            {'name': 'Employee', 'attendance_manager_id': cls.approver_user.id},
            {'name': 'Stranger', 'user_id': cls.stranger_user.id},
        ])
        cls.approver_employee.approval_backups = cls.backup_user
        cls.attendance, cls.backup_attendance = cls.env['hr.attendance'].create([{
            'employee_id': employee.id,
            'check_in': datetime(2026, 11, 2, 8),
            'check_out': datetime(2026, 11, 2, 12),
        } for employee in (cls.employee, cls.backup_employee)])

    def test_backup_gets_officer_group(self):
        self.assertTrue(self.backup_user.has_group('hr_attendance.group_hr_attendance_officer'))
        self.assertEqual(self.backup_user.role, 'regular_user')

    def test_any_internal_user_can_be_approver(self):
        light_user = new_test_user(self.env, login='light', groups='base.group_user')
        self.assertEqual(light_user.role, 'light_user')
        self.stranger_employee.attendance_manager_id = light_user
        self.assertTrue(light_user.has_group('hr_attendance.group_hr_attendance_officer'))
        self.assertEqual(light_user.role, 'regular_user')

    def test_backup_can_manage_attendances(self):
        self.env.invalidate_all()
        attendance = self.attendance.with_user(self.backup_user)
        self.assertEqual(attendance.search([('id', '=', self.attendance.id)]), self.attendance)
        self.assertTrue(attendance.is_manager)
        attendance.check_out = datetime(2026, 11, 2, 13)
        self.assertEqual(self.attendance.check_out, datetime(2026, 11, 2, 13))
        # an officer who is neither the approver nor its backup
        self.assertFalse(self.attendance.with_user(self.stranger_user).search([('id', '=', self.attendance.id)]))

    def test_backup_does_not_manage_own_attendances(self):
        self.env.invalidate_all()
        self.assertFalse(self.backup_attendance.with_user(self.backup_user).is_manager)

    def test_removed_backup_loses_access(self):
        self.approver_employee.approval_backups = False
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            self.attendance.with_user(self.backup_user).check_out = datetime(2026, 11, 2, 13)

    def test_officer_group_kept_for_backups(self):
        """A former approver loses the officer group, unless it is the backup of an approver."""
        other_user = new_test_user(self.env, login='other')
        for user in (self.backup_user, other_user):
            self.stranger_employee.attendance_manager_id = user
            self.stranger_employee.attendance_manager_id = self.approver_user
        self.assertTrue(self.backup_user.has_group('hr_attendance.group_hr_attendance_officer'))
        self.assertFalse(other_user.has_group('hr_attendance.group_hr_attendance_officer'))
