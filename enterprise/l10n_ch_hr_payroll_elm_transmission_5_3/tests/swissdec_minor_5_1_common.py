# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.tests.common import tagged
from odoo.tools import file_open
from odoo import Command

from .swissdec_minor_common import TestSwissdecMinorCommon

from datetime import datetime, date
from freezegun import freeze_time
from collections import defaultdict
from unittest.mock import patch


_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install', 'swissdec_payroll')
class TestSwissdecCommon(TestSwissdecMinorCommon):

    @classmethod
    def _l10n_ch_generate_swissdec_5_1_demo_data(cls, company):
        mapped_declarations = {}
        with freeze_time("2021-11-01"):
            # Generate Employees
            employees = cls.env['hr.employee'].with_context(tracking_disable=True).create([
                {'registration_number': '2', 'certificate': 'universityBachelor', 'name': "Maria Paganini", 'gender': 'female', 'company_id': company.id, 'country_id': cls.env.ref('base.it').id, 'l10n_ch_sv_as_number': '756.3598.1127.37', 'birthday': date(1958, 9, 30), 'marital': 'married', 'l10n_ch_marital_from': date(1992, 3, 13), 'private_street': 'Zentralstrasse 17', 'private_zip': '6030', 'private_city': 'Ebikon', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 1054, 'l10n_ch_residence_category': 'settled-C', 'l10n_ch_canton': 'LU', 'lang': 'de_DE'},
                {'registration_number': '2.1', 'certificate': 'universityBachelor', 'name': "Sandro Paganini", 'gender': 'male', 'company_id': company.id, 'country_id': cls.env.ref('base.it').id, 'l10n_ch_sv_as_number': '756.0000.9994.12', 'birthday': date(1957, 9, 30), 'marital': 'married', 'l10n_ch_marital_from': date(1992, 3, 13), 'private_street': 'Zentralstrasse 17', 'private_zip': '6030', 'private_city': 'Ebikon', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 1054, 'l10n_ch_residence_category': 'settled-C', 'l10n_ch_canton': 'LU', 'lang': 'de_DE'},
                {'registration_number': '3', 'certificate': 'vocEducationCompl', 'name': "Pia Lusser", 'gender': 'female', 'company_id': company.id, 'country_id': cls.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.6417.0995.23', 'birthday': date(1958, 2, 5), 'marital': 'married', 'l10n_ch_marital_from': date(1979, 8, 14), 'private_street': 'Buochserstrasse 4', 'private_zip': '6370', 'private_city': 'Stans', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 1509, 'l10n_ch_residence_category': False, 'l10n_ch_canton': 'NW', 'lang': 'de_DE'},
                {'registration_number': '3.1', 'certificate': 'vocEducationCompl', 'name': "Hans Lusser", 'gender': 'male', 'company_id': company.id, 'country_id': cls.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.0000.9994.29', 'birthday': date(1957, 2, 5), 'marital': 'married', 'l10n_ch_marital_from': date(1979, 8, 14), 'private_street': 'Buochserstrasse 4', 'private_zip': '6370', 'private_city': 'Stans', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 1509, 'l10n_ch_residence_category': False, 'l10n_ch_canton': 'NW', 'lang': 'de_DE'},
                {'registration_number': '9', 'certificate': 'doctorate', 'name': "Michael Estermann", 'gender': 'male', 'company_id': company.id, 'country_id': cls.env.ref('base.de').id, 'l10n_ch_sv_as_number': '756.1931.9954.43', 'birthday': date(1956, 1, 1), 'marital': 'married', 'l10n_ch_marital_from': date(1987, 4, 12), 'private_street': 'Seestrasse 3', 'private_zip': '6353', 'private_city': 'Weggis', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 1069, 'l10n_ch_residence_category': 'settled-C', 'l10n_ch_canton': 'LU', 'lang': 'de_DE'},
                {'registration_number': '9.1', 'certificate': 'doctorate', 'name': "Maria Estermann", 'gender': 'female', 'company_id': company.id, 'country_id': cls.env.ref('base.de').id, 'l10n_ch_sv_as_number': '756.0000.9994.36', 'birthday': date(1955, 1, 1), 'marital': 'married', 'l10n_ch_marital_from': date(1987, 4, 12), 'private_street': 'Seestrasse 3', 'private_zip': '6353', 'private_city': 'Weggis', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 1069, 'l10n_ch_residence_category': 'settled-C', 'l10n_ch_canton': 'LU', 'lang': 'de_DE'},
            ])
            mapped_employees = {}
            for index, employee in enumerate(employees, start=1):
                mapped_employees[f"employee_{employee.registration_number}"] = employee

            cdd_hourly = {"contract_type_id": cls.env.ref('l10n_ch_hr_payroll.l10n_ch_contract_type_fixedSalaryHrs').id}
            cdi_month = {"contract_type_id": cls.env.ref('l10n_ch_hr_payroll.l10n_ch_contract_type_indefiniteSalaryMth').id}

            info_m = cls.env['hr.job'].create({
                "name": "Informaticien"
            })
            # Generate Contracts
            contracts = cls.env['hr.contract'].with_context(tracking_disable=True).create([
                # TF 02
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdd_hourly, 'name': "Contract For Maria Paganini", 'irregular_working_time': True, 'l10n_ch_lpp_entry_reason': 'entryCompany', 'employee_id': mapped_employees['employee_2'].id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'wage_type': "hourly", 'l10n_ch_has_hourly': True, "l10n_ch_contractual_13th_month_rate": 8.33, 'wage': 0, 'hourly_wage': 30.0, 'l10n_ch_lesson_wage': 30, 'l10n_ch_has_lesson': True, 'state': "open", 'l10n_ch_social_insurance_id': cls.avs_2.id, 'l10n_ch_laa_group': cls.laa_group_A, 'laa_solution_number': '1', 'l10n_ch_location_unit_id': cls.location_unit_1.id, "l10n_ch_lpp_not_insured": True, 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': cls.caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 0, 'l10n_ch_contractual_holidays_rate': 13.04, 'l10n_ch_contractual_public_holidays_rate': 4},
                # TF 2.1
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdd_hourly, 'name': "Contract For Maria Paganini", 'irregular_working_time': True, 'l10n_ch_lpp_entry_reason': 'entryCompany', 'employee_id': mapped_employees['employee_2.1'].id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'wage_type': "hourly", 'l10n_ch_has_hourly': True, "l10n_ch_contractual_13th_month_rate": 8.33, 'wage': 0, 'hourly_wage': 30.0, 'l10n_ch_lesson_wage': 30, 'l10n_ch_has_lesson': True, 'state': "open", 'l10n_ch_social_insurance_id': cls.avs_2.id, 'l10n_ch_laa_group': cls.laa_group_A, 'laa_solution_number': '1', 'l10n_ch_location_unit_id': cls.location_unit_1.id, "l10n_ch_lpp_not_insured": True, 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': cls.caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 0, 'l10n_ch_contractual_holidays_rate': 13.04, 'l10n_ch_contractual_public_holidays_rate': 4},
                # TF 03
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdi_month, 'name': "Contract For Lusser Pia", 'l10n_ch_location_unit_id': cls.location_unit_1.id, 'lpp_employee_amount': 385, 'employee_id': mapped_employees['employee_3'].id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 5500, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': cls.avs_2.id, 'l10n_ch_laa_group': cls.laa_group_A, 'laa_solution_number': '1', "l10n_ch_lpp_not_insured": True,  'l10n_ch_lpp_insurance_id': cls.lpp_0.id, 'l10n_ch_compensation_fund_id': cls.caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 30},
                # TF 3.1
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdi_month, 'name': "Contract For Lusser Pia", 'l10n_ch_location_unit_id': cls.location_unit_1.id, 'lpp_employee_amount': 385, 'employee_id': mapped_employees['employee_3.1'].id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 5500, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': cls.avs_2.id, 'l10n_ch_laa_group': cls.laa_group_A, 'laa_solution_number': '1', 'l10n_ch_lpp_insurance_id': cls.lpp_0.id, 'l10n_ch_compensation_fund_id': cls.caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 30},
                # TF 09
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdi_month, 'name': "Contract full time For Estermann Michael", 'l10n_ch_location_unit_id': cls.location_unit_1.id, 'employee_id': mapped_employees['employee_9'].id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 2000, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': cls.avs_2.id, 'l10n_ch_laa_group': cls.laa_group_A, 'laa_solution_number': '3', "l10n_ch_lpp_not_insured": True,  'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': cls.caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 30, 'l10n_ch_avs_status': 'retired'},
                # TF 9.1
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdi_month, 'name': "Contract full time For Estermann Michael", 'l10n_ch_location_unit_id': cls.location_unit_1.id, 'employee_id': mapped_employees['employee_9.1'].id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 2000, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': cls.avs_2.id, 'l10n_ch_laa_group': cls.laa_group_A, 'laa_solution_number': '3', "l10n_ch_lpp_not_insured": True,  'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': cls.caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 30, 'l10n_ch_avs_status': 'retired_wave_deduct'},
            ])
            contracts_by_employee = defaultdict(lambda: cls.env['hr.contract'])
            for contract in contracts:
                contracts_by_employee[contract.employee_id] += contract
            mapped_contracts = {}
            for eidx, employee in enumerate(employees, start=1):
                for cidx, contract in enumerate(contracts_by_employee[employee], start=1):
                    mapped_contracts[f"contract_{contract.employee_id.registration_number}"] = contract

            all_emps = cls.env["hr.employee"]
            for emp in mapped_employees:
                all_emps += mapped_employees[emp]

            cls.env['l10n.ch.hr.contract.wage'].create([
                # TF02
                {'description': 'Salaire horaire', 'amount': 150.0, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Salaire horaire', 'amount': 70.0, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Salaire horaire', 'amount': 70.0, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Salaire horaire', 'amount': 142.0, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Salaire horaire', 'amount': 20.0, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Salaire horaire', 'amount': 100.0, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Salaire horaire', 'amount': 120.0, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Salaire horaire', 'amount': 130.0, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Salaire horaire', 'amount': 162.0, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Salaire horaire', 'amount': 50.0, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Salaire horaire', 'amount': 162.0, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Salaire horaire', 'amount': 150.0, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Salaire horaire', 'amount': 120.0, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Salaire horaire', 'amount': 50.0, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Salaire à la leçon', 'amount': 20.0, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Salaire à la leçon', 'amount': 20.0, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Salaire à la leçon', 'amount': 40.0, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Salaire à la leçon', 'amount': 20.0, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Salaire à la leçon', 'amount': 20.0, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Salaire à la leçon', 'amount': 20.0, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Salaire à la leçon', 'amount': 20.0, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Salaire à la leçon', 'amount': 20.0, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 90, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 50, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 25, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 35, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 40, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 35, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 105, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 89, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 81, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 95, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Commission', 'amount': 2044, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1218').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Perte de gain RHT/ITP (SH)', 'amount': 3000, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2065').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Perte de gain RHT/ITP (SH)', 'amount': 3000, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2065').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Indemnité de chômage', 'amount': 2200, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2070').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Indemnité de chômage', 'amount': 2200, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2070').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Délai de carence RHT/ITP', 'amount': 200, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2075').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Délai de carence RHT/ITP', 'amount': 200, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2075').id, 'contract_id': mapped_contracts['contract_2'].id},
                {'description': 'Allocation pour enfant', 'amount': 200, 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_2'].id},

                {'description': 'Salaire horaire', 'amount': 150.0, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Salaire horaire', 'amount': 70.0, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Salaire horaire', 'amount': 70.0, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Salaire horaire', 'amount': 142.0, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Salaire horaire', 'amount': 20.0, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Salaire horaire', 'amount': 100.0, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Salaire horaire', 'amount': 120.0, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Salaire horaire', 'amount': 130.0, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Salaire horaire', 'amount': 162.0, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Salaire horaire', 'amount': 50.0, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Salaire horaire', 'amount': 162.0, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Salaire horaire', 'amount': 150.0, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Salaire horaire', 'amount': 120.0, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Salaire horaire', 'amount': 50.0, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Salaire à la leçon', 'amount': 20.0, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Salaire à la leçon', 'amount': 20.0, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Salaire à la leçon', 'amount': 40.0, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Salaire à la leçon', 'amount': 20.0, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Salaire à la leçon', 'amount': 20.0, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Salaire à la leçon', 'amount': 20.0, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Salaire à la leçon', 'amount': 20.0, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Salaire à la leçon', 'amount': 20.0, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 90, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 50, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 25, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 35, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 40, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 35, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 105, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 89, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 81, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 95, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Commission', 'amount': 2044, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1218').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Perte de gain RHT/ITP (SH)', 'amount': 3000, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2065').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Perte de gain RHT/ITP (SH)', 'amount': 3000, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2065').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Indemnité de chômage', 'amount': 2200, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2070').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Indemnité de chômage', 'amount': 2200, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2070').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Délai de carence RHT/ITP', 'amount': 200, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2075').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Délai de carence RHT/ITP', 'amount': 200, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2075').id, 'contract_id': mapped_contracts['contract_2.1'].id},
                {'description': 'Allocation pour enfant', 'amount': 200, 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_2.1'].id},


                # TF03
                {'description': 'Indemnité spéciale', 'amount': 3200, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1212').id, 'contract_id': mapped_contracts['contract_3'].id},
                {'description': 'Indemnité spéciale', 'amount': 3200, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1212').id, 'contract_id': mapped_contracts['contract_3'].id},
                {'description': 'Cadeau pour ancienneté de service', 'amount': 22000, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1230').id, 'contract_id': mapped_contracts['contract_3'].id},
                {'description': 'Prestation en capital à caractère de prévoyance', 'amount': 6000, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1410').id, 'contract_id': mapped_contracts['contract_3'].id},

                {'description': 'Indemnité spéciale', 'amount': 3200, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1212').id, 'contract_id': mapped_contracts['contract_3.1'].id},
                {'description': 'Indemnité spéciale', 'amount': 3200, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1212').id, 'contract_id': mapped_contracts['contract_3.1'].id},
                {'description': 'Cadeau pour ancienneté de service', 'amount': 22000, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1230').id, 'contract_id': mapped_contracts['contract_3.1'].id},
                {'description': 'Prestation en capital à caractère de prévoyance', 'amount': 6000, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1410').id, 'contract_id': mapped_contracts['contract_3.1'].id},

                # TF09
                {'description': 'Gratification', 'amount': 1700, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1204').id, 'contract_id': mapped_contracts['contract_9'].id},
                {'description': 'Gratification', 'amount': 200, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1204').id, 'contract_id': mapped_contracts['contract_9'].id},
                {'description': 'Indemnité spéciale', 'amount': 35000, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1212').id, 'contract_id': mapped_contracts['contract_9'].id},
                {'description': 'Indemnité journalière accident', 'amount': 30000, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2030').id, 'contract_id': mapped_contracts['contract_9'].id},
                {'description': 'Indemnité journalière accident', 'amount': 32000, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2030').id, 'contract_id': mapped_contracts['contract_9'].id},
                {'description': 'Correction indemnité de tiers', 'amount': 30000, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2050').id,  'contract_id': mapped_contracts['contract_9'].id},
                {'description': 'Correction indemnité de tiers', 'amount': 32000, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2050').id,  'contract_id': mapped_contracts['contract_9'].id},

                {'description': 'Gratification', 'amount': 1700, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1204').id, 'contract_id': mapped_contracts['contract_9.1'].id},
                {'description': 'Gratification', 'amount': 200, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1204').id, 'contract_id': mapped_contracts['contract_9.1'].id},
                {'description': 'Indemnité spéciale', 'amount': 35000, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1212').id, 'contract_id': mapped_contracts['contract_9.1'].id},
                {'description': 'Indemnité journalière accident', 'amount': 30000, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2030').id, 'contract_id': mapped_contracts['contract_9.1'].id},
                {'description': 'Indemnité journalière accident', 'amount': 32000, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2030').id, 'contract_id': mapped_contracts['contract_9.1'].id},
                {'description': 'Correction indemnité de tiers', 'amount': 30000, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2050').id,  'contract_id': mapped_contracts['contract_9.1'].id},
                {'description': 'Correction indemnité de tiers', 'amount': 32000, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2050').id,  'contract_id': mapped_contracts['contract_9.1'].id},
            ])
        with freeze_time("2022-01-26"):

            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 1, 1))

            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 01/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        with freeze_time("2022-02-26"):
            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 2, 1))

            mapped_contracts["contract_3"].write({
                "l10n_ch_lpp_not_insured": True,
                "l10n_ch_lpp_withdrawal_reason": "retirement",
                "l10n_ch_lpp_withdrawal_valid_as_of": date(2022, 2, 28)
            })
            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 02/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        with freeze_time("2022-03-26"):
            mapped_contracts["contract_3"].write({
                'wage': 1500,
                'l10n_ch_laa_group': cls.laa_group_A, 'laa_solution_number': '3',
                'l10n_ch_avs_status': 'retired',
                'l10n_ch_weekly_hours': 8.4
            })

            mapped_contracts["contract_3.1"].write({
                'wage': 1500,
                'l10n_ch_laa_group': cls.laa_group_A, 'laa_solution_number': '3',
                'l10n_ch_avs_status': 'retired_wave_deduct',
                'l10n_ch_weekly_hours': 8.4
            })


            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 3, 1))

            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 03/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        with freeze_time("2022-04-26"):
            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 4, 1))
            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 04/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        with freeze_time("2022-05-26"):
            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 5, 1))
            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 05/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        with freeze_time("2022-06-26"):

            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 6, 1))
            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 06/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        with freeze_time("2022-07-26"):

            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 7, 1))

            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 07/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        with freeze_time("2022-08-26"):
            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 8, 1))

            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 08/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        with freeze_time("2022-09-26"):
            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 9, 1))
            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 09/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        with freeze_time("2022-10-26"):

            mapped_contracts['contract_9'].write({'wage': 1000, 'l10n_ch_weekly_hours': 21})
            mapped_contracts['contract_9.1'].write({'wage': 1000, 'l10n_ch_weekly_hours': 21})

            mapped_contracts['contract_2'].write({
                "l10n_ch_avs_status": "retired"
            })
            mapped_contracts['contract_2.1'].write({
                "l10n_ch_avs_status": "retired"
            })

            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 10, 1))

            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 10/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        with freeze_time("2022-11-26"):
            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 11, 1))
            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 11/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        with freeze_time("2022-12-26"):
            cls.env["l10n.ch.avs.splits"].create({
                "employee_id": mapped_employees["employee_9"].id,
                "year": datetime.now().year,
                "additional_delivery_date": date(2023, 2, 14),
                "state": "confirmed"
            })
            cls.env["l10n.ch.avs.splits"].create({
                "employee_id": mapped_employees["employee_9.1"].id,
                "year": datetime.now().year,
                "additional_delivery_date": date(2023, 2, 14),
                "state": "confirmed"
            })
            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 12, 1))

            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 12/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        with freeze_time("2023-01-26"):
            # 2023-01
            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2023, 1, 1))

            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 01/2023",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        with freeze_time("2023-02-26"):
            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2023, 2, 1))

            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 02/2023",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'yearly_retrospective_5_1_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        return mapped_declarations

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with patch.object(cls.env.registry['l10n.ch.employee.yearly.values'], '_generate_certificate_uuid', lambda self: "#DOC-ID"):
            mapped_declarations = cls._l10n_ch_generate_swissdec_5_1_demo_data(cls.muster_ag_company)

        for identifier, declaration in mapped_declarations.items():
            assert isinstance(identifier, str)
            setattr(cls, identifier, declaration)
