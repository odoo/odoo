# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo.tests.common import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tools.float_utils import float_compare


@tagged('post_install', '-at_install', 'declarations_validation')
class TestPayslipValidation(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='be_comp'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.be').id,
            'vat': 'BE0897223670',
            'phone': '0471098765',
            'street': 'Test street',
            'city': 'Test city',
            'zip': '8292',
            'l10n_be_company_number': '0123456789',
            'l10n_be_revenue_code': '1234',
        })

        cls.env.user.tz = 'Europe/Brussels'

        cls.EMPLOYEES_COUNT = 5

        cls.resource_calendar_38_hours_per_week = cls.env['resource.calendar'].create([{
            'name': "Test Calendar : 38 Hours/Week",
            'company_id': cls.env.company.id,
            'hours_per_day': 7.6,
            'tz': "Europe/Brussels",
            'two_weeks_calendar': False,
            'hours_per_week': 38.0,
            'full_time_required_hours': 38.0,
            'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                'name': "Attendance",
                'dayofweek': dayofweek,
                'hour_from': hour_from,
                'hour_to': hour_to,
                'day_period': day_period,
                'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 8.0, 12.0, "morning"),
                ("0", 12.0, 13.0, "lunch"),
                ("0", 13.0, 16.6, "afternoon"),
                ("1", 8.0, 12.0, "morning"),
                ("1", 12.0, 13.0, "lunch"),
                ("1", 13.0, 16.6, "afternoon"),
                ("2", 8.0, 12.0, "morning"),
                ("2", 12.0, 13.0, "lunch"),
                ("2", 13.0, 16.6, "afternoon"),
                ("3", 8.0, 12.0, "morning"),
                ("3", 12.0, 13.0, "lunch"),
                ("3", 13.0, 16.6, "afternoon"),
                ("4", 8.0, 12.0, "morning"),
                ("4", 12.0, 13.0, "lunch"),
                ("4", 13.0, 16.6, "afternoon"),

            ]],
        }])

        cls.employees = cls.env['hr.employee'].create([{
            'name': "Test Employee %s" % (i),
            'private_street': 'Employee Street %s' %(i),
            'private_zip': '100%s' % (i),
            'private_city': 'Employee City %s' %(i),
            'private_country_id': cls.env.ref('base.be').id,
            'resource_calendar_id': cls.resource_calendar_38_hours_per_week.id,
            'company_id': cls.env.company.id,
            'km_home_work': 75,
            'certificate': 'master',
            'niss': '91072800%s' % (i) + str(97 - int('91072800%s' % (i)) % 97),
        } for i in range(cls.EMPLOYEES_COUNT)])

        cls.brand = cls.env['fleet.vehicle.model.brand'].create([{
            'name': "Test Brand"
        }])

        cls.model = cls.env['fleet.vehicle.model'].create([{
            'name': "Test Model",
            'brand_id': cls.brand.id
        }])

        cls.cars = cls.env['fleet.vehicle'].create([{
            'name': "Test Car %s" % (i),
            'license_plate': "TEST%s" % (i),
            'driver_id': cls.employees[i].work_contact_id.id,
            'company_id': cls.env.company.id,
            'model_id': cls.model.id,
            'first_contract_date': datetime.date(2020, 10, 8),
            'co2': 88.0,
            'car_value': 38000.0,
            'fuel_type': "diesel",
            'acquisition_date': datetime.date(2020, 1, 1)
        } for i in range(cls.EMPLOYEES_COUNT)])

        cls.vehicle_contract = cls.env['fleet.vehicle.log.contract'].create([{
            'name': "Test Contract %s" % (i),
            'vehicle_id': cls.cars[i].id,
            'company_id': cls.env.company.id,
            'start_date': datetime.date(2020, 10, 8),
            'expiration_date': datetime.date(2021, 10, 8),
            'state': "open",
            'cost_generated': 0.0,
            'cost_frequency': "monthly",
            'recurring_cost_amount_depreciated': 450.0
        } for i in range(cls.EMPLOYEES_COUNT)])

        cls.contracts = cls.env['hr.contract'].create([{
            'name': "Contract For Payslip Test %s" % (i),
            'employee_id': cls.employees[i].id,
            'resource_calendar_id': cls.resource_calendar_38_hours_per_week.id,
            'company_id': cls.env.company.id,
            'date_generated_from': datetime.datetime(2020, 9, 1, 0, 0, 0),
            'date_generated_to': datetime.datetime(2020, 9, 1, 0, 0, 0),
            'car_id': cls.cars[i].id,
            'structure_type_id': cls.env.ref('hr_contract.structure_type_employee_cp200').id,
            'date_start': datetime.date(2018, 12, 31),
            'wage': 2650.0,
            'wage_on_signature': 2650.0 + i * 100,
            'state': "open",
            'transport_mode_car': True,
            'fuel_card': 150.0,
            'internet': 38.0,
            'representation_fees': 150.0,
            'mobile': 30.0,
            'meal_voucher_amount': 7.45,
            'eco_checks': 250.0,
            'ip_wage_rate': 25.0,
            'ip': True,
            'rd_percentage': 100,
        } for i in range(cls.EMPLOYEES_COUNT)])

        cls.contracts.generate_work_entries(datetime.date(2021, 1, 1), datetime.date(2021, 12, 31))

        cls.batch = cls.env['hr.payslip.run'].create({
            'name': 'History Batch',
            'date_start': datetime.date(2021, 1, 1),
            'date_end': datetime.date(2021, 12, 31),
            'company_id': cls.env.company.id,
        })

        # Janvier 2021: Salary + Commissions
        # Février 2021: Salary
        # Mars 2021: Salary (10 unpaid days)
        # Avril 2021: Salary + Warrants (2 payslips)
        # Mai 2021: Salary (20 legal days)
        # Juin 2021: Salary + Double Holiday Pay (2 payslips)
        # Juillet 2021: Salary + Commissions
        # Aout 2021: Salary
        # Septembre 2021: Salary
        # Octobre 2021: Salary + Commissions
        # Novembre 2021: Salary
        # Décembre 2021: Salary (recup de decembre) + 13eme mois (2 payslips)
        cls.journal = cls.env['account.journal'].search([('type', '=', 'general')], limit=1)

        # Janvier 2021: Salary + Commissions
        cls.january_2021 = cls.env['hr.payslip'].create([{
            'name': 'Payslip Jan 2021 %s' % (i),
            'contract_id': cls.contracts[i].id,
            'date_from': datetime.datetime(2021, 1, 1),
            'date_to': datetime.datetime(2021, 1, 31),
            'employee_id': cls.employees[i].id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': cls.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
                'amount': 2000,
            })]
        } for i in range(cls.EMPLOYEES_COUNT)])

        # Février 2021: Salary
        cls.february_2021 = cls.env['hr.payslip'].create([{
            'name': 'Payslip Feb 2021',
            'contract_id': cls.contracts[i].id,
            'date_from': datetime.datetime(2021, 2, 1),
            'date_to': datetime.datetime(2021, 2, 28),
            'employee_id': cls.employees[i].id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        } for i in range(cls.EMPLOYEES_COUNT)])

        # Mars 2021: Salary (10 unpaid days)
        cls.march_2021 = cls.env['hr.payslip'].create([{
            'name': 'Payslip Mar 2021',
            'contract_id': cls.contracts[i].id,
            'date_from': datetime.datetime(2021, 3, 1),
            'date_to': datetime.datetime(2021, 3, 31),
            'employee_id': cls.employees[i].id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        } for i in range(cls.EMPLOYEES_COUNT)])

        # Avril 2021: Salary + Warrants (2 payslips)
        cls.april_2021 = cls.env['hr.payslip'].create([{
            'name': 'Payslip Apr 2021',
            'contract_id': cls.contracts[i].id,
            'date_from': datetime.datetime(2021, 4, 1),
            'date_to': datetime.datetime(2021, 4, 30),
            'employee_id': cls.employees[i].id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        } for i in range(cls.EMPLOYEES_COUNT)])

        cls.warrant_2021 = cls.env['hr.payslip'].create([{
            'name': 'Payslip Warrant 2021',
            'contract_id': cls.contracts[i].id,
            'date_from': datetime.datetime(2021, 4, 1),
            'date_to': datetime.datetime(2021, 4, 30),
            'employee_id': cls.employees[i].id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_structure_warrant').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': cls.env.ref('l10n_be_hr_payroll.cp200_other_input_warrant').id,
                'amount': 2000,
            })]
        } for i in range(cls.EMPLOYEES_COUNT)])

        # Mai 2021: Salary (20 legal days)
        cls.may_2021 = cls.env['hr.payslip'].create([{
            'name': 'Payslip May 2021',
            'contract_id': cls.contracts[i].id,
            'date_from': datetime.datetime(2021, 5, 1),
            'date_to': datetime.datetime(2021, 5, 31),
            'employee_id': cls.employees[i].id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        } for i in range(cls.EMPLOYEES_COUNT)])

        # Juin 2021: Salary + Double Holiday Pay (2 payslips)
        cls.june_2021 = cls.env['hr.payslip'].create([{
            'name': 'Payslip Jun 2021',
            'contract_id': cls.contracts[i].id,
            'date_from': datetime.datetime(2021, 6, 1),
            'date_to': datetime.datetime(2021, 6, 30),
            'employee_id': cls.employees[i].id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        } for i in range(cls.EMPLOYEES_COUNT)])

        cls.double_2021 = cls.env['hr.payslip'].create([{
            'name': 'Payslip Double 2021',
            'contract_id': cls.contracts[i].id,
            'date_from': datetime.datetime(2021, 6, 1),
            'date_to': datetime.datetime(2021, 6, 30),
            'employee_id': cls.employees[i].id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        } for i in range(cls.EMPLOYEES_COUNT)])

        # Juillet 2021: Salary + Commissions
        cls.july_2021 = cls.env['hr.payslip'].create([{
            'name': 'Payslip Jul 2021',
            'contract_id': cls.contracts[i].id,
            'date_from': datetime.datetime(2021, 7, 1),
            'date_to': datetime.datetime(2021, 7, 31),
            'employee_id': cls.employees[i].id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': cls.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
                'amount': 2000,
            })]
        } for i in range(cls.EMPLOYEES_COUNT)])

        # Aout 2021: Salary
        cls.august_2021 = cls.env['hr.payslip'].create([{
            'name': 'Payslip Aug 2021',
            'contract_id': cls.contracts[i].id,
            'date_from': datetime.datetime(2021, 8, 1),
            'date_to': datetime.datetime(2021, 8, 31),
            'employee_id': cls.employees[i].id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        } for i in range(cls.EMPLOYEES_COUNT)])

        # Septembre 2021: Salary
        cls.september_2021 = cls.env['hr.payslip'].create([{
            'name': 'Payslip Sep 2021',
            'contract_id': cls.contracts[i].id,
            'date_from': datetime.datetime(2021, 9, 1),
            'date_to': datetime.datetime(2021, 9, 30),
            'employee_id': cls.employees[i].id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        } for i in range(cls.EMPLOYEES_COUNT)])

        # Octobre 2021: Salary + Commissions
        cls.october_2021 = cls.env['hr.payslip'].create([{
            'name': 'Payslip Oct 2021',
            'contract_id': cls.contracts[i].id,
            'date_from': datetime.datetime(2021, 10, 1),
            'date_to': datetime.datetime(2021, 10, 31),
            'employee_id': cls.employees[i].id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': cls.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
                'amount': 2000,
            })]
        } for i in range(cls.EMPLOYEES_COUNT)])

        # Novembre 2021: Salary
        cls.november_2021 = cls.env['hr.payslip'].create([{
            'name': 'Payslip Nov 2021',
            'contract_id': cls.contracts[i].id,
            'date_from': datetime.datetime(2021, 11, 1),
            'date_to': datetime.datetime(2021, 11, 30),
            'employee_id': cls.employees[i].id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        } for i in range(cls.EMPLOYEES_COUNT)])

        # Décembre 2021: Salary + 13eme mois (2 payslips)
        cls.december_2021 = cls.env['hr.payslip'].create([{
            'name': 'Payslip Dec 2021',
            'contract_id': cls.contracts[i].id,
            'date_from': datetime.datetime(2021, 12, 1),
            'date_to': datetime.datetime(2021, 12, 31),
            'employee_id': cls.employees[i].id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
            'input_line_ids': [
                (0, 0, {
                    'input_type_id': cls.env.ref('l10n_be_hr_payroll.input_simple_december_pay').id,
                    'amount': 150,
                }), (0, 0, {
                    'input_type_id': cls.env.ref('l10n_be_hr_payroll.input_double_december_pay').id,
                    'amount': 100,
                })],
        } for i in range(cls.EMPLOYEES_COUNT)])

        cls.thirteen_2021 = cls.env['hr.payslip'].create([{
            'name': 'Payslip Thirteen Month 2021',
            'contract_id': cls.contracts[i].id,
            'date_from': datetime.datetime(2021, 12, 1),
            'date_to': datetime.datetime(2021, 12, 31),
            'employee_id': cls.employees[i].id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_thirteen_month').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        } for i in range(cls.EMPLOYEES_COUNT)])

        all_payslips = cls.january_2021 + cls.february_2021 + cls.march_2021 + cls.april_2021 + \
                       cls.warrant_2021 + cls.may_2021 + cls.june_2021 + cls.double_2021 + \
                       cls.july_2021 + cls.august_2021 + cls.september_2021 + cls.october_2021 + \
                       cls.november_2021 + cls.december_2021 + cls.thirteen_2021
        all_payslips.action_refresh_from_work_entries()
        all_payslips.action_payslip_done()

    def validate_results(self, declaration, results):
        fields_to_validate = [
            'pp_amount',
            'pp_amount_32',
            'pp_amount_33',
            'pp_amount_34',
            'taxable_amount',
            'taxable_amount_32',
            'taxable_amount_33',
            'taxable_amount_34',
            'deducted_amount',
            'deducted_amount_32',
            'deducted_amount_33',
            'deducted_amount_34',
            'capped_amount_34',
        ]
        error = []
        for field_name in fields_to_validate:
            declaration_value = declaration[field_name]
            if field_name not in results:
                error.append("Missing Checked Line: '%s' - %s," % (field_name, declaration_value))
                continue
            value = results[field_name]
            if float_compare(declaration_value, value, 2):
                error.append("Code: %s - Expected: %s - Reality: %s" % (field_name, value, declaration_value))
        if error:
            error.append("Declaration Actual Values: ")
            error.append("{")
            for field_name in fields_to_validate:
                error.append("    '%s': %s," % (field_name, declaration[field_name]))
            error.append("}")
        self.assertEqual(len(error), 0, '\n' + '\n'.join(error))

    def test_274_declaration(self):
        declaration = self.env['l10n_be.274_xx'].create({
            'year': 2021,
            'month': '1',
        })
        declaration_results = {
            'pp_amount': 5609.82,
            'pp_amount_32': 0.0,
            'pp_amount_33': 5609.82,
            'pp_amount_34': 0.0,
            'taxable_amount': 18309.8,
            'taxable_amount_32': 0.0,
            'taxable_amount_33': 18309.8,
            'taxable_amount_34': 0.0,
            'deducted_amount': 4487.86,
            'deducted_amount_32': 0.0,
            'deducted_amount_33': 4487.86,
            'deducted_amount_34': 0.0,
            'capped_amount_34': 0.0,
        }
        self.validate_results(declaration, declaration_results)

    def test_274_declaration_warrant(self):
        # Check warrants are included
        declaration = self.env['l10n_be.274_xx'].create({
            'year': 2021,
            'month': '4',
        })
        declaration_results = {
            'pp_amount': 6815.03,
            'pp_amount_32': 0.0,
            'pp_amount_33': 1465.03,
            'pp_amount_34': 0.0,
            'taxable_amount': 19616.8,
            'taxable_amount_32': 0.0,
            'taxable_amount_33': 9616.800000000001,
            'taxable_amount_34': 0.0,
            'deducted_amount': 1172.03,
            'deducted_amount_32': 0.0,
            'deducted_amount_33': 1172.03,
            'deducted_amount_34': 0.0,
            'capped_amount_34': 0.0,
        }
        self.validate_results(declaration, declaration_results)

    def test_274_declaration_cap(self):
        # Check bachelors are capped based on other employees
        self.employees[:3].write({'certificate': 'bachelor'})
        declaration = self.env['l10n_be.274_xx'].create({
            'year': 2021,
            'month': '1',
        })
        declaration_results = {
            'pp_amount': 5609.82,
            'pp_amount_32': 0.0,
            'pp_amount_33': 2333.49,
            'pp_amount_34': 3276.33,
            'taxable_amount': 18309.8,
            'taxable_amount_32': 0.0,
            'taxable_amount_33': 7509.71,
            'taxable_amount_34': 10800.09,
            'deducted_amount': 4487.86,
            'deducted_amount_32': 0.0,
            'deducted_amount_33': 1866.79,
            'deducted_amount_34': 2621.07,
            'capped_amount_34': 466.7,
        }
        self.validate_results(declaration, declaration_results)

    def test_274_declaration_december(self):
        # Check december pay recuperation
        declaration = self.env['l10n_be.274_xx'].create({
            'year': 2021,
            'month': '12',
        })
        declaration_results = {
            'pp_amount': 7686.88,
            'pp_amount_32': 0.0,
            'pp_amount_33': 1747.78,
            'pp_amount_34': 0.0,
            'taxable_amount': 23095.95,
            'taxable_amount_32': 0.0,
            'taxable_amount_33': 10268.800000000001,
            'taxable_amount_34': 0.0,
            'deducted_amount': 1398.22,
            'deducted_amount_32': 0.0,
            'deducted_amount_33': 1398.22,
            'deducted_amount_34': 0.0,
            'capped_amount_34': 0.0,
        }
        self.validate_results(declaration, declaration_results)

    def test_274_declaration_export(self):
        # Check exported data are the same than the computed fields
        def _to_eurocent(amount):
            return '%s' % int(amount * 100)

        self.employees[:3].write({'certificate': 'bachelor'})
        self.employees[3].write({'certificate': 'doctor'})

        declaration = self.env['l10n_be.274_xx'].create({
            'year': 2021,
            'month': '1',
        })
        declaration_results = {
            'pp_amount': 5609.82,
            'pp_amount_32': 1152.3,
            'pp_amount_33': 1181.19,
            'pp_amount_34': 3276.33,
            'taxable_amount': 18309.8,
            'taxable_amount_32': 3723.89,
            'taxable_amount_33': 3785.82,
            'taxable_amount_34': 10800.09,
            'deducted_amount': 4487.86,
            'deducted_amount_32': 921.84,
            'deducted_amount_33': 944.95,
            'deducted_amount_34': 2621.07,
            'capped_amount_34': 466.7,
        }
        self.validate_results(declaration, declaration_results)

        declaration_data = declaration._get_rendering_data()
        for data in declaration_data['declarations']:
            declaration_type = data['revenue_nature']
            suffix = '_%s' % (declaration_type) if declaration_type != 10 else ''

            xml_taxable = data['taxable_revenue']
            field_taxable = declaration['taxable_amount' + suffix]
            self.assertEqual(xml_taxable, _to_eurocent(field_taxable))

            xml_pp = data['prepayment']
            if not suffix:
                field_pp = declaration['pp_amount' + suffix]
                self.assertEqual(xml_pp, _to_eurocent(field_pp))
            else:
                if declaration_type != 34:
                    field_pp = -declaration['deducted_amount' + suffix]
                    self.assertEqual(xml_pp, _to_eurocent(field_pp))
                else:
                    field_pp = -declaration.capped_amount_34
                    self.assertTrue(int(xml_pp) / 100.0 - field_pp <= 0.01)

    def test_declarations_equivalence(self):
        # Check that the sum of all the 274.10 sheets over the year = 281.10
        declarations_274 = self.env['l10n_be.274_xx'].create([{
            'year': 2021,
            'month': str(i),
        } for i in range(1, 13)])
        total_declared_pp = sum(declarations_274.mapped('pp_amount'))

        declaration_281 = self.env['l10n_be.281_10'].create({
            'year': '2021',
        })
        data_281 = declaration_281.with_context(no_round_281_10=True)._get_rendering_data(self.employees)
        declared_pp = data_281['total_data']['r9014_controletotaal']
        self.assertAlmostEqual(total_declared_pp, declared_pp, places=2)

    def test_281_10_comeback(self):
        # Check that we use the old first_contract_date instead of
        # the new one
        self.assertEqual(self.employees[0].first_contract_date, datetime.date(2018, 12, 31))
        self.contracts[0].write({
            'date_end': datetime.date(2021, 12, 31),
            'state': 'close',
        })
        self.env['hr.contract'].create({
            'name': "New Contract For Payslip Test 0",
            'employee_id': self.employees[0].id,
            'resource_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'date_generated_from': datetime.datetime(2020, 9, 1, 0, 0, 0),
            'date_generated_to': datetime.datetime(2020, 9, 1, 0, 0, 0),
            'car_id': self.cars[0].id,
            'structure_type_id': self.env.ref('hr_contract.structure_type_employee_cp200').id,
            'date_start': datetime.date(2022, 3, 1),
            'wage': 2650.0,
            'wage_on_signature': 2650.0,
            'state': "open",
            'transport_mode_car': True,
            'fuel_card': 150.0,
            'internet': 38.0,
            'representation_fees': 150.0,
            'mobile': 30.0,
            'meal_voucher_amount': 7.45,
            'eco_checks': 250.0,
            'ip_wage_rate': 25.0,
            'ip': True,
            'rd_percentage': 100,
        })
        self.assertEqual(self.employees[0].first_contract_date, datetime.date(2022, 3, 1))
        declaration_281 = self.env['l10n_be.281_10'].create({
            'year': '2021',
        })
        data_281 = declaration_281.with_context(no_round_281_10=True)._get_rendering_data(self.employees)
        for employee_data in data_281['employees_data']:
            if employee_data['f2011_nationaalnr'] == self.employees[0].niss:
                self.assertEqual(employee_data['f10_2055_datumvanindienstt'], '31-12-2018')

    def test_281_10_departure(self):
        departure_notice = self.env['hr.payslip.employee.depature.notice'].create({
            'employee_id': self.employees[0].id,
            'leaving_type_id': self.env.ref('hr.departure_fired').id,
            'start_notice_period': datetime.date(2021, 12, 31),
            'end_notice_period': datetime.date(2021, 12, 31),
            'first_contract': datetime.date(2018, 12, 31),
            'notice_respect': 'without',
            'departure_description': 'foo',
        })

        # Termination Fees
        termination_payslip_id = departure_notice.compute_termination_fee()['res_id']
        termination_fees = self.env['hr.payslip'].browse(termination_payslip_id)
        termination_fees.compute_sheet()
        termination_fees.action_payslip_done()

        # Holiday Attests
        holiday_attest = self.env['hr.payslip.employee.depature.holiday.attests'].with_context(
            active_id=self.employees[0].id).create({})
        holiday_attest.write(holiday_attest.with_context(active_id=self.employees[0].id).default_get(holiday_attest._fields))
        holiday_pay_ids = holiday_attest.with_context(
            default_date_from=datetime.date(2021, 12, 1),
            default_date_to=datetime.date(2021, 12, 31),
        ).compute_termination_holidays()['domain'][0][2]
        holiday_pays = self.env['hr.payslip'].browse(holiday_pay_ids)
        holiday_pays.action_payslip_done()

        # 281.10 Declaration
        declaration_281 = self.env['l10n_be.281_10'].create({
            'year': '2021',
        })
        data_281 = declaration_281.with_context(no_round_281_10=True)._get_rendering_data(self.employees)
        for employee_data in data_281['employees_data']:
            if employee_data['f2011_nationaalnr'] == self.employees[0].niss:
                self.assertEqual(
                    employee_data['f10_2063_vervroegdvakantieg'],
                    holiday_pays._get_line_values(['GROSS'], compute_sum=True)['GROSS']['sum']['total'])
                self.assertEqual(
                    employee_data['f10_2065_opzeggingsreclasseringsverg'],
                    termination_fees._get_line_values(['GROSS'], compute_sum=True)['GROSS']['sum']['total'])
