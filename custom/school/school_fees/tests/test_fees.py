# See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo.tests import common


class TestFees(common.TransactionCase):

    def setUp(self):
        super(TestFees, self).setUp()
        self.payslip_line_obj = self.env['student.payslip.line']
        self.fees_structure_line_obj = self.env['student.fees.structure.line']
        self.fees_register_obj = self.env['student.fees.register']
        self.fees_structure_obj = self.env['student.fees.structure']
        self.student_payslip_obj = self.env['student.payslip']
        self.student = self.env.ref('school.demo_student_student_5')
        self.school = self.env.ref('school.demo_school_1')
        self.standard = self.env.ref('school.demo_school_standard_1')
        self.acct_type = self.env.ref('account.data_account_type_revenue')
#       Create Payslip Line
        self.payslip_line = self.payslip_line_obj.\
            create({'name': 'Test case-fees',
                    'code': '10',
                    'type': 'month',
                    'amount': 2000.00,
                    })
#       Create Fees_structure_line
        self.fees_structure_line = self.fees_structure_line_obj.\
            create({'name': 'Educational Fees',
                    'code': '01',
                    'type': 'month',
                    'amount': 4000.00
                    })
#        Create fees structure
        self.fees_structure = self.fees_structure_obj.\
            create({'name': 'fees structure-2017',
                    'code': 'FS-2017',
                    'line_ids': [(4, self.fees_structure_line.ids)]
                    })
#        find the sale type journal
        self.journal = self.env['account.journal'].search([('type', '=',
                                                            'sale')],
                                                          limit=1)
        # Create Student Fees Register
        self.fees_register = self.fees_register_obj.\
            create({'name': self.student.id,
                    'date': '2017-06-05',
                    'company_id': self.school.company_id.id,
                    'fees_structure': self.fees_structure.id,
                    'standard_id': self.standard.id,
                    'journal_id': self.journal.id
                    })
        self.fees_register._total_amount()
        self.fees_register.fees_register_draft()
        self.fees_register.fees_register_confirm()
#        Create Student Fees Receipt
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.student_payslip = self.student_payslip_obj.\
            create({'student_id': self.student.id,
                    'name': 'Test Fees Receipt',
                    'number': 'SLIP/097',
                    'date': current_date,
                    'fees_structure_id': self.fees_structure.id,
                    'journal_id': self.journal.id
                    })
        self.student_payslip.onchange_student()
        self.student_payslip.onchange_journal_id()
        self.student_payslip.payslip_confirm()
        self.student_payslip.student_pay_fees()
        self.student_payslip.payslip_paid()
        self.student_payslip.invoice_view()

    def test_fees(self):
        self.assertEqual(self.student.state, 'done')
