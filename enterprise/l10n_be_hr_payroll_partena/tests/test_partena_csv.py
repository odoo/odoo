# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import datetime

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import file_open


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestL10nBEHrPartenaCSV(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.belgium = cls.env.ref('base.be')
        cls.company = cls.env['res.company'].create({
            'name': 'Test Belgium Company',
            'country_id': cls.belgium.id,
            'partena_code': '123456',
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'company_id': cls.company.id,
            'partena_code': '000006',
        })

        cls.contract = cls.env['hr.contract'].create({
            'name': 'Test Contract',
            'employee_id': cls.employee.id,
            'company_id': cls.company.id,
            'date_start': datetime(2024, 10, 1, 0, 0, 0),
            'date_end': datetime(2024, 10, 31, 0, 0, 0),
            'wage': 3000,
            'country_code': 'BE',
            'state': 'open',
        })

        cls.work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Test Work Entry Type',
            'code': 'WORKTEST',
            'partena_code': '55555',
        })

        cls.work_entry = cls.env['hr.work.entry'].create({
            'name': 'Work Entry',
            'company_id': cls.company.id,
            'employee_id': cls.employee.id,
            'contract_id': cls.contract.id,
            'work_entry_type_id': cls.work_entry_type.id,
            'date_start': cls.employee.contract_id.date_start,
            'date_stop': cls.employee.contract_id.date_end,
        })
        cls.work_entry.action_validate()

    def _check_csv_file(self, expected_csv_path, current_export_file):
        current_file = base64.b64decode(current_export_file).decode()
        current_values = [line.split(';') for line in current_file.split('\n') if line]

        with file_open(expected_csv_path, 'rb') as csv_file:
            expected_file = csv_file.read().decode()
            expected_values = [line.split(';') for line in expected_file.split('\n') if line]

        self.assertEqual(current_values, expected_values)

    def test_BE_partena_work_entry_type_code_verification(self):
        """Test Partena code validation rules (must be exactly 5 chars) for hr.work.entry.type"""
        with self.assertRaises(ValidationError):
            self.work_entry_type.write({'partena_code': '1234'})
        with self.assertRaises(ValidationError):
            self.work_entry_type.write({'partena_code': '123456'})
        self.work_entry_type.write({'partena_code': '54321'})
        self.assertEqual(self.work_entry_type.partena_code, '54321', "Partena code for WE should be valid when 5 characters long")

    def test_BE_partena_employee_code_verification(self):
        """Test Partena code validation rules (must be exactly 6 chars) for hr.employee"""
        with self.assertRaises(ValidationError):
            self.employee.write({'partena_code': '12345'})
        with self.assertRaises(ValidationError):
            self.employee.write({'partena_code': '1234567'})
        self.employee.write({'partena_code': '654321'})
        self.assertEqual(self.employee.partena_code, '654321', "Partena code for employee should be valid when 6 characters long")

    def test_BE_partena_company_code_verification(self):
        """Test Partena code validation rules (must be exactly 6 chars) for res.company"""
        with self.assertRaises(ValidationError):
            self.company.write({'partena_code': '12345'})
        with self.assertRaises(ValidationError):
            self.company.write({'partena_code': '1234567'})
        self.company.write({'partena_code': '654321'})
        self.assertEqual(self.company.partena_code, '654321', "Partena code for company should be valid when 6 characters long")

    def test_BE_partena_CSV_generation(self):
        export = self.env['l10n.be.hr.payroll.export.partena'].create({
            'company_id': self.company.id,
            'reference_month': '10',
            'reference_year': 2024,
        })
        export.action_populate()

        self.assertTrue(export.eligible_employee_line_ids)
        self.assertIn(self.employee, export.eligible_employee_line_ids.employee_id)

        export.action_export_file()
        self.assertTrue(export.export_file)

        expected_csv_path = 'l10n_be_hr_payroll_partena/tests/test_csv_file/test_csv_partena.csv'
        self._check_csv_file(expected_csv_path, export.export_file)

    def test_BE_partena_CSV_generation_multicompany(self):
        """Test that the values in the CSV are correct in multicompany mode."""

        company_2 = self.env['res.company'].create({
            'name': 'Second Belgium Company',
            'country_id': self.belgium.id,
            'partena_code': '567890',
        })

        export = self.env['l10n.be.hr.payroll.export.partena'].with_company(company_2).create({
            'company_id': self.company.id,
            'reference_month': '10',
            'reference_year': 2024,
        })
        export.action_populate()

        self.assertTrue(export.eligible_employee_line_ids)
        self.assertIn(self.employee, export.eligible_employee_line_ids.employee_id)

        export.action_export_file()
        self.assertTrue(export.export_file)

        expected_csv_path = 'l10n_be_hr_payroll_partena/tests/test_csv_file/test_csv_partena.csv'
        self._check_csv_file(expected_csv_path, export.export_file)
