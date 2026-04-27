# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pdb

from odoo.addons.l10n_ch_hr_payroll_elm_transmission.tests.common import TestSwissdecCommon
from odoo.tests.common import tagged, TransactionCase
from odoo.tools import file_open
from odoo import Command

from datetime import date
from freezegun import freeze_time


_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install', 'swissdec_payroll')
class TestSwissdecMinorCommon(TestSwissdecCommon):

    def _get_truth_base_path(self):
        return "l10n_ch_hr_payroll_elm_transmission_5_3/tests/data/declaration_truth_base/"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        with freeze_time("2021-11-01"):
            cls.env["res.lang"]._activate_lang("fr_FR")
            cls.env["res.lang"]._activate_lang("de_DE")
            cls.env["res.lang"]._activate_lang("it_IT")

            cls.env.user.tz = 'Europe/Zurich'

            # Generate Location Units
            LocationUnit = cls.env['l10n.ch.location.unit'].with_context(tracking_disable=True)

            cls.location_unit_1 = LocationUnit.create({
                "company_id": cls.muster_ag_company.id,
                "partner_id": cls.env['res.partner'].create({
                    'name': 'Hauptsitz',  # 'Siège principal - Lucerne',
                    'street': 'Bahnhofstrasse 1',
                    'zip': '6003',
                    'city': 'Luzern',
                    'country_id': cls.env.ref('base.ch').id,
                }).id,
                "bur_ree_number": "A92978109",
                "canton": 'LU',
                "dpi_number": '158.87.6',
                "municipality": '1061',
                "weekly_hours": 42,
                "weekly_lessons": 21,
            })

            cls.location_unit_3 = LocationUnit.create({
                "company_id": cls.muster_ag_company.id,
                "partner_id": cls.env['res.partner'].create({
                    'name': 'Verkauf',  # 'Vente - Vevey',
                    'street': 'Rue des Moulins 9',
                    'zip': '1800',
                    'city': 'Vevey',
                    'country_id': cls.env.ref('base.ch').id,
                }).id,
                "bur_ree_number": "A89058588",
                "canton": 'VD',
                "dpi_number": '23.957.55.6',
                "municipality": '5890',
                "weekly_hours": 40,
                "weekly_lessons": 20,
            })

            cls.location_unit_4 = LocationUnit.create({
                "company_id": cls.muster_ag_company.id,
                "partner_id": cls.env['res.partner'].create({
                    'name': 'Beratung',  # 'Consultation - Bellinzone',
                    'street': 'Via Canonico Ghiringhelli 19',
                    'zip': '6500',
                    'city': 'Bellinzona',
                    'country_id': cls.env.ref('base.ch').id,
                }).id,
                "bur_ree_number": "A92978114",
                "canton": 'TI',
                "dpi_number": '83189.7',
                "municipality": '5002',
                "weekly_hours": 40,
                "weekly_lessons": 20,
            })

            cls.location_unit_2 = LocationUnit.create({
                "company_id": cls.muster_ag_company.id,
                "partner_id": cls.env['res.partner'].create({
                    'name': 'Werkhof/Büro',  # 'Atelier/Bureau - Berne',
                    'street': 'Zeughausgasse 9',
                    'zip': '3011',
                    'city': 'Bern',
                    'country_id': cls.env.ref('base.ch').id,
                }).id,
                "bur_ree_number": "A89058593",
                "canton": 'BE',
                "dpi_number": '9217.8',
                "municipality": '351',
                "weekly_hours": 40,
                "weekly_lessons": 20,
            })

            # Generate Resource Calendars
            cls.st_institutions = cls.env["l10n.ch.source.tax.institution"].create([
                {
                    "name": "QST-BE",
                    "canton": "BE",
                    "dpi_number": "9217.8",
                    "company_id": cls.muster_ag_company.id
                }
            ])

            cls.salary_certificate_profile = cls.env['l10n.ch.salary.certificate.profile'].create({
                "company_id": cls.muster_ag_company.id,
                'l10n_ch_cs_other_fringe_benefits': "Avantages sur primes d'assurance",
            })

            # Generate AVS
            cls.avs_2 = cls.env['l10n.ch.social.insurance'].create({
                'name': 'AVS 2022',
                'member_number': '100-9976.9',
                'insurance_company': 'AVS 2022',
                "company_id": cls.muster_ag_company.id,
                'insurance_code': '003.000',
                'age_start': 18,
                'age_stop_male': 65,
                'age_stop_female': 64,
                'avs_line_ids': [(0, 0, {
                    'date_from': date(2021, 1, 1),
                    'employer_rate': 5.3,
                    'employee_rate': 5.3,
                })],
                'ac_line_ids': [(0, 0, {
                    'date_from': date(2021, 1, 1),
                    'employer_rate': 1.1,
                    'employee_rate': 1.1,
                    'employee_additional_rate': 0.5,
                    'employer_additional_rate': 0.5,
                })],
                'l10n_ch_avs_rente_ids': [(0, 0, {
                    'date_from': date(2021, 1, 1),
                    'amount': 1400
                })],
                'l10n_ch_avs_ac_threshold_ids': [(0, 0, {
                    'date_from': date(2021, 1, 1),
                    'amount': 148200
                })],
                'l10n_ch_avs_acc_threshold_ids': [(0, 0, {
                    'date_from': date(2021, 1, 1),
                    'amount': 370500
                })]
            })

            # Generate LAA
            laa_1_partner = cls.env['res.partner'].create({
                'name': "Backwork-Versicherungen",
                'street': "Bahnhofstrasse 7",
                'city': "Luzern",
                'zip': "6003",
                'country_id': cls.env.ref('base.ch').id,
                'company_id': cls.muster_ag_company.id,
            })

            cls.laa_1 = cls.env['l10n.ch.accident.insurance'].create({
                'name': "Backwork-Versicherungen",
                'customer_number': '12577.2',
                "company_id": cls.muster_ag_company.id,
                'contract_number': '125',
                'insurance_company': 'Backwork-Versicherungen',
                'insurance_code': 'S1000',
                'insurance_company_address_id': laa_1_partner.id,
                'laa_group_ids': [
                    (0, 0, {
                        "name": "Backwork-Versicherungen Group A",
                        "group_unit": "A",
                        "line_ids": [(0, 0, {
                            "date_from": date(2021, 1, 1),
                            "date_to": False,
                            "threshold": 148200,
                            "occupational_male_rate": 0,
                            "occupational_female_rate": 0,
                            "non_occupational_male_rate": 1.6060,
                            "non_occupational_female_rate": 1.6060,
                            "employer_occupational_part": "0",
                            "employer_non_occupational_part": "0",
                        })],
                    })
                ],
            })
            cls.laa_group_A = cls.laa_1.laa_group_ids[0].id

            # Generate CAF
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

            # Generate LPP
            lpp_partner = cls.env['res.partner'].create({
                'name': "Pensionskasse Oldsoft",
                'street': "Fellerstrasse 23",
                'city': "Bern",
                'zip': "3027",
                'country_id': cls.env.ref('base.ch').id,
                'company_id': cls.muster_ag_company.id,
            })

            cls.lpp_0 = cls.env['l10n.ch.lpp.insurance'].create({
                "name": 'Pensionskasse Oldsoft',
                "company_id": cls.muster_ag_company.id,
                "customer_number": '1099-8777.1',
                "contract_number": '4500-0',
                'insurance_company': 'Pensionskasse Oldsoft',
                'insurance_code': 'L1200',
                "insurance_company_address_id": lpp_partner.id,
                "solutions_ids": [
                    (0, 0, {
                        "name": "Production",
                        "code": "11"}),
                    (0, 0, {
                        "name": "Vente",
                        "code": "21"}),
                    (0, 0, {
                        "name": "Administration",
                        "code": "22"}),
                    (0, 0, {
                        "name": "Cadre surobligatoire",
                        "code": "K2010"})],
                "fund_number": False,
            })

            cls.avs_2.write({
                'laa_insurance_id': cls.laa_1.id,
                'laa_insurance_from': date(2021, 1, 1),
                'lpp_insurance_id': cls.lpp_0.id,
                'lpp_insurance_from': date(2021, 1, 1),
            })
