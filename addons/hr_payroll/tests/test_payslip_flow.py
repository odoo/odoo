# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo.report import render_report
from odoo.tools import config, test_reports
from odoo.addons.hr_payroll.tests.common import TestPayslipBase
from odoo.fields import Date

class TestPayslipFlow(TestPayslipBase):

    def test_00_payslip_flow(self):
        """ Testing payslip flow and report printing """
        # I create an employee Payslip
        richard_payslip = self.env['hr.payslip'].create({
            'name': 'Payslip of Richard',
            'employee_id': self.richard_emp.id
        })

        payslip_input = self.env['hr.payslip.input'].search([('payslip_id', '=', richard_payslip.id)])
        # I assign the amount to Input data
        payslip_input.write({'amount': 5.0})

        # I verify the payslip is in draft state
        self.assertEqual(richard_payslip.state, 'draft', 'State not changed!')

        context = {
            "lang": "en_US", "tz": False, "active_model": "ir.ui.menu",
            "department_id": False, "section_id": False,
            "active_ids": [self.ref("hr_payroll.menu_department_tree")],
            "active_id": self.ref("hr_payroll.menu_department_tree")
        }
        # I click on 'Compute Sheet' button on payslip
        richard_payslip.with_context(context).compute_sheet()

        # Then I click on the 'Confirm' button on payslip
        richard_payslip.action_payslip_done()

        # I verify that the payslip is in done state
        self.assertEqual(richard_payslip.state, 'done', 'State not changed!')

        # I want to check refund payslip so I click on refund button.
        richard_payslip.refund_sheet()

        # I check on new payslip Credit Note is checked or not.
        payslip_refund = self.env['hr.payslip'].search([('name', 'like', 'Refund: '+ richard_payslip.name), ('credit_note', '=', True)])
        self.assertTrue(bool(payslip_refund), "Payslip not refunded!")

        # I want to generate a payslip from Payslip run.
        payslip_run = self.env['hr.payslip.run'].create({
            'date_end': '2011-09-30',
            'date_start': '2011-09-01',
            'name': 'Payslip for Employee'
        })

        # I create record for generating the payslip for this Payslip run.

        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.richard_emp.ids)]
        })

        # I generate the payslip by clicking on Generat button wizard.
        payslip_employee.with_context(active_id=payslip_run.id).compute_sheet()

        # I open Contribution Register and from there I print the Payslip Lines report.
        self.env['payslip.lines.contribution.register'].create({
            'date_from': '2011-09-30',
            'date_to': '2011-09-01'
        })

        # I print the payslip report
        data, format = render_report(self.env.cr, self.env.uid, richard_payslip.ids, 'hr_payroll.report_payslip', {}, {})
        if config.get('test_report_directory'):
            file(os.path.join(config['test_report_directory'], 'hr_payroll-payslip.'+ format), 'wb+').write(data)

        # I print the payslip details report
        data, format = render_report(self.env.cr, self.env.uid, richard_payslip.ids, 'hr_payroll.report_payslipdetails', {}, {})
        if config.get('test_report_directory'):
            file(os.path.join(config['test_report_directory'], 'hr_payroll-payslipdetails.'+ format), 'wb+').write(data)

        # I print the contribution register report
        context = {'model': 'hr.contribution.register', 'active_ids': [self.ref('hr_payroll.hr_houserent_register')]}
        test_reports.try_report_action(self.env.cr, self.env.uid, 'action_payslip_lines_contribution_register', context=context, our_module='hr_payroll')

    def test_01_test_iregular_working_hours(self):
        """ Testing payslip holiday calculations """
        # I create an employee Payslip on a fixed date so we know the exact days of week in this month
        amanda_payslip_jan = self.env['hr.payslip'].create({
            'name': 'Payslip of Amanda',
            'employee_id': self.amanda_emp.id,
            'date_from': '2017-01-01',
            'date_to': '2017-01-31'
        })

        payslip_input = self.env['hr.payslip.input'].search([('payslip_id', '=', amanda_payslip_jan.id)])
        # I assign the amount to Input data
        payslip_input.write({'amount': 5.0})

        # I verify the payslip is in draft state
        self.assertEqual(amanda_payslip_jan.state, 'draft', 'State not changed!')

        context = {
            "lang": "en_US", "tz": 'UTC', "active_model": "ir.ui.menu",
            "department_id": False, "section_id": False,
            "active_ids": [self.ref("hr_payroll.menu_department_tree")],
            "active_id": self.ref("hr_payroll.menu_department_tree")
        }
        # I select the 'Employee' field in the payslip
        amanda_payslip_jan.with_context(context).onchange_contract()
        # I click on 'Compute Sheet' button on payslip
        amanda_payslip_jan.with_context(context).compute_sheet()

        WORK100 = None
        for worked_day in amanda_payslip_jan.worked_days_line_ids:
            if worked_day.code == "WORK100":
                WORK100 = worked_day

        # I check that there are 200 working hours for this month calculcated and 26 working days
        self.assertIsNotNone(WORK100,"WORK100 should be generated by the calculation")
        self.assertEqual(WORK100.number_of_hours, 206.0, "Number of worked hours in Jan paysleep shoulb be 206 ( 22*8 + 5*6 )")
        self.assertEqual(WORK100.number_of_days, 27.0, "Number of worked days in Jan paysleep shoulb be 27 ( 22 Mon-Fri + 5 Sunday )")

    def test_02_test_iregular_holidays(self):
        """ Testing payslip holiday calculations """
        # I create an employee Payslip on a fixed date so we know the exact days of week in this month
        amanda_payslip_feb = self.env['hr.payslip'].create({
            'name': 'Payslip of Amanda',
            'employee_id': self.amanda_emp.id,
            'date_from': '2017-02-01',
            'date_to': '2017-02-28'
        })

        payslip_input = self.env['hr.payslip.input'].search([('payslip_id', '=', amanda_payslip_feb.id)])
        # I assign the amount to Input data
        payslip_input.write({'amount': 5.0})

        # I verify the payslip is in draft state
        self.assertEqual(amanda_payslip_feb.state, 'draft', 'State not changed!')

        context = {
            "lang": "en_US", "tz": 'UTC', "active_model": "ir.ui.menu",
            "department_id": False, "section_id": False,
            "active_ids": [self.ref("hr_payroll.menu_department_tree")],
            "active_id": self.ref("hr_payroll.menu_department_tree")
        }
        # I select the 'Employee' field in the payslip
        amanda_payslip_feb.with_context(context).onchange_contract()

        # I click on 'Compute Sheet' button on payslip
        amanda_payslip_feb.with_context(context).compute_sheet()

        WORK100 = None
        HOLIDAY_S1 = None
        HOLIDAY_S2 = None
        HOLIDAY_S3 =  None
        for worked_day in amanda_payslip_feb.worked_days_line_ids:
            if worked_day.code == "WORK100":
                WORK100 = worked_day
            elif worked_day.code == "HOLIDAY_S1":
                HOLIDAY_S1 = worked_day
            elif worked_day.code == "HOLIDAY_S2":
                HOLIDAY_S2 = worked_day
            elif worked_day.code == "HOLIDAY_S3":
                HOLIDAY_S3 = worked_day

        # I check that there are 200 working hours for this month calculcated and 26 working days
        self.assertIsNotNone(WORK100, "WORK100 should be generated by the calculation")
        self.assertEqual(WORK100.number_of_hours, 154.0, "Number of worked hours in Jan paysleep shoulb be 154")
        self.assertEqual(round(WORK100.number_of_days, 2), 19.83,
                         "Number of worked days in Jan paysleep shoulb be 19.83 ( 24 - 0.5 - 0.68 - 3 ) ")

        # I check that the S1 type of holiday is calculated with 0.5 days and 4 hours
        self.assertIsNotNone(HOLIDAY_S1, "HOLIDAY_S1 should be generated by the calculation")
        self.assertEqual(HOLIDAY_S1.number_of_hours, 4.0, "Number of HOLIDAY_S1 hopurs should be 4")
        self.assertEqual(round(HOLIDAY_S1.number_of_days, 2), 0.5, "Number of HOLIDAY_S1 worked days shopuld be 0.5")

        # I check that the S2 type of holiday is calculated with 0.67 days and 4 hours
        self.assertIsNotNone(HOLIDAY_S2, "HOLIDAY_S2 should be generated by the calculation")
        self.assertEqual(HOLIDAY_S2.number_of_hours, 4.0, "Number of HOLIDAY_S2 hopurs should be 4")
        self.assertEqual(round(HOLIDAY_S2.number_of_days, 2), 0.67, "Number of HOLIDAY_S1 worked days shopuld be 0.67")

        # I check that the S3 type of holiday is calculated with 3 days and 22 hours
        self.assertIsNotNone(HOLIDAY_S3, "HOLIDAY_S3 should be generated by the calculation")
        self.assertEqual(HOLIDAY_S3.number_of_hours, 22.0, "Number of HOLIDAY_S3 hopurs should be 8+8+6 = 22")
        self.assertEqual(round(HOLIDAY_S3.number_of_days, 2), 3.0, "Number of HOLIDAY_S3 worked days shopuld be 3")
