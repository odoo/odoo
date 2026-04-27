# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pdb

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import tagged
from odoo.tools import file_open
from odoo import Command

from .swissdec_minor_common import TestSwissdecMinorCommon

import json
from datetime import datetime, date
from freezegun import freeze_time
from collections import defaultdict
from unittest.mock import patch


_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install', 'swissdec_payroll')
class TestSwissdecCommon(TestSwissdecMinorCommon):
    @classmethod
    def _l10n_ch_generate_swissdec_5_3_demo_data(cls, company):
        mapped_declarations = {}
        with freeze_time("2021-11-01"):
            employees = cls.env['hr.employee'].with_context(tracking_disable=True).create([
                {'registration_number': '381', 'certificate': 'doctorate', "l10n_ch_cross_border_start": date(2022, 11, 1), "l10n_ch_cross_border_commuter": True, 'l10n_ch_telework_percentage': 0.2, 'name': "Josefine Dubois", 'gender': 'female', 'company_id': company.id, 'country_id': cls.env.ref('base.fr').id, 'l10n_ch_sv_as_number': False, 'birthday': date(1998, 1, 15), 'marital': 'single', 'l10n_ch_marital_from': date(1998, 1, 15), 'private_street': 'Grand Rue', 'private_zip': '90100', 'private_city': 'Delle', 'private_country_id': cls.env.ref('base.fr').id, 'l10n_ch_residence_category': 'crossBorder-G', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True, 'l10n_ch_canton': 'EX', 'lang': 'de_DE'},
                {'registration_number': '382', 'certificate': 'doctorate', "l10n_ch_cross_border_start": date(2022, 11, 1), "l10n_ch_cross_border_commuter": True, 'l10n_ch_telework_percentage': 0, 'name': "Charles Leclerc", 'gender': 'male', 'company_id': company.id, 'country_id': cls.env.ref('base.fr').id, 'l10n_ch_sv_as_number': False, 'birthday': date(2000, 4, 28), 'marital': 'single', 'l10n_ch_marital_from': date(2000, 4, 28), 'private_street': 'Grand Rue', 'private_zip': '90100', 'private_city': 'Delle', 'private_country_id': cls.env.ref('base.fr').id, 'l10n_ch_residence_category': 'crossBorder-G', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True, 'l10n_ch_canton': 'EX', 'lang': 'de_DE'},
                {'registration_number': '383', 'certificate': 'doctorate', "l10n_ch_cross_border_start": date(2022, 11, 1), "l10n_ch_cross_border_commuter": True, 'l10n_ch_telework_percentage': 0.5, 'name': "Antoine Dumont", 'gender': 'male', 'company_id': company.id, 'country_id': cls.env.ref('base.fr').id, 'l10n_ch_sv_as_number': False, 'birthday': date(2002, 8, 20), 'marital': 'single', 'l10n_ch_marital_from': date(2002, 8, 20), 'private_street': 'Grand Rue', 'private_zip': '90100', 'private_city': 'Delle', 'private_country_id': cls.env.ref('base.fr').id, 'l10n_ch_residence_category': 'crossBorder-G', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True, 'l10n_ch_canton': 'EX', 'lang': 'de_DE'},
            ])
            mapped_employees = {}
            for index, employee in enumerate(employees, start=1):
                mapped_employees[f"employee_{employee.registration_number}"] = employee

            cdi_month = {"contract_type_id": cls.env.ref('l10n_ch_hr_payroll.l10n_ch_contract_type_indefiniteSalaryMth').id}

            info_m = cls.env['hr.job'].create({
                "name": "Informaticien"
            })
            # Generate Contracts
            contracts = cls.env['hr.contract'].with_context(tracking_disable=True).create([
                # TF 381
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdi_month, 'name': "Contract full time For Estermann Michael", 'l10n_ch_location_unit_id': cls.location_unit_2.id, 'employee_id': mapped_employees['employee_381'].id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 7250, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': cls.avs_2.id, 'l10n_ch_laa_group': cls.laa_group_A, 'laa_solution_number': '3', "l10n_ch_lpp_not_insured": True,  'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': cls.caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 30, 'l10n_ch_avs_status': 'retired'},
                # TF 382
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdi_month, 'name': "Contract full time For Estermann Michael", 'l10n_ch_location_unit_id': cls.location_unit_2.id, 'employee_id': mapped_employees['employee_382'].id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 7250, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': cls.avs_2.id, 'l10n_ch_laa_group': cls.laa_group_A, 'laa_solution_number': '3', "l10n_ch_lpp_not_insured": True,  'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': cls.caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 30, 'l10n_ch_avs_status': 'retired'},
                # TF 383
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdi_month, 'name': "Contract full time For Estermann Michael", 'l10n_ch_location_unit_id': cls.location_unit_2.id, 'employee_id': mapped_employees['employee_383'].id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 7250, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': cls.avs_2.id, 'l10n_ch_laa_group': cls.laa_group_A, 'laa_solution_number': '3', "l10n_ch_lpp_not_insured": True,  'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': cls.caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 30, 'l10n_ch_avs_status': 'retired'},
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

        with freeze_time("2022-11-26"):
            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 11, 1))

            mapped_declarations[f'yearly_retrospective_5_3_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 12/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'yearly_retrospective_5_3_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()

        with freeze_time("2022-12-26"):
            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 12, 1))

            mapped_declarations[f'yearly_retrospective_5_3_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 12/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'yearly_retrospective_5_3_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        return mapped_declarations

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with patch.object(cls.env.registry['l10n.ch.employee.yearly.values'], '_generate_certificate_uuid', lambda self: "#DOC-ID"):
            mapped_declarations = cls._l10n_ch_generate_swissdec_5_3_demo_data(cls.muster_ag_company)

        for identifier, declaration in mapped_declarations.items():
            assert isinstance(identifier, str)
            setattr(cls, identifier, declaration)
