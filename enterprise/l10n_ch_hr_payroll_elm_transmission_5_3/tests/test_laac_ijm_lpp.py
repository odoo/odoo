# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.tests.common import tagged
from odoo.tools import file_open
from odoo import Command

from .swissdec_minor_common import TestSwissdecMinorCommon

from datetime import datetime, date
from freezegun import freeze_time


_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install', 'swissdec_payroll')
class TestSwissdecCommon(TestSwissdecMinorCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.laac_1 = cls.env['l10n.ch.additional.accident.insurance'].create({
            'name': 'Backwork-Versicherungen',
            'customer_number': '7651-873.1',
            "company_id": cls.muster_ag_company.id,
            'contract_number': '4566-4',
            'insurance_company': 'Backwork-Versicherungen',
            'insurance_code': 'S1000',
            'line_ids': [
                (0, 0, {
                    'solution_name': 'Group 1',
                    'solution_type': '1',
                    'solution_number': '0',
                    'rate_ids': [(0, 0, {
                        'date_from': date(2021, 1, 1),
                        'wage_from': 0,
                        'wage_to': 300000,
                        'male_rate': 1.2456,
                        'female_rate': 1.4756,
                        'employer_part': '50',
                    })],
                }),
            ]
        })
        cls.ijm_1 = cls.env['l10n.ch.sickness.insurance'].create({
            "name": 'Backwork-Versicherungen',
            "company_id": cls.muster_ag_company.id,
            "customer_number": '7651-873.1',
            "contract_number": '4567-4',
            "insurance_company": 'Backwork-Versicherungen',
            "insurance_code": 'S1000',
            "line_ids": [
                (0, 0, {
                    "solution_name": "Group 1",
                    "solution_type": "1",
                    "solution_number": "0",
                    "rate_ids": [(0, 0, {
                        'date_from': date(2021, 1, 1),
                        'wage_from': 0,
                        'wage_to': 300000,
                        'male_rate': 1.2456,
                        'female_rate': 1.4756,
                        'employer_part': '50',
                    })]
                }),
            ]
        })

        cls.laac_solution = cls.laac_1.line_ids[0]
        cls.ijm_solution = cls.ijm_1.line_ids[0]
        cls.caf_lu_2 = cls.env['l10n.ch.compensation.fund'].create({
            "name": 'Familienausgleichskassen Kanton Luzern',
            "company_id": cls.muster_ag_company.id,
            "member_number": '100-9976.70',
            "member_subnumber": '',
            "insurance_company": 'Familienausgleichskassen Kanton Luzern',
            "insurance_code": '003.000',
            "caf_line_ids": [(0, 0, {
                'date_from': date(2021, 1, 1),
                'date_to': False,
                'employee_rate': 0,
                'company_rate': 0,
            })],
        })



        cls.employee_male = cls.env['hr.employee'].create([
            {'registration_number': '3', 'certificate': 'vocEducationCompl', 'name': "Lusser Pia", 'gender': 'male', 'company_id': cls.muster_ag_company.id, 'country_id': cls.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.6417.0995.23', 'birthday': date(1958, 2, 5), 'marital': 'married', 'l10n_ch_marital_from': date(1979, 8, 14), 'private_street': 'Buochserstrasse 4', 'private_zip': '6370', 'private_city': 'Stans', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 1509, 'l10n_ch_residence_category': False, 'l10n_ch_canton': 'NW', 'lang': 'de_DE'},
        ])

        cls.employee_female = cls.env['hr.employee'].create([
            {'registration_number': '4', 'certificate': 'vocEducationCompl', 'name': "Lusser Pia", 'gender': 'female', 'company_id': cls.muster_ag_company.id, 'country_id': cls.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.6417.0995.23', 'birthday': date(1958, 2, 5), 'marital': 'married', 'l10n_ch_marital_from': date(1979, 8, 14), 'private_street': 'Buochserstrasse 4', 'private_zip': '6370', 'private_city': 'Stans', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 1509, 'l10n_ch_residence_category': False, 'l10n_ch_canton': 'NW', 'lang': 'de_DE'},
        ])

        cls.contract_male = cls.env['hr.contract'].with_context(tracking_disable=True).create([
            {"l10n_ch_job_type": "noCadre", 'l10n_ch_lpp_percentage_employee': 10.45, 'l10n_ch_lpp_percentage_employer': 12.643, 'l10n_ch_lpp_in_percentage': True, 'name': "Contract For Lusser Pia", 'l10n_ch_sickness_insurance_line_ids': [(4, cls.ijm_solution.id)], 'l10n_ch_additional_accident_insurance_line_ids': [(4, cls.laac_solution.id)], 'l10n_ch_location_unit_id': cls.location_unit_2.id, 'lpp_employee_amount': 385, 'employee_id': cls.employee_female.id, 'company_id': cls.muster_ag_company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1 / 12) * 100, 'wage': 10000, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': cls.avs_2.id, 'l10n_ch_laa_group': cls.laa_group_A, 'laa_solution_number': '1', "l10n_ch_lpp_not_insured": False, 'l10n_ch_lpp_insurance_id': cls.lpp_0.id, 'l10n_ch_compensation_fund_id': cls.caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 30},
        ])

        cls.contract_female = cls.env['hr.contract'].with_context(tracking_disable=True).create([
            {"l10n_ch_job_type": "noCadre", 'l10n_ch_lpp_percentage_employee': 9.1245, 'l10n_ch_lpp_percentage_employer': 4.643, 'l10n_ch_lpp_in_percentage': True, 'name': "Contract For John Pia", 'l10n_ch_sickness_insurance_line_ids': [(4, cls.ijm_solution.id)], 'l10n_ch_additional_accident_insurance_line_ids': [(4, cls.laac_solution.id)], 'l10n_ch_location_unit_id': cls.location_unit_2.id, 'lpp_employee_amount': 385, 'employee_id': cls.employee_male.id, 'company_id': cls.muster_ag_company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1 / 12) * 100, 'wage': 10000, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': cls.avs_2.id, 'l10n_ch_laa_group': cls.laa_group_A, 'laa_solution_number': '1', "l10n_ch_lpp_not_insured": False, 'l10n_ch_lpp_insurance_id': cls.lpp_0.id, 'l10n_ch_compensation_fund_id': cls.caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 30},
        ])


    @freeze_time("2022-01-01")
    def test_01_no_custom_parts(self):
        slips = self._l10n_ch_create_batch(self.muster_ag_company, 1).slip_ids
        self.assertEqual(slips[0].line_ids.filtered(lambda l: l.code == "LAAC1").rate, -1.4756/2)
        self.assertEqual(slips[0].line_ids.filtered(lambda l: l.code == "LAAC1.COMP").rate, 1.4756/2)
        self.assertEqual(slips[1].line_ids.filtered(lambda l: l.code == "LAAC1").rate, -1.2456/2)
        self.assertEqual(slips[1].line_ids.filtered(lambda l: l.code == "LAAC1.COMP").rate, 1.2456/2)

        self.assertEqual(slips[0].line_ids.filtered(lambda l: l.code == "IJM1").rate, -1.4756/2)
        self.assertEqual(slips[0].line_ids.filtered(lambda l: l.code == "IJM1.COMP").rate, 1.4756/2)
        self.assertEqual(slips[1].line_ids.filtered(lambda l: l.code == "IJM1").rate, -1.2456/2)
        self.assertEqual(slips[1].line_ids.filtered(lambda l: l.code == "IJM1.COMP").rate, 1.2456/2)

        self.laac_solution.rate_ids.write({
            'employer_part': '0'
        })
        self.ijm_solution.rate_ids.write({
            'employer_part': '0'
        })

        slips = self._l10n_ch_create_batch(self.muster_ag_company, 1).slip_ids
        self.assertEqual(slips[0].line_ids.filtered(lambda l: l.code == "LAAC1").rate, -1.4756)
        self.assertEqual(slips[0].line_ids.filtered(lambda l: l.code == "LAAC1.COMP").rate, 0)
        self.assertEqual(slips[1].line_ids.filtered(lambda l: l.code == "LAAC1").rate, -1.2456)
        self.assertEqual(slips[1].line_ids.filtered(lambda l: l.code == "LAAC1.COMP").rate, 0)

        self.assertEqual(slips[0].line_ids.filtered(lambda l: l.code == "IJM1").rate, -1.4756)
        self.assertEqual(slips[0].line_ids.filtered(lambda l: l.code == "IJM1.COMP").rate, 0)
        self.assertEqual(slips[1].line_ids.filtered(lambda l: l.code == "IJM1").rate, -1.2456)
        self.assertEqual(slips[1].line_ids.filtered(lambda l: l.code == "IJM1.COMP").rate, 0)

        self.laac_solution.rate_ids.write({
            'employer_part': '100'
        })
        self.ijm_solution.rate_ids.write({
            'employer_part': '100'
        })

        slips = self._l10n_ch_create_batch(self.muster_ag_company, 1).slip_ids
        self.assertEqual(slips[0].line_ids.filtered(lambda l: l.code == "LAAC1").rate, 0)
        self.assertEqual(slips[0].line_ids.filtered(lambda l: l.code == "LAAC1.COMP").rate, 1.4756)
        self.assertEqual(slips[1].line_ids.filtered(lambda l: l.code == "LAAC1").rate, 0)
        self.assertEqual(slips[1].line_ids.filtered(lambda l: l.code == "LAAC1.COMP").rate, 1.2456)

        self.assertEqual(slips[0].line_ids.filtered(lambda l: l.code == "IJM1").rate, 0)
        self.assertEqual(slips[0].line_ids.filtered(lambda l: l.code == "IJM1.COMP").rate, 1.4756)
        self.assertEqual(slips[1].line_ids.filtered(lambda l: l.code == "IJM1").rate, 0)
        self.assertEqual(slips[1].line_ids.filtered(lambda l: l.code == "IJM1.COMP").rate, 1.2456)

    @freeze_time("2022-01-01")
    def test_02_with_custom_parts(self):
        self.laac_solution.rate_ids.write({
            "custom_employer_rates": True,
            "employer_rate_male": 3.9989,
            "employer_rate_female": 2.1999
        })
        self.ijm_solution.rate_ids.write({
            "custom_employer_rates": True,
            "employer_rate_male": 9.9999,
            "employer_rate_female": 1.8989
        })

        slips = self._l10n_ch_create_batch(self.muster_ag_company, 1).slip_ids
        self.assertAlmostEqual(slips[0].line_ids.filtered(lambda l: l.code == "LAAC1").rate, -1.4756, 6)
        self.assertAlmostEqual(slips[0].line_ids.filtered(lambda l: l.code == "LAAC1.COMP").rate, 2.1999, 6)
        self.assertAlmostEqual(slips[1].line_ids.filtered(lambda l: l.code == "LAAC1").rate, -1.2456, 6)
        self.assertAlmostEqual(slips[1].line_ids.filtered(lambda l: l.code == "LAAC1.COMP").rate, 3.9989, 6)

        self.assertAlmostEqual(slips[0].line_ids.filtered(lambda l: l.code == "IJM1").rate, -1.4756, 6)
        self.assertAlmostEqual(slips[0].line_ids.filtered(lambda l: l.code == "IJM1.COMP").rate, 1.8989, 6)
        self.assertAlmostEqual(slips[1].line_ids.filtered(lambda l: l.code == "IJM1").rate, -1.2456, 6)
        self.assertAlmostEqual(slips[1].line_ids.filtered(lambda l: l.code == "IJM1.COMP").rate, 9.9999, 6)

    @freeze_time("2022-01-01")
    def test_03_lpp_in_percentage(self):
        slips = self._l10n_ch_create_batch(self.muster_ag_company, 1).slip_ids
        self.assertEqual(slips[0].line_ids.filtered(lambda l: l.code == "LPPSALARY").total, 5355, 2)
        self.assertAlmostEqual(slips[0].line_ids.filtered(lambda l: l.code == "PP.PERCENTAGE").total, -559.6, 2)
        self.assertAlmostEqual(slips[0].line_ids.filtered(lambda l: l.code == "PP.PERCENTAGE.COMP").total, 677.05, 2)

        self.assertEqual(slips[1].line_ids.filtered(lambda l: l.code == "LPPSALARY").total, 5355, 2)
        self.assertAlmostEqual(slips[1].line_ids.filtered(lambda l: l.code == "PP.PERCENTAGE").total, -488.6, 2)
        self.assertAlmostEqual(slips[1].line_ids.filtered(lambda l: l.code == "PP.PERCENTAGE.COMP").total, 248.65, 2)

    @freeze_time("2022-01-01")
    def test_04_lpp_negative_avs_salary(self):
        self.env['l10n.ch.hr.contract.wage'].create([
            {'description': 'Indemnité accident', 'amount': 30000, 'date_start': date(2022, 1, 1), 'input_type_id': self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2030').id, 'contract_id': self.contract_male.id},
            {'description': 'Correction indemnité de tier', 'amount': 30000, 'date_start': date(2022, 1, 1), 'input_type_id': self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2050').id, 'contract_id': self.contract_male.id},
            {'description': 'Indemnité accident', 'amount': 30000, 'date_start': date(2022, 1, 1), 'input_type_id': self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2030').id, 'contract_id': self.contract_female.id},
            {'description': 'Correction indemnité de tier', 'amount': 30000, 'date_start': date(2022, 1, 1), 'input_type_id': self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2050').id, 'contract_id': self.contract_female.id},
        ])
        slips = self._l10n_ch_create_batch(self.muster_ag_company, 1).slip_ids
        self.assertEqual(slips[0].line_ids.filtered(lambda l: l.code == "AVSSALARY").total, -20000, 2)
        self.assertEqual(slips[0].line_ids.filtered(lambda l: l.code == "LPPSALARY").total, 5355.0, 2)
        self.assertAlmostEqual(slips[0].line_ids.filtered(lambda l: l.code == "PP.PERCENTAGE").total, -559.6, 2)
        self.assertAlmostEqual(slips[0].line_ids.filtered(lambda l: l.code == "PP.PERCENTAGE.COMP").total, 677.05, 2)

        self.assertEqual(slips[1].line_ids.filtered(lambda l: l.code == "AVSSALARY").total, -20000, 2)
        self.assertEqual(slips[1].line_ids.filtered(lambda l: l.code == "LPPSALARY").total, 5355.0, 2)
        self.assertAlmostEqual(slips[1].line_ids.filtered(lambda l: l.code == "PP.PERCENTAGE").total, -488.6, 2)
        self.assertAlmostEqual(slips[1].line_ids.filtered(lambda l: l.code == "PP.PERCENTAGE.COMP").total, 248.65, 2)

    @freeze_time("2022-01-01")
    def test_05_lpp_lower_than_coordination(self):
        (self.contract_female + self.contract_male).write({
            "wage": 2500
        })

        slips = self._l10n_ch_create_batch(self.muster_ag_company, 1).slip_ids
        self.assertEqual(slips[0].line_ids.filtered(lambda l: l.code == "AVSSALARY").total, 2500, 2)
        self.assertEqual(slips[0].line_ids.filtered(lambda l: l.code == "LPPSALARY").total, 315, 2)
        self.assertAlmostEqual(slips[0].line_ids.filtered(lambda l: l.code == "PP.PERCENTAGE").total, -32.9, 2)
        self.assertAlmostEqual(slips[0].line_ids.filtered(lambda l: l.code == "PP.PERCENTAGE.COMP").total, 39.85, 2)

        self.assertEqual(slips[1].line_ids.filtered(lambda l: l.code == "AVSSALARY").total, 2500, 2)
        self.assertEqual(slips[1].line_ids.filtered(lambda l: l.code == "LPPSALARY").total, 315, 2)
        self.assertAlmostEqual(slips[1].line_ids.filtered(lambda l: l.code == "PP.PERCENTAGE").total, -28.75, 2)
        self.assertAlmostEqual(slips[1].line_ids.filtered(lambda l: l.code == "PP.PERCENTAGE.COMP").total, 14.65, 2)

    @freeze_time("2022-01-01")
    def test_06_family_allowances_logic(self):
        """
        Test the Swiss Family Allowance logic:
        1. Ranks (Standard vs 3rd child+).
        2. Age Limits (Child vs Education).
        3. Status impacts (Non-responsible, Dependent).
        4. Supplementary amounts.
        """

        self.caf_lu_2.write({
            'caf_scale_ids': [
                (0, 0, {
                    'min_age': 0, 'max_age': 16, 'min_child_rank': 1,
                    'amount': 200.0, 'allowance_type': 'child',
                    'amount_supplementary': 15.0
                }),
                (0, 0, {
                    'min_age': 16, 'max_age': 25, 'min_child_rank': 1,
                    'amount': 250.0, 'allowance_type': 'education',
                    'amount_supplementary': 0.0
                }),
                (0, 0, {
                    'min_age': 0, 'max_age': 16, 'min_child_rank': 3,
                    'amount': 300.0, 'allowance_type': 'child',
                    'amount_supplementary': 20.0
                }),
                (0, 0, {
                    'min_age': 16, 'max_age': 25, 'min_child_rank': 3,
                    'amount': 350.0, 'allowance_type': 'education',
                    'amount_supplementary': 0.0
                }),
            ]
        })


        # Child 1:
        # Should get Education Allowance (Rule 2). Rank 1.
        child_1 = self.env['l10n.ch.hr.employee.children'].create({
            'name': 'Child 1 (18y)',
            'employee_id': self.employee_male.id,
            'birthdate': date(2004, 1, 1),
            'l10n_ch_child_status': 'responsible',
            'allowance_eligible': True,
        })

        # Child 2:
        # Should get Child Allowance (Rule 1). Rank 2.
        self.env['l10n.ch.hr.employee.children'].create({
            'name': 'Child 2 (10y)',
            'employee_id': self.employee_male.id,
            'birthdate': date(2012, 1, 1),
            'l10n_ch_child_status': 'responsible',
            'allowance_eligible': True,
            'allowance_supplementary_eligible': True,
        })

        # Child 3:
        # Should get Child Allowance Boost (Rule 3). Rank 3.
        self.env['l10n.ch.hr.employee.children'].create({
            'name': 'Child 3 (2y)',
            'employee_id': self.employee_male.id,
            'birthdate': date(2020, 1, 1),
            'l10n_ch_child_status': 'responsible',
            'allowance_eligible': True,
            'allowance_supplementary_eligible': True,
        })

        # Child 1 (18y) Responsible: Child Allowance ended at 16, Edu ends at 25.
        self.assertEqual(child_1.child_allowance_end_date, date(2020, 1, 31)) # End of month of 16th bday
        self.assertEqual(child_1.education_allowance_end_date, date(2029, 1, 31))

        batch = self._l10n_ch_create_batch(self.muster_ag_company, 1)
        slip = batch.slip_ids.filtered(lambda s: s.employee_id == self.employee_male)

        # Input Codes
        input_child = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000')
        input_edu = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3010')

        self.assertTrue(len(slip.input_line_ids), 3)

        # Child 1: Rank 1, Age 18 -> Education (250)
        line_c1 = slip.input_line_ids.filtered(
            lambda l: l.input_type_id == input_edu and l.amount == 250.0
        )
        self.assertTrue(line_c1, "Child 1 should receive Education Allowance of 250")

        # Child 2: Rank 2, Age 10 -> Child (200)
        line_c2 = slip.input_line_ids.filtered(
            lambda l: l.input_type_id == input_child and l.amount == 215.0
        )
        self.assertTrue(line_c2, "Child 2 should receive Child Allowance of 200")

        # Child 3: Rank 3, Age 2 -> Child Boost (300) + Suppl (20) = 320
        line_c3 = slip.input_line_ids.filtered(
            lambda l: l.input_type_id == input_child and l.amount == 320.0
        )
        self.assertTrue(line_c3, "Child 3 should receive Boosted Allowance + Supplementary (300+20)")

        # Create Child 4: Age 19.
        # Dependent: Gets CHILD Allowance (extended to 20).
        child_4 = self.env['l10n.ch.hr.employee.children'].create({
            'name': 'Child 4 (19y)',
            'employee_id': self.employee_male.id,
            'birthdate': date(2003, 1, 1),
            'l10n_ch_child_status': 'dependent', # Incapable of work
            'allowance_eligible': True,
            'allowance_supplementary_eligible': True,
        })

        child_4._compute_allowance_dates()

        self.assertEqual(child_4.child_allowance_end_date, date(2023, 1, 31))

        batch = self._l10n_ch_create_batch(self.muster_ag_company, 1)
        slip = batch.slip_ids.filtered(lambda s: s.employee_id == self.employee_male)

        self.assertEqual(len(slip.input_line_ids), 4)

        line_c1 = slip.input_line_ids.filtered(
            lambda l: l.input_type_id == input_edu and l.amount == 250.0
        )
        self.assertEqual(len(line_c1), 2, "2 Children should receive Education Allowance of 250")

        line_c2 = slip.input_line_ids.filtered(
            lambda l: l.input_type_id == input_child and l.amount == 320.0
        )
        self.assertEqual(len(line_c2), 2, "2 Children should receive Child Allowance of 320")
