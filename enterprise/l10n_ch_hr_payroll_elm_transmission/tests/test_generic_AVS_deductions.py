# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged, TransactionCase
from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install', 'swissdec_payroll')
class TestGenericAVSDeductions(TransactionCase):
    @freeze_time("2026-02-28")
    def setUp(self):
        super().setUp()
        self.company_ch = self.env['res.company'].create({'name': 'Swiss Comp.', 'country_id': self.env.ref('base.ch').id})
        self.struct = self.env.ref('l10n_ch_hr_payroll_elm_transmission.hr_payroll_structure_ch_elm')
        self.employee = self.env['hr.employee'].create({'name': 'Swiss Test Employee', 'company_id': self.company_ch.id})
        social_insurance = self.env['l10n.ch.social.insurance'].create({
            'name': 'Test Social Insurance',
            'insurance_company': '048.000',
            'insurance_code': '048.000',
        })
        self.contract = self.env['hr.contract'].create({
            'name': 'Contract Swiss',
            'employee_id': self.employee.id,
            'date_start': '2026-01-01',
            'state': 'open',
            'wage': 6000.0,
            'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id,
            'l10n_ch_social_insurance_id': social_insurance.id,
            'l10n_ch_has_monthly': True,
        })

    @freeze_time("2026-02-28")
    def _create_test_payslip(self):
        return self.env['hr.payslip'].create({
            'name': "Payslip Test",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'struct_id': self.struct.id,
            'date_from': '2026-02-01',
            'date_to': '2026-02-28',
        })

    @freeze_time("2026-02-28")
    def test_generic_avs_deductions(self):
        input_codes = ['5400', '5401', '5402', '5403', '5404', '5405', '5406', '5407', '5408', '7400', '7401', '7402', '7403', '7404', '7405', '7406', '7407', '7408']
        payslip = self._create_test_payslip()
        payslip.write({'input_line_ids': [
            (0, 0, {
                'input_type_id': self.env.ref(f"l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_{input_code}").id,
                'amount': 1.1 + 0.01 * i
            }) for i, input_code in enumerate(input_codes)
        ]})
        payslip.compute_sheet()
        for i, input_code in enumerate(input_codes):
            line_code = "AVS.GENERIC"
            if input_code.startswith('7'):
                line_code += ".COMP"
            if int(input_code[-1]):
                line_code += f".{int(input_code[-1]) + 1}"
            payslip_line = payslip.line_ids.filtered(lambda l: l.code == line_code)
            self.assertTrue(payslip_line, f"Rule {input_code} line is not there")
            rate = 1.1 + 0.01 * i
            self.assertAlmostEqual(payslip_line.rate, rate * (1 if input_code.startswith('7') else -1), 2)
            self.assertEqual(payslip_line.amount, 6000)
