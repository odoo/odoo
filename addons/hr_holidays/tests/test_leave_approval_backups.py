# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta

from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user, tagged
from odoo.tools.safe_eval import expr_eval

from odoo.addons.base.tests.common import BaseCommon


def _next_working_day(days):
    day = date.today() + timedelta(days=days)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day


@tagged('post_install', '-at_install')
class TestLeaveApprovalBackups(BaseCommon):
    _test_user_groups = ('hr.group_hr_user',)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        employee_groups = 'hr_holidays.group_hr_holidays_employee'
        cls.approver_user = new_test_user(cls.env, login='approver', groups=employee_groups)
        cls.backup_user = new_test_user(cls.env, login='backup', groups='base.group_user')
        cls.employee_user = new_test_user(cls.env, login='employee', groups=employee_groups)
        cls.stranger_user = new_test_user(cls.env, login='stranger', groups=employee_groups)
        cls.approver_employee, cls.backup_employee, cls.employee, cls.stranger_employee = cls.env['hr.employee'].create([
            {'name': 'Approver', 'user_id': cls.approver_user.id},
            {'name': 'Backup', 'user_id': cls.backup_user.id},
            {'name': 'Employee', 'user_id': cls.employee_user.id, 'leave_manager_id': cls.approver_user.id},
            {'name': 'Stranger', 'user_id': cls.stranger_user.id},
        ])
        cls.work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Approved by the manager',
            'code': 'BACKUP_TEST',
            'count_as': 'absence',
            'requires_allocation': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
            'leave_validation_type': 'manager',
        })
        cls.approver_employee.approval_backups = cls.backup_user

    @classmethod
    def _create_leave(cls, employee, days=14):
        day = _next_working_day(days)
        return cls.env['hr.leave'].with_user(employee.user_id).create({
            'employee_id': employee.id,
            'work_entry_type_id': cls.work_entry_type.id,
            'request_date_from': day,
            'request_date_to': day,
        })

    def test_backup_gets_approver_group(self):
        """A light user added as backup gets the approver group, so becomes a regular user."""
        light_user = new_test_user(self.env, login='light', groups='base.group_user')
        self.assertEqual(light_user.role, 'light_user')
        self.approver_employee.approval_backups |= light_user
        self.assertTrue(light_user.has_group('hr_holidays.group_hr_holidays_responsible'))
        self.assertEqual(light_user.role, 'regular_user')

    def test_any_internal_user_can_be_approver(self):
        light_user = new_test_user(self.env, login='light', groups='base.group_user')
        self.assertEqual(light_user.role, 'light_user')
        Employee = self.env['hr.employee']
        picker_domain = expr_eval(Employee._fields['leave_manager_id'].ui_domain(Employee), {'company_id': self.company.id})
        self.assertIn(light_user, self.env['res.users'].search(picker_domain))
        self.stranger_employee.leave_manager_id = light_user
        self.assertTrue(light_user.has_group('hr_holidays.group_hr_holidays_responsible'))
        self.assertEqual(light_user.role, 'regular_user')

    def test_backup_can_approve(self):
        leave = self._create_leave(self.employee)
        self.env.invalidate_all()
        self.assertEqual(self.env['hr.leave'].with_user(self.backup_user).search([('id', '=', leave.id)]), leave)
        self.assertFalse(self.env['hr.leave'].with_user(self.stranger_user).search([('id', '=', leave.id)]))
        leave_as_backup = leave.with_user(self.backup_user)
        self.assertTrue(leave_as_backup.can_validate)
        self.assertTrue(leave_as_backup.can_refuse)
        leave_as_backup.action_approve()
        self.assertEqual(leave.state, 'validate')

    def test_backup_cannot_approve_own_leave(self):
        self.backup_employee.leave_manager_id = self.approver_user
        leave = self._create_leave(self.backup_employee)
        self.env.invalidate_all()
        leave_as_backup = leave.with_user(self.backup_user)
        self.assertFalse(leave_as_backup.can_validate)
        with self.assertRaises(UserError):
            leave_as_backup.action_approve()
        self.assertEqual(leave.state, 'confirm')

    def test_removed_backup_loses_access(self):
        leave = self._create_leave(self.employee)
        self.approver_employee.approval_backups = False
        self.env.invalidate_all()
        self.assertFalse(self.env['hr.leave'].with_user(self.backup_user).search([('id', '=', leave.id)]))
        with self.assertRaises(AccessError):
            leave.with_user(self.backup_user).action_approve()

    def test_no_activity_for_backup(self):
        leave = self._create_leave(self.employee)
        # the approval activity goes to the approver only
        self.assertEqual(leave.sudo().activity_ids.user_id, self.approver_user)

    def test_approver_group_kept_for_backups(self):
        """A former approver loses the approver group, unless it is the backup of an approver."""
        other_user = new_test_user(self.env, login='other', groups='base.group_user')
        for user in (self.backup_user, other_user):
            self.stranger_employee.leave_manager_id = user
            self.stranger_employee.leave_manager_id = self.approver_user
        self.assertTrue(self.backup_user.has_group('hr_holidays.group_hr_holidays_responsible'))
        self.assertFalse(other_user.has_group('hr_holidays.group_hr_holidays_responsible'))

    def test_is_approver(self):
        self.assertTrue(self.approver_employee.is_approver)
        self.assertFalse(self.stranger_employee.is_approver)
