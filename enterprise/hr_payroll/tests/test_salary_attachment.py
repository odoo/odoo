# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.hr_payroll.tests.common import TestPayslipBase

from datetime import date, datetime

class TestSalaryAttachment(TestPayslipBase):

    def setUp(self):
        super().setUp()
        self.current_year = datetime.now().year
        self.toto = self.env['hr.employee'].create({'name': 'Toto'})
        self.current_year = datetime.now().year
        self.env['hr.contract'].create({
            'date_start': date(self.current_year, 1, 1),
            'date_end': date(self.current_year, 12, 31),
            'name': 'Contract of Toto',
            'wage': 1000.0,
            'state': 'open',
            'employee_id': self.toto.id,
            'structure_type_id': self.structure_type.id,
            'date_generated_from': datetime(self.current_year, 1, 1, 0, 0),
            'date_generated_to': datetime(self.current_year, 1, 1, 0, 0),
        })
        self.attachement_type = self.env.ref('hr_payroll.input_attachment_salary')
        self.child_support_type = self.env.ref('hr_payroll.input_child_support')

    def action_pay_payslip(self, employee):
        payslip = self.env['hr.payslip'].create({
            'name': 'Payslip',
            'employee_id': employee.id
        })
        payslip.compute_sheet()
        payslip.action_payslip_done()
        payslip.action_payslip_paid()

    def test_attachment_fixed_amount(self):
        attachment = self.env['hr.salary.attachment'].create({
            'employee_ids': [self.toto.id],
            'description': 'Fixed amount',
            'other_input_type_id': self.attachement_type.id,
            'date_start': date(self.current_year, 1, 1),
            'monthly_amount': 200,
            'total_amount': 600,
        })
        self.action_pay_payslip(self.toto)
        self.assertEqual(attachment.paid_amount, 200)
        self.action_pay_payslip(self.toto)
        self.assertEqual(attachment.paid_amount, 400)
        self.action_pay_payslip(self.toto)
        self.assertEqual(attachment.paid_amount, 600)
        self.assertEqual(attachment.remaining_amount, 0)
        self.assertEqual(attachment.state, 'close')

    def test_attachment_payslip_amount(self):
        attachment = self.env['hr.salary.attachment'].create({
            'employee_ids': [self.toto.id],
            'description': 'Monthly amount',
            'other_input_type_id': self.child_support_type.id,
            'date_start': date(self.current_year, 1, 1),
            'monthly_amount': 500,
        })
        self.action_pay_payslip(self.toto)
        self.assertEqual(attachment.paid_amount, 500)
        self.action_pay_payslip(self.toto)
        self.assertEqual(attachment.paid_amount, 1000)
        self.action_pay_payslip(self.toto)
        self.assertEqual(attachment.paid_amount, 1500)
        self.assertEqual(attachment.remaining_amount, 500)
        self.assertEqual(attachment.state, 'open')

    def test_distribution_attachment_fixed_amount(self):
        attachment_A, attachment_B = self.env['hr.salary.attachment'].create([
            {
                'employee_ids': [self.toto.id],
                'description': 'Fixed amount A',
                'other_input_type_id': self.attachement_type.id,
                'date_start': date(self.current_year, 1, 1),
                'monthly_amount': 200,
                'total_amount': 500,
            },
            {
                'employee_ids': [self.toto.id],
                'description': 'Fixed amount B',
                'other_input_type_id': self.attachement_type.id,
                'date_start': date(self.current_year, 1, 1),
                'monthly_amount': 100,
                'total_amount': 1000,
            }
        ])
        self.action_pay_payslip(self.toto)
        self.assertEqual(attachment_A.paid_amount, 200)
        self.assertEqual(attachment_B.paid_amount, 100)
        self.action_pay_payslip(self.toto)
        self.assertEqual(attachment_A.paid_amount, 400)
        self.assertEqual(attachment_B.paid_amount, 200)
        # We have a total amount of 300 to distribute between attachments
        self.action_pay_payslip(self.toto)
        self.assertEqual(attachment_A.paid_amount, 500) # Don't exceed total_amount
        self.assertEqual(attachment_B.paid_amount, 300)

    def test_distribution_attachment_payslip_amount(self):
        attachment_A, attachment_B = self.env['hr.salary.attachment'].create([
            {
                'employee_ids': [self.toto.id],
                'description': 'Monthly amount A',
                'other_input_type_id': self.child_support_type.id,
                'date_start': date(self.current_year, 1, 1),
                'monthly_amount': 200,
            },
            {
                'employee_ids': [self.toto.id],
                'description': 'Monthly amount B',
                'other_input_type_id': self.child_support_type.id,
                'date_start': date(self.current_year, 1, 1),
                'monthly_amount': 500,
            }
        ])
        self.action_pay_payslip(self.toto)
        self.assertEqual(attachment_A.paid_amount, 200)
        self.assertEqual(attachment_B.paid_amount, 500)

    def test_attachments_fixed_and_payslip_amount(self):
        attachment_fixed, attachment_monthly = self.env['hr.salary.attachment'].create([
            {
                'employee_ids': [self.toto.id],
                'description': 'Fixed amount',
                'other_input_type_id': self.attachement_type.id,
                'date_start': date(self.current_year, 1, 1),
                'monthly_amount': 200,
                'total_amount': 600,
            },
            {
                'employee_ids': [self.toto.id],
                'description': 'Montly amount',
                'other_input_type_id': self.child_support_type.id,
                'date_start': date(self.current_year, 1, 1),
                'monthly_amount': 500,
            }
        ])
        self.action_pay_payslip(self.toto)
        self.assertEqual(attachment_fixed.paid_amount, 200)
        self.assertEqual(attachment_monthly.paid_amount, 500)

    def test_attachments_fixed_and_payslip_amount_manual_change(self):
        fixed_A, fixed_B, monthly_A, monthly_B = self.env['hr.salary.attachment'].create([
            {
                'employee_ids': [self.toto.id],
                'description': 'Fixed A',
                'other_input_type_id': self.attachement_type.id,
                'date_start': date(self.current_year, 1, 1),
                'monthly_amount': 100,
                'total_amount': 1000,
            },
            {
                'employee_ids': [self.toto.id],
                'description': 'Fixed B',
                'other_input_type_id': self.attachement_type.id,
                'date_start': date(self.current_year, 1, 1),
                'monthly_amount': 200,
                'total_amount': 500,
            },
            {
                'employee_ids': [self.toto.id],
                'description': 'Montly A',
                'other_input_type_id': self.child_support_type.id,
                'date_start': date(self.current_year, 1, 1),
                'monthly_amount': 100,
            },
            {
                'employee_ids': [self.toto.id],
                'description': 'Montly B',
                'other_input_type_id': self.child_support_type.id,
                'date_start': date(self.current_year, 1, 1),
                'monthly_amount': 200,
            }
        ])
        payslip = self.env['hr.payslip'].create({
            'name': 'Payslip',
            'employee_id': self.toto.id
        })
        payslip.compute_sheet()
        pl_fixed = payslip.line_ids.filtered(lambda l: l.name == 'Fixed A, Fixed B')
        pl_fixed.amount = 500
        pl_fixed.total = pl_fixed.quantity * pl_fixed.amount * pl_fixed.rate / 100
        payslip.action_payslip_done()
        payslip.action_payslip_paid()
        self.assertEqual(fixed_A.paid_amount, 100)
        # 500 (changed manually) - 300 = 200 remaining
        # Estimated end date of fixed B is before fixed A
        # Add 200 to initial 200 of fixed A
        self.assertEqual(fixed_B.paid_amount, 400)
        self.assertEqual(monthly_A.paid_amount, 100)
        self.assertEqual(monthly_B.paid_amount, 200)

    def test_attachment_inputs_with_same_code(self):
        # 3rd attachment should be ignored even though it comes last
        att_1, att_2, _ = self.env["hr.payslip.input.type"].create([{
            "name": "Allowance 1",
            "code": "ALW.ATT",
            "available_in_attachments": True,
            "default_no_end_date": True
        }, {
            "name": "Allowance 2",
            "code": "ALW.ATT",
            "available_in_attachments": True,
            "default_no_end_date": True
        }, {
            "name": "Allowance 3",
            "code": "ALW.ATT",
            "available_in_attachments": True,
            "default_no_end_date": True
        }])

        self.env['hr.salary.rule'].create({
            'name': 'Allowance Attachment',
            'sequence': 99,
            'amount_select': 'code',
            'amount_python_compute': "result = inputs['ALW.ATT'].amount",
            'quantity': "'WORK100' in worked_days and worked_days['WORK100'].number_of_days",
            'code': "ALW.ATT",
            'category_id': self.env.ref('hr_payroll.ALW').id,
            'struct_id': self.developer_pay_structure.id,
        })

        self.env['hr.salary.attachment'].create([{
            'employee_ids': [self.toto.id],
            'description': 'Test Attachment',
            'other_input_type_id': att_1.id,
            'date_start': date(self.current_year, 1, 1),
            'monthly_amount': 100,
            'total_amount': 1000,
        }, {
            'employee_ids': [self.toto.id],
            'description': 'Test Attachment',
            'other_input_type_id': att_2.id,
            'date_start': date(self.current_year, 1, 1),
            'monthly_amount': 50,
            'total_amount': 1000,
        }])

        payslip = self.env['hr.payslip'].create({
            'name': 'Payslip',
            'employee_id': self.toto.id
        })
        payslip.compute_sheet()
        payslip.action_payslip_done()
        payslip.action_payslip_paid()

        self.assertRecordValues(payslip.input_line_ids, [
            {"code": "ALW.ATT", "input_type_id": att_1.id, "amount": 100},
            {"code": "ALW.ATT", "input_type_id": att_2.id, "amount": 50},
        ])
        self.assertRecordValues(payslip.salary_attachment_ids, [
            {"other_input_type_id": att_1.id, "paid_amount": 100},
            {"other_input_type_id": att_2.id, "paid_amount": 50},
        ])
