# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date


from odoo import Command
from odoo.addons.l10n_in_hr_payroll.tests.common import TestPayrollCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPaymentAdviceBatch(TestPayrollCommon):
    def _prepare_payslip_run(self):
        payslip_run = self.env['hr.payslip.run'].create({
            'date_start': '2023-01-01',
            'date_end': '2023-01-31',
            'name': 'January Batch',
            'company_id': self.company_in.id,
        })

        payslip_employee = self.env['hr.payslip.employees'].with_company(self.company_in).create({
            'employee_ids': [
                Command.set([self.rahul_emp.id, self.jethalal_emp.id])
            ]
        })

        payslip_employee.with_context(active_id=payslip_run.id).compute_sheet()
        payslip_run.action_validate()
        return payslip_run

    def test_payment_report_advice_xlsx_creation(self):
        payslip_run = self._prepare_payslip_run()
        self.assertEqual(payslip_run.state, "close", "Payslip run should be in Done state")

        # Generating the XLSX report for the batch
        payment_report_dict = self.env["hr.payroll.payment.report.wizard"].create({
            'payslip_ids': payslip_run.slip_ids.ids,
            'payslip_run_id': payslip_run.id,
            'export_format': 'advice',
        }).generate_payment_report_xls()

        payment_report = self.env['hr.payroll.payment.report.wizard'].browse(payment_report_dict['res_id'])

        self.assertTrue(payslip_run.payment_report, "XLSX File should be generated!")
        self.assertTrue(payment_report.l10n_in_payment_advice_xlsx, "XLSX File should be generated!")
        self.assertEqual(payment_report.l10n_in_payment_advice_filename_xlsx, payment_report.l10n_in_reference + '.xlsx')
        self.assertTrue(payslip_run.payment_report_filename)

    def test_payment_report_advice_pdf_creation(self):
        payslip_run = self._prepare_payslip_run()
        self.assertEqual(payslip_run.state, "close", "Payslip run should be in Done state")

        # Generating the PDF report for the batch
        payment_report_dict = self.env["hr.payroll.payment.report.wizard"].create({
            'payslip_ids': payslip_run.slip_ids.ids,
            'payslip_run_id': payslip_run.id,
            'export_format': 'advice',
        }).generate_payment_report_pdf()

        payment_report = self.env['hr.payroll.payment.report.wizard'].browse(payment_report_dict['res_id'])

        self.assertTrue(payslip_run.payment_report, "PDF File should be generated!")
        self.assertTrue(payment_report.l10n_in_payment_advice_pdf, "PDF File should be generated!")
        self.assertEqual(payment_report.l10n_in_payment_advice_filename_pdf, payment_report.l10n_in_reference + '.pdf')
        self.assertTrue(payslip_run.payment_report_filename)

    def test_payment_advice_xlsx_report_from_payslip(self):
        jethalal_payslip = self.env['hr.payslip'].create({
            'name': 'Jethalal Payslip',
            'employee_id': self.jethalal_emp.id,
            'contract_id': self.contract_jethalal.id,
            'date_from': date(2023, 1, 1),
            'date_to': date(2023, 1, 31),
        })
        jethalal_payslip.compute_sheet()
        jethalal_payslip.action_payslip_done()
        self.assertEqual(jethalal_payslip.state, "done", "Payslip should be in Done state")

        # Generating the XLSX report for the payslip
        payment_report_dict = self.env["hr.payroll.payment.report.wizard"].create({
            'payslip_ids': jethalal_payslip.ids,
            'export_format': 'advice',
        }).generate_payment_report_xls()
        payment_report = self.env['hr.payroll.payment.report.wizard'].browse(payment_report_dict['res_id'])

        self.assertTrue(jethalal_payslip.payment_report, "XLSX File should be generated!")
        self.assertTrue(payment_report.l10n_in_payment_advice_xlsx, "XLSX File should be generated!")
        self.assertEqual(payment_report.l10n_in_payment_advice_filename_xlsx, payment_report.l10n_in_reference + '.xlsx')
        self.assertTrue(jethalal_payslip.payment_report_filename, payment_report.l10n_in_reference + '.xlsx')

    def test_payment_advice_pdf_report_from_payslip(self):
        rahul_payslip = self.env['hr.payslip'].create({
            'name': 'Rahul Payslip',
            'employee_id': self.rahul_emp.id,
            'contract_id': self.contract_rahul.id,
            'date_from': date(2023, 1, 1),
            'date_to': date(2023, 1, 31),
        })
        rahul_payslip.compute_sheet()
        rahul_payslip.action_payslip_done()
        self.assertEqual(rahul_payslip.state, "done", "Payslip should be in Done state")

        # Generating the PDF report for the payslip
        payment_report_dict = self.env["hr.payroll.payment.report.wizard"].create({
            'payslip_ids': rahul_payslip.ids,
            'export_format': 'advice',
        }).generate_payment_report_pdf()

        payment_report = self.env['hr.payroll.payment.report.wizard'].browse(payment_report_dict['res_id'])

        self.assertTrue(rahul_payslip.payment_report, "PDF File should be generated!")
        self.assertTrue(payment_report.l10n_in_payment_advice_pdf, "PDF File should be generated!")
        self.assertEqual(payment_report.l10n_in_payment_advice_filename_pdf, payment_report.l10n_in_reference + '.pdf')
        self.assertTrue(rahul_payslip.payment_report_filename, payment_report.l10n_in_reference + '.pdf')
