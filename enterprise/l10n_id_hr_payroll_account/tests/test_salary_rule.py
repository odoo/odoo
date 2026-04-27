# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from odoo.tests import tagged
from odoo import Command
from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon

PERIOD = {
    1: (1, 31),
    2: (1, 28),
    3: (1, 31),
    4: (1, 30),
    5: (1, 31),
    6: (1, 30),
    7: (1, 31),
    8: (1, 31),
    9: (1, 30),
    10: (1, 31),
    11: (1, 30),
    12: (1, 31),
}


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('id')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.id'),
            structure=cls.env.ref('l10n_id_hr_payroll.hr_payroll_structure_id_employee_salary'),
            structure_type=cls.env.ref('l10n_id_hr_payroll.structure_type_employee_id'),
            contract_fields={
                'wage': 1e7,
                'l10n_id_bpjs_jkk': 0.0024,  # 0.24%
            }
        )

    def test_pph_tk0(self):
        """ Basic payslip with TK/0 (1)"""
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.worked_days_line_ids), 1)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 10000000, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 23)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 184)
        payslip_results = {'BASE': 10000000, 'BASIC': 10000000, 'BPJS_JKK': 24000, 'BPJS_JKM': 30000, 'BPJS_Kesehatan': 400000, 'GROSS': 10454000, 'JHT': -200000, 'JP': -100000, 'BPJS_KESEHATAN_DED': -100000, 'PPH21': -261350, 'NET': 9338650}
        self._validate_payslip(payslip, payslip_results)

    def test_pph_tk2(self):
        """ Basic payslip with TK/2 (2)"""
        self.contract.wage = 13e6
        self.employee.l10n_id_kode_ptkp = 'tk2'

        payslip = self._generate_payslip(date(2024, 6, 1), date(2024, 6, 30))

        payslip_results = {'BASE': 13000000, 'BASIC': 13000000, 'BPJS_JKK': 31200, 'BPJS_JKM': 39000, 'BPJS_Kesehatan': 480000, 'GROSS': 13550200, 'JHT': -260000, 'BPJS_KESEHATAN_DED': -120000, 'JP': -100423, 'PPH21': -542008, 'NET': 11977569}
        self._validate_payslip(payslip, payslip_results)

    def test_with_unpaid_leave(self):
        """ Unpaid leave of 7 days (3) """
        self.contract.wage = 6e6

        leaves_to_create = [
            (datetime(2024, 6, 6), datetime(2024, 6, 6), 'hr_holidays.holiday_status_unpaid'),
            (datetime(2024, 6, 7), datetime(2024, 6, 7), 'hr_holidays.holiday_status_unpaid'),
            (datetime(2024, 6, 10), datetime(2024, 6, 10), 'hr_holidays.holiday_status_unpaid'),
            (datetime(2024, 6, 11), datetime(2024, 6, 11), 'hr_holidays.holiday_status_unpaid'),
            (datetime(2024, 6, 12), datetime(2024, 6, 12), 'hr_holidays.holiday_status_unpaid'),
            (datetime(2024, 6, 13), datetime(2024, 6, 13), 'hr_holidays.holiday_status_unpaid'),
            (datetime(2024, 6, 14), datetime(2024, 6, 14), 'hr_holidays.holiday_status_unpaid'),
        ]

        for leave in leaves_to_create:
            self._generate_leave(leave[0], leave[1], leave[2])

        payslip = self._generate_payslip(date(2024, 6, 1), date(2024, 6, 30))

        payslip_results = {'BASE': 3900000, 'BASIC': 3900000, 'BPJS_JKK': 14400, 'BPJS_JKM': 18000, 'BPJS_Kesehatan': 240000, 'GROSS': 4172400, 'JHT': -120000, 'BPJS_KESEHATAN_DED': -60000, 'JP': -60000, 'PPH21': 0, 'NET': 3660000}
        self._validate_payslip(payslip, payslip_results)

    def test_with_allowance(self):
        """ 50k/day meal allowance, 50k/day transport allowance, 20m wage"""
        self.contract.wage = 2e7

        payslip = self._generate_payslip(
            date(2024, 6, 1),
            date(2024, 6, 30),
            input_line_ids=[
                Command.create(
                    {
                        'input_type_id': self.env.ref('l10n_id_hr_payroll.input_transport_allowance').id,
                        'amount': 1000000
                    }),
                Command.create(
                    {
                        'input_type_id': self.env.ref('l10n_id_hr_payroll.input_meal_allowance').id,
                        'amount': 1000000,
                    }
                )
            ]
        )

        payslip_results = {'BASIC': 2e7, 'TRANSPORT_ALW': 1000000, 'BASE': 22e6, 'MEAL': 1000000, 'BPJS_JKK': 48000, 'BPJS_JKM': 60000, 'BPJS_Kesehatan': 480000, 'GROSS': 22588000, 'JHT': -400000, 'JP': -100423, 'BPJS_KESEHATAN_DED': -120000, 'PPH21': -2032920, 'NET': 19346657}
        self._validate_payslip(payslip, payslip_results)

    def test_with_reimbursement(self):
        """ 5m wage weith 500k reimbursement """
        self.contract.wage = 5e6

        payslip = self._generate_payslip(
            date(2024, 6, 1),
            date(2024, 6, 30),
            input_line_ids=[
                Command.create(
                    {
                        'input_type_id': self.env.ref('l10n_id_hr_payroll.input_global_reimbursement').id,
                        'amount': 5e5
                    }),
            ]
        )

        payslip_results = {'BASE': 5e6, 'BASIC': 5e6, 'BPJS_JKK': 12e3, 'BPJS_JKM': 15e3, 'BPJS_Kesehatan': 2e5, 'GROSS': 5227e3, 'JHT': -1e5, 'JP': -5e4, 'BPJS_KESEHATAN_DED': -5e4, 'PPH21': 0, 'REIMBURSEMENT': 5e5, 'NET': 53e5}
        self._validate_payslip(payslip, payslip_results)

    def test_low_income_with_meal_alw(self):
        """ Wage of 2m with 50k/day meal allowance """
        self.contract.wage = 2e6

        payslip = self._generate_payslip(
            date(2024, 6, 1),
            date(2024, 6, 30),
            input_line_ids=[
                Command.create(
                    {
                        'input_type_id': self.env.ref('l10n_id_hr_payroll.input_meal_allowance').id,
                        'amount': 1e6
                    }),
            ]
        )

        payslip_results = {"BASIC": 2e6, "MEAL": 1e6, "BASE": 3e6, "BPJS_JKK": 4800, "BPJS_JKM": 6000, "BPJS_Kesehatan": 8e4, "GROSS": 3090800, "JHT": -4e4, "JP": -2e4, "BPJS_KESEHATAN_DED": -2e4, "PPH21": 0, "NET": 292e4}
        self._validate_payslip(payslip, payslip_results)

    def test_with_insurance_and_meal_alw(self):
        """ 1m wage with 300k/day meal allowance and 500k/month insurance allowance (8)"""

        self.contract.wage = 1e6

        payslip = self._generate_payslip(
            date(2024, 6, 1),
            date(2024, 6, 30),
            input_line_ids=[
                Command.create(
                    {
                        'input_type_id': self.env.ref('l10n_id_hr_payroll.input_meal_allowance').id,
                        'amount': 6e6
                    }),
                Command.create(
                    {
                        'input_type_id': self.env.ref('l10n_id_hr_payroll.input_insurance_allowance').id,
                        'amount': 5e5
                    }
                )
            ]
        )

        payslip_results = {'BASIC': 1e6, 'MEAL': 6e6, 'INSURANCE': 5e5, 'BASE': 75e5, 'BPJS_JKK': 2400, 'BPJS_JKM': 3e3, 'BPJS_Kesehatan': 4e4, 'GROSS': 7545400, 'JHT': -2e4, 'JP': -1e4, 'BPJS_KESEHATAN_DED': -1e4, 'PPH21': -113181, 'NET': 7346819}
        self._validate_payslip(payslip, payslip_results)

    def test_no_jkk_jkm(self):
        """ Exclude JKK, JKM (9) """
        self.contract.wage = 5e6

        payslip = self._generate_payslip(
            date(2024, 6, 1),
            date(2024, 6, 30),
            input_line_ids=[
                Command.create(
                    {
                        'input_type_id': self.env.ref('l10n_id_hr_payroll.input_laptop_allowance').id,
                        'amount': 3e5
                    })
            ]
        )
        payslip.write({
            'l10n_id_include_jkk_jkm': False,
        })
        payslip.compute_sheet()

        payslip_results = {'BASIC': 5000000.0, 'LAPTOP': 300000.0, 'BASE': 5300000.0, 'BPJS_Kesehatan': 200000.0, 'GROSS': 5500000.0, 'BPJS_KESEHATAN_DED': -50000.0, 'PPH21': -13750.0, 'NET': 5236250.0}
        self._validate_payslip(payslip, payslip_results)

    def test_no_bpjs_kesehatan(self):
        """ Test payslip without BPJS kesehatan (10) """
        self.contract.wage = 5e6

        payslip = self._generate_payslip(
            date(2024, 6, 1),
            date(2024, 6, 30),
            input_line_ids=[
                Command.create(
                    {
                        'input_type_id': self.env.ref('l10n_id_hr_payroll.input_laptop_allowance').id,
                        'amount': 3e5
                    })
            ]
        )

        payslip.write({'l10n_id_include_bpjs_kesehatan': False})
        payslip.compute_sheet()

        payslip_results = {'BASIC': 5000000.0, 'LAPTOP': 300000.0, 'BASE': 5300000.0, 'BPJS_JKK': 12000.0, 'BPJS_JKM': 15000.0, 'GROSS': 5327000.0, 'JHT': -100000.0, 'JP': -50000.0, 'PPH21': 0.0, 'NET': 5150000.0}
        self._validate_payslip(payslip, payslip_results)

    def test_no_allowance_ded(self):
        """ Test allowance and deduction being removed from payslip (12)"""
        payslip = self._generate_payslip(
            date(2024, 6, 1),
            date(2024, 6, 30),
            input_line_ids=[
                Command.create(
                    {
                        'input_type_id': self.env.ref('l10n_id_hr_payroll.input_laptop_allowance').id,
                        'amount': 3e5
                    })
            ]
        )

        payslip.write({
            'l10n_id_include_jkk_jkm': False,
            'l10n_id_include_bpjs_kesehatan': False
        })
        payslip.compute_sheet()

        payslip_results = {'BASIC': 10000000.0, 'LAPTOP': 300000.0, 'BASE': 10300000.0, 'GROSS': 10300000.0, 'PPH21': -231750.0, 'NET': 10068250.0}
        self._validate_payslip(payslip, payslip_results)

    def test_allowance_thr(self):
        """ Test 20m salary with THR on April """
        self.contract.wage = 2e7

        payslip = self._generate_payslip(
            date(2024, 4, 1),
            date(2024, 4, 30),
            input_line_ids=[
                Command.create(
                    {
                        'input_type_id': self.env.ref('l10n_id_hr_payroll.input_holiday_allowance').id,
                        'amount': 1e7
                    })
            ]
        )

        payslip_results = {'BASIC': 2e7, 'THR': 1e7, 'BPJS_JKK': 48e3, 'BPJS_JKM': 6e4, 'BPJS_Kesehatan': 48e4, 'BASE': 3e7, 'GROSS': 30588e3, 'JHT': -4e5, 'JP': -100423, 'BPJS_KESEHATAN_DED': -12e4, 'PPH21': -3976440, 'NET': 25403137}
        self._validate_payslip(payslip, payslip_results)

    # =============================
    # END OF YEAR/CONTRACT PAYMENTS
    # =============================
    def test_end_of_year_payment_not_validated(self):
        """ Test if slip is not validated yet, then yearly gross=gross of that year only with no accumulation """
        self.contract.wage = 1e7

        for i in range(1, 13):
            drange = PERIOD[i]
            slip = self._generate_payslip(
                date(2024, i, drange[0]),
                date(2024, i, drange[1])
            )

            if i == 12:
                payslip = slip

        lines_to_compare = payslip._get_line_values(['GROSS'])
        self.assertAlmostEqual(lines_to_compare['GROSS'][payslip.id]['total'], 10454e3)

    def test_end_of_year_payment(self):
        """ Generate payslip from january to dec then focus on the end of year (15) """
        self.contract.wage = 2e7

        for i in range(1, 13):
            drange = PERIOD[i]
            slip = self._generate_payslip(
                date(2024, i, drange[0]),
                date(2024, i, drange[1]),
            )
            slip.action_payslip_done()

            if i == 12:
                payslip = slip

        payslip_results = {'BASE': 2e7, 'BASIC': 2e7, 'BPJS_JKK': 48e3, 'BPJS_JKM': 6e4, 'BPJS_Kesehatan': 48e4, 'GROSS': 20588e3, 'JHT': -4e5, 'JP': -100423, 'BPJS_KESEHATAN_DED': -12e4, 'PKP': 187056000, 'PTKP': 54e6, 'JABATAN': 6e6, 'PPH21': -1676280, 'NET': 17703297}
        self._validate_payslip(payslip, payslip_results)

    def test_end_of_year_payment_2(self):
        """ use 10m wage check only end of year (16)"""
        for i in range(1, 13):
            drange = PERIOD[i]
            slip = self._generate_payslip(
                date(2024, i, drange[0]),
                date(2024, i, drange[1]),
            )
            slip.action_payslip_done()

            if i == 12:
                payslip = slip

        payslip_results = {'BASE': 1e7, 'BASIC': 1e7, 'BPJS_JKK': 24e3, 'BPJS_JKM': 3e4, 'BPJS_Kesehatan': 4e5, 'GROSS': 10454e3, 'JHT': -2e5, 'JP': -1e5, 'BPJS_KESEHATAN_DED': -1e5, 'PKP': 65448e3, 'PTKP': 54e6, 'JABATAN': 6e6, 'PPH21': -942350, 'NET': 8657650}
        self._validate_payslip(payslip, payslip_results)

    def test_end_of_contract(self):
        """ Contract lasts until end of August (17) """
        self.contract.date_end = date(2024, 8, 31)

        for i in range(1, 9):
            drange = PERIOD[i]
            slip = self._generate_payslip(
                date(2024, i, drange[0]),
                date(2024, i, drange[1]),
            )
            slip.action_payslip_done()

            if i == 8:
                payslip = slip

        payslip_results = {'BASE': 1e7, 'BASIC': 1e7, 'BPJS_JKK': 24e3, 'BPJS_JKM': 3e4, 'BPJS_Kesehatan': 4e5, 'GROSS': 10454e3, 'JHT': -2e5, 'JP': -1e5, 'BPJS_KESEHATAN_DED': -1e5, 'JABATAN': 4e6, 'PKP': 25632e3, 'PTKP': 54e6, 'PPH21': 547850, 'NET': 10147850}
        self._validate_payslip(payslip, payslip_results)

    def test_end_of_contract_2(self):
        """ 15 Jan - 31 Dec + get the December's payslip (19) """
        self.contract.date_start = date(2024, 1, 15)

        for i in range(1, 13):
            drange = PERIOD[i]
            slip = self._generate_payslip(
                date(2024, i, drange[0]),
                date(2024, i, drange[1]),
            )
            slip.action_payslip_done()

            if i == 12:
                payslip = slip

        payslip_results = {'BASE': 1e7, 'BASIC': 1e7, 'BPJS_JKK': 24e3, 'BPJS_JKM': 3e4, 'BPJS_Kesehatan': 4e5, 'GROSS': 10454e3, 'JHT': -2e5, 'JP': -1e5, 'BPJS_KESEHATAN_DED': -1e5, 'PKP': 61107343.48, 'PTKP': 54e6, 'JABATAN': 5795439.13, 'PPH21': -523057.61, 'NET': 9076942.39}
        self._validate_payslip(payslip, payslip_results)

    def test_end_of_contract_3(self):
        """15 Jan - end of year, payroll cycle at 15th"""
        self.contract.date_start = date(2024, 1, 15)

        for i in range(1, 12):
            slip = self._generate_payslip(
                date(2024, i, 15),
                date(2024, i + 1, 14)
            )
            slip.action_payslip_done()

            if i == 11:
                payslip = slip

        payslip_results = {'BASE': 1e7, 'BASIC': 1e7, 'BPJS_JKK': 24e3, 'BPJS_JKM': 3e4, 'BPJS_Kesehatan': 4e5, 'GROSS': 10454e3, 'JHT': -2e5, 'JABATAN': 55e5, 'JP': -1e5, 'BPJS_KESEHATAN_DED': -1e5, 'PKP': 55494e3, 'PTKP': 54e6, 'PPH21': -161200, 'NET': 9438800}
        self._validate_payslip(payslip, payslip_results)

    def test_end_of_year_with_allowance(self):
        """ End of year testing with transport allowance (21) """
        self.contract.date_start = date(2024, 10, 1)
        self.contract.wage = 2e7
        for i in range(10, 12):
            drange = PERIOD[i]
            slip = self._generate_payslip(
                date(2024, i, drange[0]),
                date(2024, i, drange[1]),
                input_line_ids=[
                    Command.create(
                        {
                            'input_type_id': self.env.ref('l10n_id_hr_payroll.input_transport_allowance').id,
                            'amount': 2e6
                        })
                ]
            )
            slip.action_payslip_done()

        payslip = self._generate_payslip(
            date(2024, 12, 1),
            date(2024, 12, 31),
            input_line_ids=[
                Command.create(
                    {
                        'input_type_id': self.env.ref('l10n_id_hr_payroll.input_transport_allowance').id,
                        'amount': 2e6
                    })
            ]
        )

        payslip_results = {'BASIC': 2e7, 'TRANSPORT_ALW': 2e6, 'BASE': 22e6, 'BPJS_JKK': 48e3, 'BPJS_JKM': 6e4, 'BPJS_Kesehatan': 48e4, 'GROSS': 22588e3, 'JHT': -4e5, 'JP': -100423, 'JABATAN': 15e5, 'BPJS_KESEHATAN_DED': -12e4, 'PKP': 12264e3, 'PTKP': 54e6, 'PPH21': 3452640, 'NET': 24832217}
        self._validate_payslip(payslip, payslip_results)

    def test_new_joiner(self):
        """ New joiner starting in 15 January, payslip for January (22)"""
        self.contract.wage = 2e7
        self.contract.date_start = date(2024, 1, 15)

        payslip = self._generate_payslip(
            date(2024, 1, 1),
            date(2024, 1, 31),
        )
        payslip.l10n_id_include_bpjs_kesehatan = False
        payslip.compute_sheet()

        payslip_results = {'BASIC': 11304347.83, 'BASE': 11304347.83, 'BPJS_JKK': 27130.43, 'BPJS_JKM': 33913.04, 'GROSS': 11365391.31, 'JHT': -226086.96, 'JP': -100423.0, 'PPH21': -397788.7, 'NET': 10580049.18}
        self._validate_payslip(payslip, payslip_results)

    # =====================================
    # OTHERS: testing specific components by components for end of year payments
    # =============================================
    def test_pkp_ptkp_show_up(self):
        """ Only appear when end of contract and end of year. Also consider only the `date_to` field
        of the payslip"""

        # November 1-30 and December 1-31. November should not show while December should
        nov_payslip = self._generate_payslip(
            date(2024, 11, 1),
            date(2024, 11, 30)
        )
        dec_payslip = self._generate_payslip(
            date(2024, 12, 1),
            date(2024, 12, 31)
        )

        self.assertEqual(nov_payslip.l10n_id_include_pkp_ptkp, False)
        self.assertEqual(dec_payslip.l10n_id_include_pkp_ptkp, True)

        # November 15-Dec 14 should be True while December 15-Jan 14 should be False
        nov_payslip_2 = self._generate_payslip(
            date(2024, 11, 15),
            date(2024, 12, 14)
        )
        dec_payslip_2 = self._generate_payslip(
            date(2024, 12, 15),
            date(2025, 1, 14)
        )
        self.assertEqual(nov_payslip_2.l10n_id_include_pkp_ptkp, True)
        self.assertEqual(dec_payslip_2.l10n_id_include_pkp_ptkp, False)

    def test_end_of_year_jabatan(self):
        """" Test to make sure biaya jabatan at the end of year is correct"""
        # payroll cycle every 14th, employee starts from october
        payslip1 = self._generate_payslip(date(2024, 10, 15), date(2024, 11, 14))
        payslip1.action_payslip_done()
        payslip2 = self._generate_payslip(date(2024, 11, 15), date(2024, 12, 14))

        payslip_results = {'BASIC': 10000000.0, 'BASE': 10000000.0, 'BPJS_JKK': 24000.0, 'BPJS_JKM': 30000.0, 'BPJS_Kesehatan': 400000.0, 'GROSS': 10454000.0, 'JHT': -200000.0, 'BPJS_KESEHATAN_DED': -100000.0, 'JP': -100000.0, 'JABATAN': 1000000.0, 'PTKP': 54000000.0, 'PKP': 0.0, 'PPH21': 261350.0, 'NET': 9861350.0}
        self._validate_payslip(payslip2, payslip_results)

    def test_pkp_above_zero(self):
        """ Test that PKP is non-negative and when PKP is 0, then return all paid PPH21 amount """
        # joins november, pph21 of december is supposed to be -(pph21 of nov)
        self.contract.date_start = date(2024, 11, 1)

        nov_pslip = self._generate_payslip(
            date(2024, 11, 1),
            date(2024, 11, 3)
        )
        nov_pslip.action_payslip_done()

        dec_pslip = self._generate_payslip(
            date(2024, 12, 1),
            date(2024, 12, 31)
        )

        nov_payslip_results = {'BASIC': 10000000.0, 'BASE': 10000000.0, 'BPJS_JKK': 24000.0, 'BPJS_JKM': 30000.0, 'BPJS_Kesehatan': 400000.0, 'GROSS': 10454000.0, 'JHT': -200000.0, 'BPJS_KESEHATAN_DED': -100000.0, 'JP': -100000.0, 'PPH21': -261350.0, 'NET': 9338650.0}
        self._validate_payslip(nov_pslip, nov_payslip_results)

        dec_payslip_results = {'BASIC': 10000000.0, 'BASE': 10000000.0, 'BPJS_JKK': 24000.0, 'BPJS_JKM': 30000.0, 'BPJS_Kesehatan': 400000.0, 'GROSS': 10454000.0, 'JHT': -200000.0, 'BPJS_KESEHATAN_DED': -100000.0, 'JP': -100000.0, 'JABATAN': 1000000.0, 'PTKP': 54000000.0, 'PKP': 0.0, 'PPH21': 261350.0, 'NET': 9861350.0}
        self._validate_payslip(dec_pslip, dec_payslip_results)

        self.assertEqual(dec_payslip_results['PKP'], 0)
        self.assertEqual(dec_payslip_results['PPH21'], -nov_payslip_results['PPH21'])
