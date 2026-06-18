from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from odoo import fields

class TestLeaveApproval(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create users
        cls.hr_manager_user = cls.env['res.users'].create({
            'name': 'HR Manager User',
            'login': 'hr_manager_user',
            'group_ids': [(4, cls.env.ref('hr_holidays.group_hr_holidays_manager').id)]
        })
        cls.dm_user = cls.env['res.users'].create({
            'name': 'Direct Manager User',
            'login': 'dm_user',
            'group_ids': [(4, cls.env.ref('hr_holidays.group_hr_holidays_user').id)]
        })
        cls.other_user = cls.env['res.users'].create({
            'name': 'Other User',
            'login': 'other_user',
            'group_ids': [(4, cls.env.ref('hr_holidays.group_hr_holidays_user').id)]
        })
        cls.employee_user = cls.env['res.users'].create({
            'name': 'Employee User',
            'login': 'employee_user',
            'group_ids': [(4, cls.env.ref('base.group_user').id)]
        })

        # Set HR Manager in settings
        cls.env.company.x_hr_leave_manager_id = cls.hr_manager_user

        # Create employees
        cls.dm_employee = cls.env['hr.employee'].create({
            'name': 'DM Employee',
            'user_id': cls.dm_user.id,
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Subordinate Employee',
            'user_id': cls.employee_user.id,
            'parent_id': cls.dm_employee.id,
        })

        # Non-annual leave type
        cls.leave_type = cls.env['hr.leave.type'].search([('is_annual_leave', '=', False)], limit=1)
        cls.leave_type.write({'leave_validation_type': 'both'})
        
    def test_01_non_annual_approval_flow(self):
        """Test strict 2-step approval for non-annual leaves."""
        # Create leave request (starts in 'confirm' state in Odoo 19)
        leave = self.env['hr.leave'].sudo().create({
            'name': 'Sick Leave',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee.id,
            'request_date_from': fields.Date.today(),
            'request_date_to': fields.Date.today(),
        })
        self.assertEqual(leave.state, 'confirm')

        # 1. Other user (not DM) tries to approve -> should fail
        with self.assertRaises(UserError):
            leave.with_user(self.other_user).action_approve()

        # 2. HR Manager (not DM) tries to approve -> should fail
        with self.assertRaises(UserError):
            leave.with_user(self.hr_manager_user).action_approve()

        # 3. DM tries to approve -> should succeed
        leave.with_user(self.dm_user).action_approve()
        self.assertEqual(leave.state, 'validate1')

        # 4. DM (not HR Manager) tries to validate -> should fail
        with self.assertRaises(UserError):
            leave.with_user(self.dm_user).action_validate()

        # 5. HR Manager tries to validate -> should succeed
        leave.with_user(self.hr_manager_user).action_validate()
        self.assertEqual(leave.state, 'validate')

    def test_02_responsible_for_approval(self):
        """Test that the responsible user for activities is correct at each step."""
        leave = self.env['hr.leave'].sudo().create({
            'name': 'Sick Leave',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee.id,
            'request_date_from': fields.Date.today(),
            'request_date_to': fields.Date.today(),
        })
        
        # At confirm state, responsible should be DM
        self.assertEqual(leave._get_responsible_for_approval(), self.dm_user)
        
        # Approve 1st step
        leave.with_user(self.dm_user).action_approve()
        
        # At validate1 state, responsible should be HR Manager
        self.assertEqual(leave._get_responsible_for_approval(), self.hr_manager_user)
