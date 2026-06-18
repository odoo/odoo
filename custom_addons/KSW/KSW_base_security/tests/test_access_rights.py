# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError

class TestAccessRights(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a contract type (required by om_hr_payroll)
        cls.contract_type = cls.env['hr.contract.type'].create({'name': 'Permanent'})
        
        # Create Employees
        cls.emp_a = cls.env['hr.employee'].create({'name': 'Manager A', 'type_id': cls.contract_type.id})
        cls.emp_b = cls.env['hr.employee'].create({'name': 'Supervisor B', 'parent_id': cls.emp_a.id, 'type_id': cls.contract_type.id})
        cls.emp_c = cls.env['hr.employee'].create({'name': 'Employee C', 'parent_id': cls.emp_b.id, 'type_id': cls.contract_type.id})
        
        # Create Users and link to Employees
        cls.user_a = cls.env['res.users'].create({
            'name': 'User A',
            'login': 'user_a',
            'email': 'a@example.com',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.emp_a.write({'user_id': cls.user_a.id})
        
        cls.user_b = cls.env['res.users'].create({
            'name': 'User B',
            'login': 'user_b',
            'email': 'b@example.com',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.emp_b.write({'user_id': cls.user_b.id})

        cls.user_c = cls.env['res.users'].create({
            'name': 'User C',
            'login': 'user_c',
            'email': 'c@example.com',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.emp_c.write({'user_id': cls.user_c.id})

    def test_01_employee_level(self):
        """Test 'Employee' group: can only see own record."""
        # Assign 'Employee' group to User B
        group_emp = self.env.ref('KSW_base_security.group_hr_employee_subordinate')
        self.user_b.write({'group_ids': [(4, group_emp.id)]})
        
        # Search employees as User B
        employees = self.env['hr.employee'].with_user(self.user_b).search([])
        self.assertIn(self.emp_b, employees)
        self.assertNotIn(self.emp_a, employees)
        self.assertNotIn(self.emp_c, employees)

    def test_02_supervisor_level(self):
        """Test 'Supervisor' group: can see own and immediate subordinates."""
        # Assign 'Supervisor' group to User B
        group_supervisor = self.env.ref('KSW_base_security.group_hr_employee_supervisor')
        self.user_b.write({'group_ids': [(4, group_supervisor.id)]})
        
        # Search employees as User B
        employees = self.env['hr.employee'].with_user(self.user_b).search([])
        self.assertIn(self.emp_b, employees)
        self.assertIn(self.emp_c, employees) # Immediate subordinate
        self.assertNotIn(self.emp_a, employees) # Manager

    def test_03_supervisor_cascading_level(self):
        """Test 'Supervisor Cascading' group: can see all subordinates."""
        # Assign 'Supervisor Cascading' group to User A
        group_cascading = self.env.ref('KSW_base_security.group_hr_employee_supervisor_cascading')
        self.user_a.write({'group_ids': [(4, group_cascading.id)]})
        
        # Search employees as User A
        employees = self.env['hr.employee'].with_user(self.user_a).search([])
        self.assertIn(self.emp_a, employees)
        self.assertIn(self.emp_b, employees) # Immediate
        self.assertIn(self.emp_c, employees) # Child of child (Cascading)

    def test_04_attendance_access(self):
        """Test attendance access for Supervisor."""
        # Create attendances
        att_b = self.env['hr.attendance'].create({'employee_id': self.emp_b.id, 'check_in': '2026-06-14 08:00:00'})
        att_c = self.env['hr.attendance'].create({'employee_id': self.emp_c.id, 'check_in': '2026-06-14 08:00:00'})
        
        # Assign Attendance Supervisor to User B
        group_att_supervisor = self.env.ref('KSW_base_security.group_hr_attendance_supervisor')
        self.user_b.write({'group_ids': [(4, group_att_supervisor.id)]})
        
        attendances = self.env['hr.attendance'].with_user(self.user_b).search([])
        self.assertIn(att_b, attendances)
        self.assertIn(att_c, attendances)
