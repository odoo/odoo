# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.report import render_report
from odoo.tools import config, test_reports
from odoo.addons.hr_payroll.tests.common import TestPayslipBase


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
            open(os.path.join(config['test_report_directory'], 'hr_payroll-payslip.'+ format), 'wb+').write(data)

        # I print the payslip details report
        data, format = render_report(self.env.cr, self.env.uid, richard_payslip.ids, 'hr_payroll.report_payslipdetails', {}, {})
        if config.get('test_report_directory'):
            open(os.path.join(config['test_report_directory'], 'hr_payroll-payslipdetails.'+ format), 'wb+').write(data)

        # I print the contribution register report
        context = {'model': 'hr.contribution.register', 'active_ids': [self.ref('hr_payroll.hr_houserent_register')]}
        test_reports.try_report_action(self.env.cr, self.env.uid, 'action_payslip_lines_contribution_register', context=context, our_module='hr_payroll')
