from datetime import datetime

from odoo.addons.hr_payroll.tests.common import TestPayslipBase
from odoo.exceptions import UserError
from odoo.tests.common import tagged


@tagged('-at_install', 'post_install_l10n', 'post_install')
class TestPayslipComputation(TestPayslipBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        mexico = cls.env.ref('base.mx')
        cls.env.company.write({
            'country_id': mexico.id
        })
        cls.richard_emp.write({
            'company_id': cls.env.company,
            'country_id': mexico.id,
        })

    def _create_payslip(self):
        return self.env['hr.payslip'].create({
            'name': 'Payslip for Richard',
            'employee_id': self.richard_emp.id,
            'struct_id': self.env.ref('l10n_mx_hr_payroll.hr_payroll_structure_mx_employee_salary').id,
            'date_from': datetime(2025, 1, 1),
            'date_to': datetime(2025, 1, 31),
            'contract_id': self.richard_emp.contract_ids[0].id,
        })

    def test_computation_with_salary_less_than_mdw(self):
        self.richard_emp.contract_ids[0].write({
            'wage': 10,
        })
        payslip = self._create_payslip()
        with self.assertRaises(UserError):
            payslip.compute_sheet()
        self.richard_emp.contract_ids[0].write({
            'wage': 8400,
        })
        payslip = self._create_payslip()
        payslip.compute_sheet()
        self.assertEqual(payslip.line_ids.filtered(lambda l: l.code == 'BASIC').mapped('total'), [8400])
