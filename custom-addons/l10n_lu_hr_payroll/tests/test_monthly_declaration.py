# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from datetime import date
from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestLuPayrollCommon


@freeze_time('2022-12-31')
@tagged('post_install_l10n', 'post_install', '-at_install')
class TestLuMonthlyDeclaration(TestLuPayrollCommon):
    def setUp(self):
        super().setUp()

        self.contract_david.generate_work_entries(date(2022, 3, 1), date(2020, 3, 31))
        self.payslip_run = self.env['hr.payslip.run'].create({
            'name': 'March 2022',
            'date_start': '2022-3-1',
            'date_end': '2022-3-31',
            'company_id': self.lux_company.id,
            'state': 'verify',
        })
        self.payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.employee_david.id)],
        })
        self.payslip_employee.with_context(active_id=self.payslip_run.id).compute_sheet()

    def test_01_generate_missing_identification(self):
        wizard = self.env['l10n.lu.monthly.declaration.wizard'].create({
            'month': '3',
            'year': '2022',
        })

        self.employee_david.identification_id = False
        with self.assertRaisesRegex(UserError, r'missing an identification number'), self.cr.savepoint():
            wizard.action_generate_declaration()

        self.employee_david.identification_id = 111111111
        wizard.action_generate_declaration()

        self.lux_company.l10n_lu_seculine = False
        with self.assertRaisesRegex(UserError, r'Missing (.+) SECUline numbers'), self.cr.savepoint():
            wizard.action_generate_declaration()

        self.lux_company.l10n_lu_seculine = 999999999

        self.lux_company.l10n_lu_official_social_security = False
        with self.assertRaisesRegex(UserError, r'Missing (.+) social security'), self.cr.savepoint():
            wizard.action_generate_declaration()

    def test_02_company_identification(self):
        wizard = self.env['l10n.lu.monthly.declaration.wizard'].create({
            'month': '3',
            'year': '2022',
        })
        wizard.action_generate_declaration()

        declaration = base64.decodebytes(wizard.decsal_file).decode('utf8')
        declaration_lines = declaration.split('\r\n')

        company_ssn = self.lux_company.l10n_lu_official_social_security
        company_seculine = self.lux_company.l10n_lu_seculine
        self.assertEqual(declaration_lines[0], f"0;{company_ssn};{company_seculine}")

    def test_03_multiple_contracts(self):
        self.payslip_run.action_draft()

        madison_employee = self.env['hr.employee'].create({
            'name': 'Madison',
            'company_id': self.lux_company.id,
            'identification_id': 987654321,
        })
        madison_contract1 = self.env['hr.contract'].create({
            'name': 'Madison Contract',
            'employee_id': madison_employee.id,
            'company_id': self.lux_company.id,
            'structure_type_id': self.env.ref('l10n_lu_hr_payroll.structure_type_employee_lux').id,
            'date_start': '2022-1-1',
            'date_end': '2022-3-11',
            'wage': 4000.0,
            'state': 'close',
        })

        madison_contract2 = madison_contract1.copy({
            'date_start': '2022-3-21',
            'date_end': False,
            'wage': 4400.0,
            'state': 'open',
        })
        laura_employee = self.env['hr.employee'].create({
            'name': 'laura',
            'company_id': self.lux_company.id,
            'identification_id': 143111140,
        })
        laura_contract1 = self.env['hr.contract'].create({
            'name': 'laura Contract',
            'employee_id': laura_employee.id,
            'company_id': self.lux_company.id,
            'structure_type_id': self.env.ref('l10n_lu_hr_payroll.structure_type_employee_lux').id,
            'date_start': '2022-3-4',
            'date_end': '2022-3-15',
            'wage': 4000.0,
            'state': 'close',
        })
        contracts = madison_contract1 | madison_contract2 | laura_contract1 | self.contract_david

        self.env['hr.leave'].create({
            'name': 'such bad weather no work',
            'employee_id': madison_employee.id,
            'holiday_status_id': self.env.ref('l10n_lu_hr_payroll.holiday_status_situational_unemployment').id,
            'request_date_from': '2022-03-09',
            'request_date_to': '2022-03-09',
        })
        contracts.generate_work_entries(date(2022, 3, 1), date(2022, 3, 31))

        batch = self.env['hr.payslip.run'].create({
            'name': 'March 2022',
            'date_start': '2022-3-1',
            'date_end': '2022-3-31',
            'company_id': self.lux_company.id,
            'state': 'verify',
        })
        payslip_employees = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.employee_david.id), (4, madison_employee.id), (4, laura_employee.id)],
        })
        payslip_employees.with_context(active_id=batch.id).compute_sheet()

        wizard = self.env['l10n.lu.monthly.declaration.wizard'].create({
            'month': '3',
            'year': '2022',
        })

        with self.assertRaisesRegex(UserError, r'^Missing amounts'), self.env.cr.savepoint():
            wizard.action_generate_declaration()

        self.assertEqual(len(wizard.situational_unemployment_ids), 1)
        self.assertEqual(wizard.situational_unemployment_ids.employee_id, madison_employee)
        self.assertEqual(wizard.situational_unemployment_ids.hours, 8)

        wizard.situational_unemployment_ids.amount = 120
        wizard.action_generate_declaration()

        declaration = base64.decodebytes(wizard.decsal_file).decode('utf8')
        declaration_lines = declaration.split('\r\n')

        self.assertEqual(len(declaration_lines), 4, "Should have 4 lines, 1 for company identification + 1 for each employee")

        employee_values = {
            laura_employee.id: {
                1: self.lux_company.l10n_lu_official_social_security,
                3: 202203,  # period reference YYYYMM
                4: 139130,  # 4000 (wage) / 23 (number working days) * 8 (worked days)
                5: 64,  # 8 days * 8h
                13: '04',  # period start date - start of contract
                14: 15,  # period end date - end of contract
            },
            madison_employee.id: {
                0: 1,
                1: self.lux_company.l10n_lu_official_social_security,
                4: 311304,
                5: 136,  # 17 days (9 days 1st contract + 9 days 2nd contract - 1 day unemployment) * 8h
                10: 8,  # 1 day of situational unemployment
                11: 12000,  # 120.00 encoded in the wizard
                13: '01',  # period start date - start of month
                14: 31,  # period end date - end of month
            },
            self.employee_david.id: {
                1: self.lux_company.l10n_lu_official_social_security,
                2: self.employee_david.identification_id,
                4: int((self.contract_david.wage) * 100),
                5: 184,  # 23 days * 8h
                10: 0,
                11: 0,
                13: '01',  # period start date - start of month
                14: 31,  # period end date - end of month
            },
        }

        employees_done = []
        for line in declaration_lines[1:]:
            fields = line.split(';')
            self.assertEqual(len(fields), 20)

            employee_id = int(fields[-1])
            if employee_id in employees_done:
                raise Exception('There should be only one line per employee')
            employees_done.append(employee_id)

            for idx, val in employee_values[employee_id].items():
                self.assertEqual(str(val), fields[idx], f"Error: expected {val} on field #{idx} found {fields[idx]} instead: \n{line}")

    def test_04_multiple_contracts_different_structures(self):
        structure_type = self.env['hr.payroll.structure.type'].create({'name': 'Lux: Test'})
        pay_structure = self.env['hr.payroll.structure'].create({
            'name': 'Lux Structure Test',
            'type_id': structure_type.id,
        })
        structure_type.default_struct_id = pay_structure

        jade_employee = self.env['hr.employee'].create({
            'name': 'Jade',
            'company_id': self.lux_company.id,
            'identification_id': 987654321,
        })
        jade_contract1 = self.env['hr.contract'].create({
            'name': 'Jade Contract',
            'employee_id': jade_employee.id,
            'company_id': self.lux_company.id,
            'structure_type_id': structure_type.id,
            'date_start': '2022-1-1',
            'date_end': '2022-3-11',
            'wage': 3000.0,
            'state': 'close',
        })
        jade_contract2 = jade_contract1.copy({
            'date_start': '2022-3-21',
            'date_end': False,
            'wage': 4400.0,
            'state': 'open',
            'structure_type_id': self.env.ref('l10n_lu_hr_payroll.structure_type_employee_lux').id,
        })
        contracts = jade_contract1 | jade_contract2
        contracts.generate_work_entries(date(2022, 3, 1), date(2022, 3, 31))

        batch = self.env['hr.payslip.run'].create({
            'name': 'March 2022',
            'date_start': '2022-3-1',
            'date_end': '2022-3-31',
            'company_id': self.lux_company.id,
            'state': 'verify',
        })
        payslip_employees = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.employee_david.id), (4, jade_employee.id)],
        })
        payslip_employees.with_context(active_id=batch.id).compute_sheet()

        wizard = self.env['l10n.lu.monthly.declaration.wizard'].create({
            'month': '3',
            'year': '2022',
        })
        wizard.action_generate_declaration()

        declaration = base64.decodebytes(wizard.decsal_file).decode('utf8')
        declaration_lines = declaration.split('\r\n')

        self.assertNotEqual(jade_contract1.structure_type_id, jade_contract2.structure_type_id)
        self.assertEqual(len(declaration_lines), 4)  # 1 for company identification + 1 for David + 2 for Jade

        jade_entries = [
            line.split(';')
            for line in declaration_lines
            if int(line.split(';')[-1]) == jade_employee.id
        ]
        self.assertEqual(len(jade_entries), 2)

        self.assertEqual(jade_entries[0][13], "01")
        self.assertEqual(jade_entries[0][14], "11")

        self.assertEqual(jade_entries[1][13], "21")
        self.assertEqual(jade_entries[1][14], "31")
