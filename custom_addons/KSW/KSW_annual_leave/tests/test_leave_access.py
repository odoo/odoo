# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

class TestLeaveAccess(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create Employees
        cls.emp_a = cls.env['hr.employee'].create({'name': 'Manager A'})
        cls.emp_b = cls.env['hr.employee'].create({'name': 'Supervisor B', 'parent_id': cls.emp_a.id})
        cls.emp_c = cls.env['hr.employee'].create({'name': 'Employee C', 'parent_id': cls.emp_b.id})
        
        # Create Users and link to Employees
        cls.user_a = cls.env['res.users'].create({
            'name': 'User A',
            'login': 'user_a_leave',
            'email': 'a_leave@example.com',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.emp_a.write({'user_id': cls.user_a.id})
        
        cls.user_b = cls.env['res.users'].create({
            'name': 'User B',
            'login': 'user_b_leave',
            'email': 'b_leave@example.com',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.emp_b.write({'user_id': cls.user_b.id})

        cls.user_c = cls.env['res.users'].create({
            'name': 'User C',
            'login': 'user_c_leave',
            'email': 'c_leave@example.com',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.emp_c.write({'user_id': cls.user_c.id})

        # Create leave types and leaves
        cls.leave_type = cls.env['hr.leave.type'].sudo().create({
            'name': 'Generic Leave',
            'requires_allocation': 'no',
        })
        
        cls.leave_a = cls.env['hr.leave'].sudo().create({
            'name': 'Leave A',
            'employee_id': cls.emp_a.id,
            'holiday_status_id': cls.leave_type.id,
            'request_date_from': '2026-06-15',
            'request_date_to': '2026-06-15',
        })
        cls.leave_b = cls.env['hr.leave'].sudo().create({
            'name': 'Leave B',
            'employee_id': cls.emp_b.id,
            'holiday_status_id': cls.leave_type.id,
            'request_date_from': '2026-06-15',
            'request_date_to': '2026-06-15',
        })
        cls.leave_c = cls.env['hr.leave'].sudo().create({
            'name': 'Leave C',
            'employee_id': cls.emp_c.id,
            'holiday_status_id': cls.leave_type.id,
            'request_date_from': '2026-06-15',
            'request_date_to': '2026-06-15',
        })

    def test_01_leave_view_self(self):
        """Test 'Self' viewing group."""
        # By default base.group_user should see own
        leaves = self.env['hr.leave'].with_user(self.user_b).search([])
        self.assertIn(self.leave_b, leaves)
        self.assertNotIn(self.leave_a, leaves)
        self.assertNotIn(self.leave_c, leaves)

    def test_02_leave_view_supervisor(self):
        """Test 'Supervisor' (immediate) viewing group."""
        group_supervisor = self.env.ref('KSW_annual_leave.group_leave_view_supervisor')
        self.user_b.write({'group_ids': [(4, group_supervisor.id)]})
        
        leaves = self.env['hr.leave'].with_user(self.user_b).search([])
        self.assertIn(self.leave_b, leaves) # Own
        self.assertIn(self.leave_c, leaves) # Immediate subordinate
        self.assertNotIn(self.leave_a, leaves) # Manager

    def test_03_leave_view_supervisor_cascading(self):
        """Test 'Supervisor Cascading' viewing group."""
        group_cascading = self.env.ref('KSW_annual_leave.group_leave_view_supervisor_cascading')
        self.user_a.write({'group_ids': [(4, group_cascading.id)]})
        
        leaves = self.env['hr.leave'].with_user(self.user_a).search([])
        self.assertIn(self.leave_a, leaves) # Own
        self.assertIn(self.leave_b, leaves) # Immediate
        self.assertIn(self.leave_c, leaves) # Recursive
