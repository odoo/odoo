# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests import new_test_user, tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged('post_install', '-at_install')
class TestApprovalBackups(BaseCommon):
    _test_user_groups = ('base.group_user', 'hr.group_hr_user')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.approver_user = new_test_user(cls.env, login='approver', name='Approver')
        cls.backup_user = new_test_user(cls.env, login='backup', name='Backup')
        cls.approver_employee = cls.env['hr.employee'].create({
            'name': 'Approver',
            'user_id': cls.approver_user.id,
        })

    def test_search_approval_backups_without_employee_access(self):
        """The access rules of the approved records search the approvers by their backups:
        this must not depend on the access to the employees of the approvers."""
        self.approver_employee.approval_backups = self.backup_user
        stranger = new_test_user(self.env, login='stranger')
        self.env.invalidate_all()
        self.assertFalse(self.env['hr.employee'].with_user(stranger).has_access('read'))
        approvers = self.env['res.users'].with_user(stranger).search([
            ('approval_backups', 'in', self.backup_user.ids),
        ])
        self.assertEqual(approvers, self.approver_user)

    def test_set_own_approval_backups_from_preferences(self):
        self.env.invalidate_all()
        self.approver_user.with_user(self.approver_user).write({
            'approval_backups': [Command.link(self.backup_user.id)],
        })
        self.assertEqual(self.approver_employee.approval_backups, self.backup_user)

    def test_approval_fields_restricted_to_hr_officers(self):
        admin_without_hr = new_test_user(self.env, login='admin_without_hr', groups='base.group_system')
        employee = self.approver_employee.with_user(admin_without_hr)
        self.env.invalidate_all()
        # the employee itself is readable, only the approval fields are restricted
        self.assertEqual(employee.name, 'Approver')
        for field_name in ('approval_backups', 'is_approver'):
            with self.subTest(field_name=field_name), self.assertRaises(AccessError):
                employee.read([field_name])
