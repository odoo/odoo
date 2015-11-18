# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os

from datetime import timedelta

from odoo import fields, report as odoo_report, tools
from odoo.tests import common
from odoo.tools import test_reports


class TestHrPayroll(common.TransactionCase):

    def setUp(self):
        super(TestHrPayroll, self).setUp()

        self.HrPayslip = self.env['hr.payslip']
        self.HrPayslipInput = self.env['hr.payslip.input']
        self.HrPayslipEmployees = self.env['hr.payslip.employees']
        self.HrEmployee = self.env['hr.employee']
        self.HrPayrollStructure = self.env['hr.payroll.structure']
        self.HrContract = self.env['hr.contract']
        self.HrPayslipRun = self.env['hr.payslip.run']
        self.PayslipLinesContributionRegister = self.env['payslip.lines.contribution.register']
        self.menu_dept_tree_id = self.ref('hr_payroll.menu_department_tree')
        self.country_id = self.ref('base.be')
        self.main_company_id = self.ref('base.main_company')
        self.rd_department_id = self.ref('hr.dep_rd')
        self.rule_id_1 = self.ref('hr_payroll.hr_salary_rule_houserentallowance1')
        self.rule_id_2 = self.ref('hr_payroll.hr_salary_rule_convanceallowance1')
        self.rule_id_3 = self.ref('hr_payroll.hr_salary_rule_professionaltax1')
        self.rule_id_4 = self.ref('hr_payroll.hr_salary_rule_providentfund1')
        self.rule_id_5 = self.ref('hr_payroll.hr_salary_rule_meal_voucher')
        self.rule_id_6 = self.ref('hr_payroll.hr_salary_rule_sales_commission')
        self.emp_type_id = self.ref('hr_contract.hr_contract_type_emp')
        self.working_hours_id = self.ref('resource.timesheet_group1')

        # create a new employee "Richard"
        self.employee_richard = self.HrEmployee.create({
            'birthday': '1984-05-01',
            'country_id': self.country_id,
            'department_id': self.rd_department_id,
            'gender': 'male',
            'name': 'Richard'
        })

        # create a salary structure
        self.sd_payroll_structure = self.HrPayrollStructure.create({
            'name': 'Salary Structure for Software Developer',
            'code': 'SD',
            'company_id': self.main_company_id,
            'rule_ids': [(6, 0, [self.rule_id_1, self.rule_id_2, self.rule_id_3, self.rule_id_4, self.rule_id_5, self.rule_id_6])]
        })

        # create a contract
        self.hr_contract_richard = self.HrContract.create({
            'date_end': (fields.Date.from_string(fields.Datetime.now()) + timedelta(days=365)),
            'date_start': fields.Datetime.now(),
            'name': 'Contract for Richard',
            'wage': 5000.0,
            'type_id': self.emp_type_id,
            'employee_id': self.employee_richard.id,
            'struct_id': self.sd_payroll_structure.id,
            'working_hours': self.working_hours_id
        })

        # create employee payslip
        self.richard_payslip = self.HrPayslip.create({
            'employee_id': self.employee_richard.id
        })

        # I want to generate a payslip from Payslip run.
        self.payslip_run = self.HrPayslipRun.create({
            'date_end': '2011-09-30',
            'date_start': '2011-09-01',
            'name': 'Payslip for Employee'})

        # generate payslip
        self.payslip_employees = self.HrPayslipEmployees.create({
            'employee_ids': [(6, 0, [self.employee_richard.id])]
        })

        # I open Contribution Register and from there I print the Payslip Lines report.
        self.payslip_lines_contribution_register = self.PayslipLinesContributionRegister.create({
            'date_from': '2011-09-30',
            'date_to': '2011-09-01'})

    def test_00_hr_payroll(self):
        """ checking the process of payslip. """

        # I assign the amount to Input data.
        payslip = self.HrPayslipInput.search([('payslip_id', '=', self.payslip_employees.id)])
        payslip.write({'amount': 5.0})

        # I verify the payslip is in done state.
        self.assertEqual(self.richard_payslip.state, 'draft', 'State not changed!')

        # I click on "Compute Sheet" button.
        context = {"lang": "en_US", "tz": False, "active_model": 'ir.ui.menu', "department_id": False, "active_ids": [self.menu_dept_tree_id], "section_id": False, "active_id": self.menu_dept_tree_id}
        self.richard_payslip.with_context(context).compute_sheet()

        # Confirm Payslip
        self.richard_payslip.signal_workflow('hr_verify_sheet')

        # I verify that the payslip is in done state.
        self.assertEqual(self.richard_payslip.state, 'done', 'State not changed!')

        # I want to check refund payslip so I click on refund button.
        self.richard_payslip.refund_sheet()

        # I check on new payslip Credit Note is checked or not.
        payslip_ids = self.richard_payslip.search([('name', 'like', 'Refund: %s' % self.richard_payslip.name), ('credit_note', '=', True)])
        self.assertTrue(payslip_ids, "Payslip not refunded!")

        # I generate the payslip by clicking on Generate button wizard.
        context = {'active_id': self.payslip_run.id}
        self.payslip_employees.with_context(context).compute_sheet()

        # I print the payslip report
        data, format = odoo_report.render_report(self.env.cr, self.env.uid, self.richard_payslip.id, 'hr_payroll.report_payslip', {}, {})
        if tools.config['test_report_directory']:
            file(os.path.join(tools.config['test_report_directory'], 'hr_payroll-payslip.'+format), 'wb+').write(data)

        # I print the payslip details report
        data, format = odoo_report.render_report(self.env.cr, self.env.uid, self.richard_payslip.id, 'hr_payroll.report_payslipdetails', {}, {})
        if tools.config['test_report_directory']:
            file(os.path.join(tools.config['test_report_directory'], 'hr_payroll-payslipdetails.'+format), 'wb+').write(data)

        # I print the contribution register report
        ctx = {'active_model': 'hr.contribution.register', 'active_ids': [self.env.ref('hr_payroll.hr_houserent_register').id]}
        test_reports.try_report_action(self.env.cr, self.env.uid, 'action_payslip_lines_contribution_register', context=ctx, our_module='hr_payroll')
