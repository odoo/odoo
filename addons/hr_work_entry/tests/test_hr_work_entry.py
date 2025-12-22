# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestHrWorkEntry(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create two companies
        cls.company_a = cls.env['res.company'].create({'name': 'Company A'})
        cls.company_b = cls.env['res.company'].create({'name': 'Company B'})
        cls.env.user.company_ids = [(6, 0, [cls.company_a.id, cls.company_b.id])]
        cls.env.user.company_id = cls.company_a.id
        # Create an employee for each company
        cls.employee_a = cls.env['hr.employee'].create({
            'name': 'Employee A',
            'company_id': cls.company_a.id,
        })
        cls.employee_b = cls.env['hr.employee'].create({
            'name': 'Employee B',
            'company_id': cls.company_b.id,
        })
        # Create a work entry type
        cls.work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Attendance',
            'code': 'ATTEND',
        })

    def test_work_entry_company_from_employee(self):
        """Test that work entry uses employee's company not the current user's company in vals."""
        work_entry = self.env['hr.work.entry'].create({
            'name': 'Test Work Entry',
            'employee_id': self.employee_b.id,
            'work_entry_type_id': self.work_entry_type.id,
            'date_start': '2024-01-01 08:00:00',
            'date_stop': '2024-01-01 16:00:00',
            'duration': 8,
        })
        self.assertEqual(
            work_entry.company_id, self.employee_b.company_id,
            "Work entry should use the employee's company not the current user's company.",
        )
