# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestHrPayrollExportPrisma(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.belgium = cls.env.ref('base.be')
        cls.company = cls.env['res.company'].create({
            'name': 'Test Belgium Company',
            'country_id': cls.belgium.id,
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'prisma_code': '12345',
            'company_id': cls.company.id,
        })

        cls.contract = cls.env['hr.contract'].create({
            'name': 'Test Contract',
            'employee_id': cls.employee.id,
            'hr_responsible_id': cls.env.ref('base.user_admin').id,
            'company_id': cls.company.id,
            'date_start': datetime(2024, 10, 1, 0, 0, 0),
            'date_end': datetime(2024, 10, 31, 0, 0, 0),
            'wage': 3000,
        })

        cls.work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Test Work Entry Type',
            'code': 'WORKTEST',
            'prisma_code': '321',
        })

    def test_invalid_prisma_code_length(self):
        """Test invalid Prisma code length (>5) for hr.employee"""
        with self.assertRaises(ValidationError):
            self.employee.write({'prisma_code': '123456'})

    def test_auto_zfill_short_prisma_code(self):
        """Test Prisma code shorter than 5 digits is zero-padded"""
        self.employee.write({'prisma_code': '12'})
        self.assertEqual(self.employee.prisma_code, '00012', "Prisma code should be zero-padded to length 5")

    def test_work_entry_type_prisma_code_validation(self):
        """Test Prisma code validation rules (2-4 chars) for hr.work.entry.type"""
        with self.assertRaises(ValidationError):
            self.work_entry_type.write({'prisma_code': '1'})
        with self.assertRaises(ValidationError):
            self.work_entry_type.write({'prisma_code': '12345'})
        self.work_entry_type.write({'prisma_code': '4321'})
        self.assertEqual(self.work_entry_type.prisma_code, '4321', "Prisma code should be valid when 2–4 chars long")

    def test_company_prisma_code_validation(self):
        """Test Prisma code validation rules (must be exactly 8 chars) for res.company"""
        with self.assertRaises(ValidationError):
            self.company.write({'prisma_code': '1234567'})
        with self.assertRaises(ValidationError):
            self.company.write({'prisma_code': '123456789'})
        self.company.write({'prisma_code': '87654321'})
        self.assertEqual(self.company.prisma_code, '87654321', "Prisma code should be valid when 8 characters long")

    def test_prisma_code_in_different_company(self):
        """Test the same Prisma code in a different company"""
        other_company = self.env['res.company'].create({
            'name': 'Other Company',
            'country_id': self.belgium.id,
        })
        other_employee = self.env['hr.employee'].create({
            'name': 'Employee in Other Company',
            'company_id': other_company.id,
            'prisma_code': '12345',
        })
        self.assertEqual(other_employee.prisma_code, '12345', "Prisma code should be valid in a different company.")

    def test_full_prisma_export_flow(self):
        """Test creating a Prisma export, populating, and generating the export file without errors"""
        self.company.prisma_code = '87654321'
        self.contract.update({
            'state': 'open',
        })
        self.employee.update({
            'contract_id': self.contract.id,
        })

        work_entry = self.env['hr.work.entry'].create({
            'name': 'Work Entry',
            'company_id': self.company.id,
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'work_entry_type_id': self.work_entry_type.id,
            'date_start': self.employee.contract_id.date_start,
            'date_stop': self.employee.contract_id.date_end,
        })
        work_entry.action_validate()

        export = self.env['l10n.be.hr.payroll.export.prisma'].with_company(self.company.id).create({
            'company_id': self.company.id,
            'reference_month': '10',
            'reference_year': 2024,
        })
        export.action_populate()

        self.assertTrue(export.eligible_employee_line_ids)
        self.assertIn(self.employee, export.eligible_employee_line_ids.employee_id)

        export.action_export_file()
        self.assertTrue(export.export_file)
