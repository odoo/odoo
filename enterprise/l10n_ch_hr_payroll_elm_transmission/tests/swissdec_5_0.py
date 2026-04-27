# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pdb

from odoo.tests.common import tagged, TransactionCase
from odoo.tools import file_open
from odoo import Command
from odoo.tests import HttpCase, tagged, TransactionCase
from datetime import datetime, date
from freezegun import freeze_time
from collections import defaultdict
from unittest.mock import patch

from .common import TestSwissdecCommon

_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install', 'swissdec_payroll')
class TestSwissdec5Common(TestSwissdecCommon):

    def _get_truth_base_path(self):
        return "l10n_ch_hr_payroll_elm_transmission/tests/data/declaration_truth_base/"

    @classmethod
    def _l10n_ch_generate_swissdec_demo_data(cls, company):
        mapped_declarations = {}
        with freeze_time("2021-11-01"):
            cls.env["res.lang"]._activate_lang("fr_FR")
            cls.env["res.lang"]._activate_lang("de_DE")
            cls.env["res.lang"]._activate_lang("it_IT")

            cls.env.user.tz = 'Europe/Zurich'

            # Generate Location Units
            LocationUnit = cls.env['l10n.ch.location.unit'].with_context(tracking_disable=True)
            location_unit_1 = LocationUnit.create({
                "company_id": company.id,
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

            location_unit_2 = LocationUnit.create({
                "company_id": company.id,
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

            location_unit_3 = LocationUnit.create({
                "company_id": company.id,
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

            location_unit_4 = LocationUnit.create({
                "company_id": company.id,
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

            # Generate Resource Calendars
            ResourceCalendar = cls.env['resource.calendar'].with_context(tracking_disable=True)
            resource_calendar_40_hours_per_week = ResourceCalendar.create([{
                'name': "Test Calendar : 40 Hours/Week",
                'company_id': company.id,
                'hours_per_day': 8.0,
                'tz': "Europe/Zurich",
                'two_weeks_calendar': False,
                'hours_per_week': 40.0,
                'full_time_required_hours': 40.0,
                'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                    'name': "Attendance",
                    'dayofweek': dayofweek,
                    'hour_from': hour_from,
                    'hour_to': hour_to,
                    'day_period': day_period,
                    'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

                }) for dayofweek, hour_from, hour_to, day_period in [
                                                     ("0", 8.0, 12.0, "morning"),
                                                     ("0", 12.0, 13.0, "lunch"),
                                                     ("0", 13.0, 17.0, "afternoon"),
                                                     ("1", 8.0, 12.0, "morning"),
                                                     ("1", 12.0, 13.0, "lunch"),
                                                     ("1", 13.0, 17.0, "afternoon"),
                                                     ("2", 8.0, 12.0, "morning"),
                                                     ("2", 12.0, 13.0, "lunch"),
                                                     ("2", 13.0, 17.0, "afternoon"),
                                                     ("3", 8.0, 12.0, "morning"),
                                                     ("3", 12.0, 13.0, "lunch"),
                                                     ("3", 13.0, 17.0, "afternoon"),
                                                     ("4", 8.0, 12.0, "morning"),
                                                     ("4", 12.0, 13.0, "lunch"),
                                                     ("4", 13.0, 17.0, "afternoon"),
                                                 ]],
            }])

            resource_calendar_42_hours_per_week = ResourceCalendar.create([{
                'name': "Test Calendar : 42 Hours/Week",
                'company_id': company.id,
                'hours_per_day': 8.0,
                'tz': "Europe/Zurich",
                'two_weeks_calendar': False,
                'hours_per_week': 42.0,
                'full_time_required_hours': 42.0,
                'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                    'name': "Attendance",
                    'dayofweek': dayofweek,
                    'hour_from': hour_from,
                    'hour_to': hour_to,
                    'day_period': day_period,
                    'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

                }) for dayofweek, hour_from, hour_to, day_period in [
                                                     ("0", 8.0, 12.0, "morning"),
                                                     ("0", 12.0, 13.0, "lunch"),
                                                     ("0", 13.0, 17.0, "afternoon"),
                                                     ("1", 8.0, 12.0, "morning"),
                                                     ("1", 12.0, 13.0, "lunch"),
                                                     ("1", 13.0, 17.0, "afternoon"),
                                                     ("2", 8.0, 12.0, "morning"),
                                                     ("2", 12.0, 13.0, "lunch"),
                                                     ("2", 13.0, 17.0, "afternoon"),
                                                     ("3", 8.0, 12.0, "morning"),
                                                     ("3", 12.0, 13.0, "lunch"),
                                                     ("3", 13.0, 17.0, "afternoon"),
                                                     ("4", 8.0, 12.0, "morning"),
                                                     ("4", 12.0, 13.0, "lunch"),
                                                     ("4", 13.0, 19.0, "afternoon"),
                                                 ]],
            }])

            resource_calendar_8_4_hours_per_week = ResourceCalendar.create([{
                'name': "Test Calendar : 8.4 Hours/Week (1/5)",
                'company_id': company.id,
                'hours_per_day': 8.4,
                'tz': "Europe/Zurich",
                'two_weeks_calendar': False,
                'hours_per_week': 8.4,
                'full_time_required_hours': 42.0,
                'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                    'name': "Attendance",
                    'dayofweek': dayofweek,
                    'hour_from': hour_from,
                    'hour_to': hour_to,
                    'day_period': day_period,
                    'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

                }) for dayofweek, hour_from, hour_to, day_period in [
                                                     ("0", 8.0, 12.0, "morning"),
                                                     ("0", 12.0, 13.0, "lunch"),
                                                     ("0", 13.0, 17.4, "afternoon"),
                                                 ]],
            }])

            resource_calendar_24_hours_per_week = ResourceCalendar.create([{
                'name': "Test Calendar : 24 Hours/Week",
                'company_id': company.id,
                'hours_per_day': 8.0,
                'tz': "Europe/Zurich",
                'two_weeks_calendar': False,
                'hours_per_week': 24,
                'full_time_required_hours': 40.0,
                'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                    'name': "Attendance",
                    'dayofweek': dayofweek,
                    'hour_from': hour_from,
                    'hour_to': hour_to,
                    'day_period': day_period,
                    'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

                }) for dayofweek, hour_from, hour_to, day_period in [
                                                     ("0", 8.0, 16.0, "morning"),
                                                     ("1", 8.0, 16.0, "morning"),
                                                     ("2", 8.0, 16.0, "morning"),
                                                 ]],
            }])

            resource_calendar_16_hours_per_week = ResourceCalendar.create([{
                'name': "Test Calendar : 16 Hours/Week",
                'company_id': company.id,
                'hours_per_day': 8.0,
                'tz': "Europe/Zurich",
                'two_weeks_calendar': False,
                'hours_per_week': 40.0,
                'full_time_required_hours': 40.0,
                'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                    'name': "Attendance",
                    'dayofweek': dayofweek,
                    'hour_from': hour_from,
                    'hour_to': hour_to,
                    'day_period': day_period,
                    'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

                }) for dayofweek, hour_from, hour_to, day_period in [
                                                     ("0", 8.0, 12.0, "morning"),
                                                     ("0", 12.0, 13.0, "lunch"),
                                                     ("0", 13.0, 17.0, "afternoon"),
                                                     ("1", 8.0, 12.0, "morning"),
                                                     ("1", 12.0, 13.0, "lunch"),
                                                     ("1", 13.0, 17.0, "afternoon"),
                                                 ]],
            }])

            resource_calendar_21_hours_per_week = ResourceCalendar.create([{
                'name': "Test Calendar : 21 Hours/Week",
                'company_id': company.id,
                'hours_per_day': 4.0,
                'tz': "Europe/Zurich",
                'two_weeks_calendar': False,
                'hours_per_week': 21.0,
                'full_time_required_hours': 42.0,
                'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                    'name': "Attendance",
                    'dayofweek': dayofweek,
                    'hour_from': hour_from,
                    'hour_to': hour_to,
                    'day_period': day_period,
                    'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

                }) for dayofweek, hour_from, hour_to, day_period in [
                                                     ("0", 8.0, 12.0, "morning"),
                                                     ("0", 12.0, 13.0, "lunch"),
                                                     ("0", 13.0, 17.0, "afternoon"),
                                                     ("1", 8.0, 12.0, "morning"),
                                                     ("1", 12.0, 13.0, "lunch"),
                                                     ("1", 13.0, 17.0, "afternoon"),
                                                     ("2", 8.0, 12.0, "morning"),
                                                     ("2", 12.0, 13.0, "lunch"),
                                                 ]],
            }])

            resource_calendar_12_6_hours_per_week = ResourceCalendar.create([{
                'name': "Test Calendar : 12.6 Hours/Week",
                'company_id': company.id,
                'hours_per_day': 4.0,
                'tz': "Europe/Zurich",
                'two_weeks_calendar': False,
                'hours_per_week': 12.6,
                'full_time_required_hours': 42.0,
                'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                    'name': "Attendance",
                    'dayofweek': dayofweek,
                    'hour_from': hour_from,
                    'hour_to': hour_to,
                    'day_period': day_period,
                    'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

                }) for dayofweek, hour_from, hour_to, day_period in [
                                                     ("0", 8.0, 12.0, "morning"),
                                                     ("0", 12.0, 13.0, "lunch"),
                                                     ("0", 13.0, 17.0, "afternoon"),
                                                     ("1", 8.0, 12.6, "morning"),
                                                 ]],
            }])

            resource_calendar_70_percent = ResourceCalendar.create([{
                'name': "Test Calendar : 42 Hours/Week",
                'company_id': company.id,
                'hours_per_day': 8.0,
                'tz': "Europe/Zurich",
                'two_weeks_calendar': False,
                'hours_per_week': 28,
                'full_time_required_hours': 40,
                'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                    'name': "Attendance",
                    'dayofweek': dayofweek,
                    'hour_from': hour_from,
                    'hour_to': hour_to,
                    'day_period': day_period,
                    'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

                }) for dayofweek, hour_from, hour_to, day_period in [
                                                     ("0", 8.0, 12.0, "morning"),
                                                     ("0", 12.0, 13.0, "lunch"),
                                                     ("0", 13.0, 16.0, "afternoon"),
                                                     ("1", 8.0, 12.0, "morning"),
                                                     ("1", 12.0, 13.0, "lunch"),
                                                     ("1", 13.0, 16.0, "afternoon"),
                                                     ("2", 8.0, 12.0, "morning"),
                                                     ("2", 12.0, 13.0, "lunch"),
                                                     ("2", 13.0, 16.0, "afternoon"),
                                                     ("3", 8.0, 12.0, "morning"),
                                                     ("3", 12.0, 13.0, "lunch"),
                                                     ("3", 13.0, 16.0, "afternoon"),
                                                 ]],
            }])

            resource_calendar_50_percent = ResourceCalendar.create([{
                'name': "Test Calendar : 20 Hours/Week",
                'company_id': company.id,
                'hours_per_day': 8.0,
                'tz': "Europe/Zurich",
                'two_weeks_calendar': False,
                'hours_per_week': 20,
                'full_time_required_hours': 40,
                'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                    'name': "Attendance",
                    'dayofweek': dayofweek,
                    'hour_from': hour_from,
                    'hour_to': hour_to,
                    'day_period': day_period,
                    'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

                }) for dayofweek, hour_from, hour_to, day_period in [
                                                     ("0", 8.0, 12.0, "morning"),
                                                     ("1", 8.0, 12.0, "morning"),
                                                     ("2", 8.0, 12.0, "morning"),
                                                     ("3", 8.0, 12.0, "morning"),
                                                     ("4", 8.0, 12.0, "morning"),
                                                 ]],
            }])

            resource_calendar_40_percent = ResourceCalendar.create([{
                'name': "Test Calendar : 16 Hours/Week",
                'company_id': company.id,
                'hours_per_day': 8.0,
                'tz': "Europe/Zurich",
                'two_weeks_calendar': False,
                'hours_per_week': 16,
                'full_time_required_hours': 40,
                'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                    'name': "Attendance",
                    'dayofweek': dayofweek,
                    'hour_from': hour_from,
                    'hour_to': hour_to,
                    'day_period': day_period,
                    'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

                }) for dayofweek, hour_from, hour_to, day_period in [
                                                     ("0", 8.0, 12.0, "morning"),
                                                     ("1", 8.0, 12.0, "morning"),
                                                     ("3", 8.0, 12.0, "morning"),
                                                     ("4", 8.0, 12.0, "morning"),
                                                 ]],
            }])

            resource_calendar_60_percent = ResourceCalendar.create([{
                'name': "Test Calendar : 24 Hours/Week",
                'company_id': company.id,
                'hours_per_day': 8.0,
                'tz': "Europe/Zurich",
                'two_weeks_calendar': False,
                'hours_per_week': 24,
                'full_time_required_hours': 40,
                'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                    'name': "Attendance",
                    'dayofweek': dayofweek,
                    'hour_from': hour_from,
                    'hour_to': hour_to,
                    'day_period': day_period,
                    'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

                }) for dayofweek, hour_from, hour_to, day_period in [
                                                     ("0", 8.0, 12.0, "morning"),
                                                     ("0", 12.0, 13.0, "lunch"),
                                                     ("0", 13.0, 17.0, "afternoon"),
                                                     ("1", 8.0, 12.0, "morning"),
                                                     ("1", 12.0, 13.0, "lunch"),
                                                     ("1", 13.0, 17.0, "afternoon"),
                                                     ("2", 8.0, 12.0, "morning"),
                                                     ("2", 12.0, 13.0, "lunch"),
                                                     ("2", 13.0, 17.0, "afternoon"),
                                                 ]],
            }])

            resource_calendar_0_hours_per_week = ResourceCalendar.create([{
                'name': "Test Calendar : 0 Hours/Week",
                'company_id': company.id,
                'hours_per_day': 0,
                'tz': "Europe/Zurich",
                'two_weeks_calendar': False,
                'hours_per_week': 0.0,
                'full_time_required_hours': 0.0,
                'attendance_ids': [(5, 0, 0)],
            }])

            st_institutions = cls.env["l10n.ch.source.tax.institution"].create([
                {
                    "name": "QST-BE",
                    "canton": "BE",
                    "dpi_number": "9217.8",
                    "company_id": company.id
                },{
                    "name": "QST-LU",
                    "canton": "LU",
                    "dpi_number": "158.87.6",
                    "company_id": company.id
                },{
                    "name": "QST-TI",
                    "canton": "TI",
                    "dpi_number": "83189.7",
                    "company_id": company.id
                },{
                    "name": "QST-VD",
                    "canton": "VD",
                    "dpi_number": "23.957.55.6",
                    "company_id": company.id
                },
            ])

            salary_certificate_profile = cls.env['l10n.ch.salary.certificate.profile'].create({
                "company_id": company.id,
                'l10n_ch_cs_other_fringe_benefits': "Avantages sur primes d'assurance",
            })

            job_1 = cls.env['hr.job'].create({'name': 'Informaticienne'})

            # Generate AVS
            avs_1 = cls.env['l10n.ch.social.insurance'].create({
                'name': 'AVS 2021',
                'member_number': '7019.2',
                "company_id": company.id,
                'insurance_company': 'AVS 2021',
                'insurance_code': '079.000',
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

            avs_2 = cls.env['l10n.ch.social.insurance'].create({
                'name': 'AVS 2022',
                'member_number': '100-9976.9',
                'insurance_company': 'AVS 2022',
                "company_id": company.id,
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
                'company_id': company.id,
            })

            laa_1 = cls.env['l10n.ch.accident.insurance'].create({
                'name': "Backwork-Versicherungen",
                'customer_number': '12577.2',
                "company_id": company.id,
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
            laa_group_A = laa_1.laa_group_ids[0].id

            # Generate LAAC
            laac_1 = cls.env['l10n.ch.additional.accident.insurance'].create({
                'name': 'Backwork-Versicherungen',
                'customer_number': '7651-873.1',
                "company_id": company.id,
                'contract_number': '4566-4',
                'insurance_company': 'Backwork-Versicherungen',
                'insurance_code': 'S1000',
                'insurance_company_address_id': laa_1_partner.id,
                'line_ids': [
                    (0, 0, {
                        'solution_name': 'Group 1, Category 0 - A0',
                        'solution_type': '1',
                        'solution_number': '0',
                        'rate_ids': [(0, 0, {
                            'date_from': date(2021, 1, 1),
                            'wage_from': 0,
                            'wage_to': 0,
                            'male_rate': 0,
                            'female_rate': 0,
                            'employer_part': '50',
                        })],
                    }),
                    (0, 0, {
                        'solution_name': 'Group 1, Category 1 - A1',
                        'solution_type': '1',
                        'solution_number': '1',
                        'rate_ids': [(0, 0, {
                            'date_from': date(2021, 1, 1),
                            'wage_from': 0,
                            'wage_to': 148200,
                            'male_rate': 0.774,
                            'female_rate': 0.774,
                            'employer_part': '0',
                        })],
                    }),
                    (0, 0, {
                        'solution_name': 'Group 1, Category 2 - A2',
                        'solution_type': '1',
                        'solution_number': '2',
                        'rate_ids': [(0, 0, {
                            'date_from': date(2021, 1, 1),
                            'wage_from': 148200,
                            'wage_to': 300000,
                            'male_rate': 0.508,
                            'female_rate': 0.508,
                            'employer_part': '0',
                        })],
                    }),
                ]
            })

            laac_10 = laac_1.line_ids[0]
            laac_11 = laac_1.line_ids[1]
            laac_12 = laac_1.line_ids[2]

            # Generate IJM
            ijm_1 = cls.env['l10n.ch.sickness.insurance'].create({
                "name": 'Backwork-Versicherungen',
                "company_id": company.id,
                "customer_number": '7651-873.1',
                "contract_number": '4567-4',
                "insurance_company": 'Backwork-Versicherungen',
                "insurance_code": 'S1000',
                "insurance_company_address_id": laa_1_partner.id,
                "line_ids": [
                    (0, 0, {
                        "solution_name": "Group 1, Category 0 - A0",
                        "solution_type": "1",
                        "solution_number": "0",
                        "rate_ids": [(0, 0, {
                            'date_from': date(2021, 1, 1),
                            "wage_from": 0,
                            "wage_to": 0,
                            "male_rate": 0,
                            "female_rate": 0,
                            "employer_part": '0',
                        })]
                    }),
                    (0, 0, {
                        "solution_name": "Group 1, Category 1 - A1",
                        "solution_type": "1",
                        "solution_number": "1",
                        "rate_ids": [(0, 0, {
                            'date_from': date(2021, 1, 1),
                            "wage_from": 0,
                            "wage_to": 120000,
                            "male_rate": 0.9660,
                            "female_rate": 1.3090,
                            "employer_part": '0',
                        })]
                    }),
                    (0, 0, {
                        "solution_name": "Group 1, Category 2 - A2",
                        "solution_type": "1",
                        "solution_number": "2",
                        "rate_ids": [(0, 0, {
                            'date_from': date(2021, 1, 1),
                            "wage_from": 88200,
                            "wage_to": 500000,
                            "male_rate": 0.1050,
                            "female_rate": 0.1230,
                            "employer_part": '0',
                        })]
                    }),
                ]
            })

            ijm_10 = ijm_1.line_ids[0]
            ijm_11 = ijm_1.line_ids[1]
            ijm_12 = ijm_1.line_ids[2]

            # Generate LPP
            lpp_partner = cls.env['res.partner'].create({
                'name': "Pensionskasse Oldsoft",
                'street': "Fellerstrasse 23",
                'city': "Bern",
                'zip': "3027",
                'country_id': cls.env.ref('base.ch').id,
                'company_id': company.id,
            })

            lpp_0 = cls.env['l10n.ch.lpp.insurance'].create({
                "name": 'Pensionskasse Oldsoft',
                "company_id": company.id,
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

            lpp_k2010 = {
                "l10n_ch_lpp_solutions": [(4, lpp_0.solutions_ids[3].id)]
            }

            lpp_11 = {
                "l10n_ch_lpp_solutions": [(4, lpp_0.solutions_ids[0].id)]
            }
            lpp_21 = {
                "l10n_ch_lpp_solutions": [(4, lpp_0.solutions_ids[1].id)]
            }
            lpp_22 = {
                "l10n_ch_lpp_solutions": [(4, lpp_0.solutions_ids[2].id)]
            }


            # Generate CAF
            caf_lu_1 = cls.env['l10n.ch.compensation.fund'].create({
                "name": 'Spida',
                "company_id": company.id,
                "member_number": '5676.3',
                "member_subnumber": '',
                "insurance_company": 'Spida',
                "insurance_code": '079.000',
                "caf_line_ids": [(0, 0, {
                    'date_from': date(2021, 1, 1),
                    'date_to': False,
                    'employee_rate': 0,
                    'company_rate': 0,
                })],
            })

            caf_lu_2 = cls.env['l10n.ch.compensation.fund'].create({
                "name": 'Familienausgleichskassen Kanton Luzern',
                "company_id": company.id,
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



            caf_be_1 = cls.env['l10n.ch.compensation.fund'].create({
                "name": 'Spida',
                "company_id": company.id,
                "member_number": '8734.3',
                "member_subnumber": '',
                "insurance_company": 'Spida',
                "insurance_code": '079.000',
                "caf_line_ids": [(0, 0, {
                    'date_from': date(2021, 1, 1),
                    'date_to': False,
                    'employee_rate': 0,
                    'company_rate': 0,
                })],
            })


            caf_be_2 = cls.env['l10n.ch.compensation.fund'].create({
                "name": 'Familienausgleichskasse Kanton Bern',
                "company_id": company.id,
                "member_number": '100-2136.90',
                "member_subnumber": '',
                "insurance_company": 'Familienausgleichskassen Kanton Luzern',
                "insurance_code": '002.000',
                "caf_line_ids": [(0, 0, {
                    'date_from': date(2021, 1, 1),
                    'date_to': False,
                    'employee_rate': 0,
                    'company_rate': 0,
                })],
            })


            caf_vd_1 = cls.env['l10n.ch.compensation.fund'].create({
                "name": 'Spida',
                "company_id": company.id,
                "member_number": '4296.8',
                "member_subnumber": '',
                "insurance_company": 'Spida',
                "insurance_code": '079.000',
                "caf_line_ids": [(0, 0, {
                    'date_from': date(2021, 1, 1),
                    'date_to': False,
                    'employee_rate': 0,
                    'company_rate': 0,
                })],
            })

            caf_vd_2 = cls.env['l10n.ch.compensation.fund'].create({
                "name": 'Caisse cantonale vaudoise de compensation',
                "company_id": company.id,
                "member_number": '100-7766.80',
                "member_subnumber": '',
                "insurance_company": 'Caisse cantonale vaudoise de compensation',
                "insurance_code": '022.000',
                "caf_line_ids": [(0, 0, {
                    'date_from': date(2021, 1, 1),
                    'date_to': False,
                    'employee_rate': 0,
                    'company_rate': 0,
                })],
            })

            caf_ti_2 = cls.env['l10n.ch.compensation.fund'].create({
                "name": 'Istituto delle assicurazioni sociali',
                "company_id": company.id,
                "member_number": '100-5467.80',
                "member_subnumber": '',
                "insurance_company": 'Istituto delle assicurazioni sociali',
                "insurance_code": '021.000',
                "caf_line_ids": [(0, 0, {
                    'date_from': date(2021, 1, 1),
                    'date_to': False,
                    'employee_rate': 0,
                    'company_rate': 0,
                })],
            })


            avs_1.write({
                'laa_insurance_id': laa_1.id,
                'laa_insurance_from': date(2021, 1, 1),
                'lpp_insurance_id': lpp_0.id,
                'lpp_insurance_from': date(2021, 1, 1),
            })

            avs_2.write({
                'laa_insurance_id': laa_1.id,
                'laa_insurance_from': date(2021, 1, 1),
                'lpp_insurance_id': lpp_0.id,
                'lpp_insurance_from': date(2021, 1, 1),
            })

            c_r = {
                "l10n_ch_cs_expense_policy": "approved",
                "l10n_ch_cs_expense_policy_approved_canton": "LU",
                "l10n_ch_cs_expense_policy_approved_date": date(2021, 1, 1),
            }
            m_a = {
                "l10n_ch_cs_employee_parti_fair_market_value": True,
                "l10n_ch_cs_employee_parti_fair_market_value_canton": "LU",
                "l10n_ch_cs_employee_parti_fair_market_value_date": date(2021, 7, 1),
            }
            f_b = {
                'l10n_ch_cs_other_fringe_benefits': "Avantages sur primes d'assurance",
            }
            e_r = {
                "l10n_ch_cs_expense_expatriate_ruling_approved": True,
                "l10n_ch_cs_expense_expatriate_ruling_approved_canton": "LU",
                "l10n_ch_cs_expense_expatriate_ruling_approved_date": date(2020, 3, 1)
            }

            tf37_additional_particular = {'l10n_ch_children':  [(0, 0, {
                'name': 'Eliane',
                'last_name': 'Rossel',
                'deduction_start': date(2012, 7, 1),
                'deduction_end': date(2030, 6, 30),
                'birthdate': date(2012, 6, 18),
            })]}

            tf18_additional_particular = {
                'l10n_ch_spouse_last_name': "Blanc",
                'l10n_ch_spouse_first_name': "Anita",
                'l10n_ch_spouse_birthday': date(1991, 6, 29),
                'l10n_ch_spouse_residence_canton': 'BS',
                'l10n_ch_spouse_street': 'Bäumlihofstrasse 385',
                'l10n_ch_spouse_zip': '4125',
                'l10n_ch_spouse_city': "Riehen",
                'l10n_ch_spouse_country_id': cls.env.ref('base.ch').id,
            }

            tf24_additional_particular = {
                'l10n_ch_spouse_sv_as_number': "756.6549.9078.26",
                'l10n_ch_spouse_last_name': "Utzinger",
                'l10n_ch_spouse_first_name': "Julie",
                'l10n_ch_spouse_birthday': date(1980, 7, 7),
                'l10n_ch_spouse_residence_canton': 'TI',
                'l10n_ch_spouse_street': 'Via Lugano 40',
                'l10n_ch_spouse_zip': '6500',
                'l10n_ch_spouse_city': "Bellinzona",
                'l10n_ch_spouse_country_id': cls.env.ref('base.ch').id,
            }

            tf36_additional_particular = {
                'l10n_ch_spouse_last_name': "Maldini",
                'l10n_ch_spouse_first_name': "Sandra",
                'l10n_ch_spouse_birthday': date(1994, 9, 27),
                'l10n_ch_spouse_residence_canton': 'BE',
                'l10n_ch_spouse_street': 'Blockweg 2',
                'l10n_ch_spouse_zip': '3007',
                'l10n_ch_spouse_city': "Bern",
                'l10n_ch_spouse_country_id': cls.env.ref('base.ch').id,}

            tf40_additional_particular = {'l10n_ch_children':  [(0, 0, {
                'name': 'Lisa',
                'last_name': 'Farine',
                'birthdate': date(2020, 5, 4),
                'deduction_start': date(2020, 6, 1),
                'deduction_end': date(2038, 5, 31),
            })]}
            tf33_additional_particular = {
                'l10n_ch_spouse_sv_as_number': "756.6328.7099.17",
                'l10n_ch_spouse_last_name': "Châtelain",
                'l10n_ch_spouse_first_name': "Rita",
                'l10n_ch_spouse_birthday': date(1976, 12, 15),
                'l10n_ch_spouse_residence_canton': 'BE',
                'l10n_ch_spouse_street': 'Wiesenstrasse 14',
                'l10n_ch_spouse_zip': '3098',
                'l10n_ch_spouse_city': "Köniz",
                'l10n_ch_spouse_country_id': cls.env.ref('base.ch').id,
            }

            tf34_additional_particular = {
                'l10n_ch_spouse_last_name': "Rinaldi",
                'l10n_ch_spouse_first_name': "Rita",
                'l10n_ch_spouse_birthday': date(1971, 12, 15),
                'l10n_ch_spouse_residence_canton': 'EX',
                'l10n_ch_spouse_street': 'Piazza Marconi 7',
                'l10n_ch_spouse_zip': '24122',
                'l10n_ch_spouse_city': "Bergamo",
                'l10n_ch_spouse_country_id': cls.env.ref('base.it').id,
            }

            tf23_additional_particular = {
                'l10n_ch_spouse_sv_as_number': "756.1928.1347.70",
                'l10n_ch_spouse_last_name': "Koller",
                'l10n_ch_spouse_first_name': "Anita",
                'l10n_ch_spouse_birthday': date(1991, 6, 29),
                'l10n_ch_spouse_residence_canton': 'TI',
                'l10n_ch_spouse_street': 'Viale Stefano Franscini 17',
                'l10n_ch_spouse_zip': '6500',
                'l10n_ch_spouse_city': "Bellinzona",
                'l10n_ch_spouse_country_id': cls.env.ref('base.ch').id,
            }

            tf31_additional_particular = {
                'l10n_ch_spouse_last_name': "Bolletto",
                'l10n_ch_spouse_first_name': "Luigi",
                'l10n_ch_spouse_birthday': date(1990, 3, 15),
                'l10n_ch_spouse_residence_canton': 'VD',
                'l10n_ch_spouse_street': 'Route de chavannes 11',
                'l10n_ch_spouse_zip': '1007',
                'l10n_ch_spouse_city': "Lausanne",
                'l10n_ch_spouse_country_id': cls.env.ref('base.ch').id,
            }

            tf22_additional_particular = {
                'l10n_ch_spouse_last_name': "Bucher",
                'l10n_ch_spouse_first_name': "Luigi",
                'l10n_ch_spouse_birthday': date(1995, 3, 15),
                'l10n_ch_spouse_residence_canton': 'TI',
                'l10n_ch_spouse_street': 'Via Serafino Balestra 9',
                'l10n_ch_spouse_zip': '6900',
                'l10n_ch_spouse_city': "Lugano",
                'l10n_ch_spouse_country_id': cls.env.ref('base.ch').id,
            }

            tf35_additional_particular = {
                'l10n_ch_spouse_sv_as_number': "756.3454.9922.51",
                'l10n_ch_spouse_last_name': "Roos",
                'l10n_ch_spouse_first_name': "Melanie",
                'l10n_ch_spouse_birthday': date(1969, 6, 12),
                'l10n_ch_spouse_residence_canton': 'TI',
                'l10n_ch_spouse_street': 'Via Ospedale 10',
                'l10n_ch_spouse_zip': '6500',
                'l10n_ch_spouse_city': "Bellinzona",
                'l10n_ch_spouse_country_id': cls.env.ref('base.ch').id,
            }




            # Generate Employees
            employees = cls.env['hr.employee'].with_context(tracking_disable=True).create([
                {'registration_number': '1', 'certificate': 'higherVocEducation', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, **c_r})], 'name': "Monica Herz", 'gender': 'female', 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'country_id': cls.env.ref('base.ch').id, 'l10n_ch_sv_as_number': False, 'birthday': date(1976, 6, 30), 'marital': 'married', 'l10n_ch_marital_from': date(2001, 5, 25), 'private_street': 'Bahnhofstrasse 1', 'private_zip': '6020', 'private_city': 'Emmenbrücke', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 1024, 'l10n_ch_residence_category': False, 'l10n_ch_canton': 'LU', 'lang': 'fr_FR'},
                {'registration_number': '2', 'certificate': 'universityBachelor', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_relocation_costs": 4251})], 'name': "Maria Paganini", 'gender': 'female', 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'country_id': cls.env.ref('base.it').id, 'l10n_ch_sv_as_number': '756.3598.1127.37', 'birthday': date(1958, 9, 30), 'marital': 'married', 'l10n_ch_marital_from': date(1992, 3, 13), 'private_street': 'Zentralstrasse 17', 'private_zip': '6030', 'private_city': 'Ebikon', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 1054, 'l10n_ch_residence_category': 'settled-C', 'l10n_ch_canton': 'LU', 'lang': 'fr_FR'},
                {'registration_number': '3', 'certificate': 'vocEducationCompl', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id})], 'name': "Pia Lusser", 'gender': 'female', 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'country_id': cls.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.6417.0995.23', 'birthday': date(1958, 2, 5), 'marital': 'married', 'l10n_ch_marital_from': date(1979, 8, 14), 'private_street': 'Buochserstrasse 4', 'private_zip': '6370', 'private_city': 'Stans', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 1509, 'l10n_ch_residence_category': False, 'l10n_ch_canton': 'NW', 'lang': 'fr_FR'},
                {'registration_number': '4', 'certificate': 'universityMaster', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, 'l10n_ch_cs_car_policy': 'empPart'})], 'name': "Markus Fankhauser", 'gender': 'male', 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'country_id': cls.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.6353.2927.43', 'birthday': date(1966, 10, 19), 'marital': 'single', 'l10n_ch_marital_from': date(1966, 10, 19), 'private_street': 'Schmiedegasse 16', 'private_zip': '3150', 'private_city': 'Schwarzenburg', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 855, 'l10n_ch_residence_category': False, 'l10n_ch_canton': 'BE', 'lang': 'fr_FR'},
                {'registration_number': '5', 'certificate': 'mandatorySchoolOnly', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, 'l10n_ch_cs_expense_policy': False})], 'name': "Johann Moser", 'gender': 'male', 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'country_id': cls.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.3574.4165.90', 'birthday': date(1957, 4, 15), 'marital': 'married', 'l10n_ch_marital_from': date(1981, 4, 23), 'private_street': 'Kramgasse 11', 'private_zip': '3011', 'private_city': 'Bern', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 351, 'l10n_ch_residence_category': False, 'l10n_ch_canton': 'BE', 'lang': 'fr_FR'},
                {'registration_number': '6', 'certificate': 'universityEntranceCertificate', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, **c_r, 'certificate_template_id': salary_certificate_profile.id})], 'name': "Anita Zahnd", 'gender': 'female', 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'country_id': cls.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.6564.5197.21', 'birthday': date(1976, 5, 23), 'marital': 'single', 'l10n_ch_marital_from': date(1976, 5, 23), 'private_street': 'Lindenweg 10', 'private_zip': '3072', 'private_city': 'Ostermundigen', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 363, 'l10n_ch_residence_category': False, 'l10n_ch_canton': 'BE', 'lang': 'fr_FR'},
                {'registration_number': '7', 'certificate': 'teacherCertificate', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id})], 'name': "Heidi Burri", 'gender': 'female', 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'country_id': cls.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.1886.7922.72', 'birthday': date(1957, 12, 16), 'marital': 'married', 'l10n_ch_marital_from': date(1992, 12, 14), 'private_street': 'Laupenstrasse 45', 'private_zip': '3008', 'private_city': 'Bern', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 351, 'l10n_ch_residence_category': False, 'l10n_ch_canton': 'BE', 'lang': 'fr_FR'},
                {'registration_number': '8', 'certificate': 'enterpriseEducation', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, 'l10n_ch_cs_expense_policy': False})], 'name': "René Lamon", 'gender': 'male', 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'country_id': cls.env.ref('base.fr').id, 'l10n_ch_sv_as_number': '756.3552.6511.80', 'birthday': date(1984, 3, 16), 'marital': 'unknown', 'l10n_ch_marital_from': date(1984, 3, 16), 'private_street': 'Effingerstrasse 87', 'private_zip': '3008', 'private_city': 'Bern', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 351, 'l10n_ch_residence_category': 'settled-C', 'l10n_ch_canton': 'BE', 'l10n_ch_tax_scale': 'A', 'lang': 'fr_FR'},
                {'registration_number': '9', 'certificate': 'doctorate', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, **c_r, 'certificate_template_id': salary_certificate_profile.id, 'l10n_ch_cs_free_meals': True})], 'name': "Michael Estermann", 'gender': 'male', 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'country_id': cls.env.ref('base.de').id, 'l10n_ch_sv_as_number': '756.1931.9954.43', 'birthday': date(1956, 1, 1), 'marital': 'married', 'l10n_ch_marital_from': date(1987, 4, 12), 'private_street': 'Seestrasse 3', 'private_zip': '6353', 'private_city': 'Weggis', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 1069, 'l10n_ch_residence_category': 'settled-C', 'l10n_ch_canton': 'LU', 'lang': 'fr_FR'},
                {'registration_number': '10', 'certificate': 'higherVocEducationBachelor', "l10n_ch_salary_certificate_profiles": [(0, 0, {**m_a, "l10n_ch_child_allowance_indirect": True, 'l10n_ch_cs_car_policy': 'toClarify', 'l10n_ch_cs_free_meals': True, 'l10n_ch_cs_employee_participation_taxable_income': True, 'l10n_ch_cs_employee_participation_taxable_income_locked': True, 'l10n_ch_cs_employee_participation_taxable_income_unlisted': True, "l10n_ch_cs_employee_participation_taxable_income_reversional": True, "l10n_ch_cs_other_fringe_benefits": "Avantages sur primes d'assurance, Prix fortement réduit sur l'achat d'une voiture de tourisme", **c_r, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_cs_free_transport": True})], 'name': "Heinz Ganz", 'gender': 'male', 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'country_id': cls.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.6362.5066.57', 'birthday': date(1996, 2, 28), 'marital': 'married', 'l10n_ch_marital_from': date(2020, 7, 1), 'private_street': 'Neuhofstrasse 47', 'private_zip': '6020', 'private_city': 'Emmenbrücke', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 1024, 'l10n_ch_canton': 'LU', 'l10n_ch_tax_scale': 'A', 'lang': 'fr_FR'},
                {'registration_number': '11', 'certificate': 'higherVocEducationMaster', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_cs_free_transport": True, **c_r, 'l10n_ch_cs_free_meals': True, 'l10n_ch_cs_other_fringe_benefits': "Avantages sur primes d'assurance", "l10n_ch_cs_car_policy": "empPart", "l10n_ch_relocation_costs": 2000})], 'name': "Peter Bosshard", 'gender': 'male', 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': company.id, 'country_id': cls.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.3426.3448.04', 'birthday': date(1978, 4, 11), 'marital': 'married', 'l10n_ch_marital_from': date(1997, 9, 5), 'private_street': 'Brünigstrasse 20', 'private_zip': '6072', 'private_city': 'Sachseln', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 1406, 'l10n_ch_residence_category': False, 'l10n_ch_canton': 'OW', 'l10n_ch_tax_scale': 'A', 'lang': 'fr_FR'},
                {'registration_number': '12', 'certificate': 'higherEducationBachelor', "l10n_ch_salary_certificate_profiles": [(0, 0, {**m_a, **e_r, "l10n_ch_cs_other_fringe_benefits": "Avantages sur primes d'assurance, Prix fortement réduit sur l'achat d'une voiture de tourisme", 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_cs_free_transport": True})], 'name': 'Renato Casanova', 'l10n_ch_sv_as_number': "756.3431.9824.73", 'gender': 'male', 'country_id': cls.env.ref('base.ch').id, 'birthday': date(1995, 1, 1), 'marital': 'partnership_dissolved_by_declaration_of_lost', 'l10n_ch_marital_from': date(2020, 6, 15), 'private_street': 'Bahnhofstrasse 6', 'private_zip': '6048', 'private_city': 'Horw', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': '1058', 'l10n_ch_canton': 'LU', 'l10n_ch_residence_category': False, 'lang': 'fr_FR', 'company_id': company.id},
                {'registration_number': '13', 'certificate': 'mandatorySchoolOnly', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id})], 'name': "Renato Combertaldi", 'gender': 'male', 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': company.id, 'country_id': cls.env.ref('base.it').id, 'l10n_ch_sv_as_number': '756.1925.1163.66', 'birthday': date(2005, 1, 1), 'marital': 'single', 'l10n_ch_marital_from': date(2005, 1, 1), 'private_street': 'Museggstrasse 4', 'private_zip': '6004', 'private_city': 'Luzern', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 1061, 'l10n_ch_residence_category': 'settled-C', 'l10n_ch_canton': 'LU', 'l10n_ch_tax_scale': 'A', 'lang': 'fr_FR'},
                {'registration_number': '14', 'company_id': company.id, 'certificate': 'enterpriseEducation', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_cs_free_transport": True, "l10n_ch_source_tax_settlement_letter": True, "l10n_ch_cs_expense_policy": "rz52", 'l10n_ch_cs_other_fringe_benefits': "Avantages sur primes d'assurance"})], 'l10n_ch_religious_denomination': 'romanCatholic', 'name': 'Anna Egli', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_sv_as_number': "756.1927.3247.52", 'gender': 'female', 'country_id': cls.env.ref('base.de').id, 'birthday': date(1977, 7, 13), 'marital': 'separated', 'l10n_ch_marital_from': date(2017, 4, 28), 'private_street': 'Seestrasse 5', 'private_zip': '6353', 'private_city': 'Weggis', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': '1069', 'l10n_ch_canton': 'LU', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
                {'registration_number': '15', 'certificate': 'teacherCertificate', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, **e_r, 'certificate_template_id': salary_certificate_profile.id})], 'name': "Lorenz Degelo", 'gender': 'male', 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': company.id, 'country_id': cls.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.3434.5392.78', 'birthday': date(1986, 2, 28), 'marital': 'registered_partnership', 'l10n_ch_marital_from': date(2011, 8, 17), 'private_street': 'Lopperstrasse 8', 'private_zip': '6010', 'private_city': 'Kriens', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 1059, 'l10n_ch_residence_category': False, 'l10n_ch_canton': 'LU', 'l10n_ch_tax_scale': 'A', 'lang': 'fr_FR'},
                {'registration_number': '16', 'company_id': company.id, 'certificate': 'universityEntranceCertificate', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, **c_r, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_relocation_costs": 2000})], 'name': 'Anna Aebi', 'l10n_ch_sv_as_number': "756.3047.5009.62", 'gender': 'female', 'country_id': cls.env.ref('base.ch').id, 'birthday': date(1957, 12, 31), 'marital': 'single', 'l10n_ch_marital_from': date(1957, 12, 31), 'private_street': 'Bundesstrasse 5', 'private_zip': '6003', 'private_city': 'Luzern', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': '1061', 'l10n_ch_canton': 'LU', 'l10n_ch_residence_category': False, 'lang': 'fr_FR'},
                {'registration_number': '17', 'l10n_ch_religious_denomination': 'romanCatholic', 'certificate': 'universityEntranceCertificate', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'name': "Fritz Binggeli", 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'gender': 'male', 'resource_calendar_id': resource_calendar_70_percent.id, 'company_id': company.id, 'country_id': cls.env.ref('base.it').id, 'l10n_ch_sv_as_number': '756.3425.9630.75', 'birthday': date(1972, 4, 11), 'marital': 'single', 'l10n_ch_marital_from': date(1972, 4, 11), 'private_street': 'Via Monte Ceneri 17', 'private_zip': '6512', 'private_city': 'Giubiasco', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 5002, 'l10n_ch_residence_category': "annual-B", 'l10n_ch_canton': 'TI', 'l10n_ch_tax_scale': 'A', 'lang': 'fr_FR', 'is_non_resident': True, 'l10n_ch_has_withholding_tax': True, 'l10n_ch_other_employment': True, 'l10n_ch_total_activity_type': 'percentage', 'l10n_ch_other_activity_percentage': 30},
                {'registration_number': '18', 'company_id': company.id, 'certificate': 'enterpriseEducation', **tf18_additional_particular, "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'name': 'Pierre Blanc', 'l10n_ch_religious_denomination': 'romanCatholic', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_sv_as_number': "756.3729.5603.90", 'gender': 'male', 'country_id': cls.env.ref('base.fr').id, 'birthday': date(1982, 12, 11), 'marital': 'married', 'l10n_ch_marital_from': date(2021, 11, 1), 'private_street': 'Freiburgstrasse 312', 'private_zip': '3018', 'private_city': 'Bern', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': '351', 'l10n_ch_canton': 'BE', 'l10n_ch_residence_category': 'ProvisionallyAdmittedForeigners-F', 'lang': 'fr_FR', 'l10n_ch_tax_scale': 'B', 'l10n_ch_has_withholding_tax': True, 'l10n_ch_other_employment': True, 'l10n_ch_total_activity_type': 'percentage', 'l10n_ch_other_activity_percentage': 60},
                {'registration_number': '19', 'certificate': 'vocEducationCompl', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'l10n_ch_religious_denomination': 'reformedEvangelical', 'name': "Melanie Andrey", 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'gender': 'female', 'resource_calendar_id': resource_calendar_50_percent.id, 'company_id': company.id, 'country_id': cls.env.ref('base.it').id, 'l10n_ch_sv_as_number': '756.1848.4786.64', 'birthday': date(1967, 5, 16), 'marital': 'single', 'l10n_ch_marital_from': date(1967, 5, 16), 'private_street': 'Via Lugano 4', 'private_zip': '6500', 'private_city': 'Bellinzona', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 5002, 'l10n_ch_residence_category': "annual-B", 'l10n_ch_canton': 'TI', 'l10n_ch_tax_scale': 'A', 'lang': 'fr_FR', 'is_non_resident': True, 'l10n_ch_has_withholding_tax': True, 'l10n_ch_other_employment': True, 'l10n_ch_total_activity_type': 'percentage', 'l10n_ch_other_activity_percentage': 40},
                {'registration_number': '20', 'company_id': company.id, 'certificate': 'universityEntranceCertificate', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'l10n_ch_religious_denomination': 'romanCatholic', 'name': 'Lukas Arnold', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_sv_as_number': "756.1859.2584.53", 'gender': 'male', 'country_id': cls.env.ref('base.it').id, 'birthday': date(1993, 6, 17), 'marital': 'single', 'l10n_ch_marital_from': date(1993, 6, 17), 'private_street': 'Brünnenstrasse 66', 'private_zip': '3018', 'private_city': 'Bern', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': '351', 'l10n_ch_canton': 'BE', 'l10n_ch_residence_category': 'NotificationProcedureForShorttermWork90Days', 'lang': 'fr_FR', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True, 'l10n_ch_other_employment': True, 'l10n_ch_total_activity_type': 'percentage', 'l10n_ch_other_activity_percentage': 50},
                {'registration_number': '21', 'certificate': 'enterpriseEducation', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'name': "Christian Meier", 'l10n_ch_religious_denomination': 'romanCatholic', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'gender': 'male', 'resource_calendar_id': resource_calendar_40_percent.id, 'company_id': company.id, 'country_id': cls.env.ref('base.it').id, 'l10n_ch_sv_as_number': '', 'birthday': date(1972, 1, 1), 'marital': 'single', 'l10n_ch_marital_from': date(1972, 1, 1), 'private_street': 'Via Campagna 5', 'private_zip': '6512', 'private_city': 'Giubiasco', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 5002, 'l10n_ch_residence_category': "NotificationProcedureForShorttermWork120Days", 'l10n_ch_canton': 'TI', 'l10n_ch_tax_scale': 'A', 'lang': 'fr_FR', 'is_non_resident': True, 'l10n_ch_has_withholding_tax': True, 'l10n_ch_other_employment': True, 'l10n_ch_total_activity_type': 'percentage', 'l10n_ch_other_activity_percentage': 50},
                {'registration_number': '22', 'company_id': company.id, 'certificate': 'vocEducationCompl', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'l10n_ch_religious_denomination': 'romanCatholic', 'name': 'Elisabeth Bucher', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_sv_as_number': "756.6319.2565.36", 'gender': 'female', 'country_id': cls.env.ref('base.it').id, 'birthday': date(1997, 6, 6), 'marital': 'single', 'l10n_ch_marital_from': date(1997, 6, 6), 'private_street': 'Via Serafino Balestra 9', 'private_zip': '6900', 'private_city': 'Lugano', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': '5192', 'l10n_ch_canton': 'TI', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'l10n_ch_has_withholding_tax': True, 'l10n_ch_tax_scale': 'A'},
                {'registration_number': '23', 'certificate': 'universityBachelor', **tf23_additional_particular, "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'l10n_ch_religious_denomination': 'romanCatholic', 'name': "Ludwig Koller", 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'gender': 'male', 'resource_calendar_id': resource_calendar_40_percent.id, 'company_id': company.id, 'country_id': cls.env.ref('base.de').id, 'l10n_ch_sv_as_number': '756.3539.3643.93', 'birthday': date(1989, 1, 10), 'marital': 'single', 'l10n_ch_marital_from': date(1989, 1, 10), 'private_street': 'Viale Stefano Franscini 17', 'private_zip': '6500', 'private_city': 'Bellinzona', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 5002, 'l10n_ch_residence_category': "annual-B", 'l10n_ch_canton': 'TI', 'l10n_ch_tax_scale': 'A', 'lang': 'fr_FR', 'is_non_resident': True, 'l10n_ch_has_withholding_tax': True},
                {'registration_number': '24', 'company_id': company.id, 'certificate': 'higherEducationBachelor', **tf24_additional_particular, "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'name': 'Jan Utzinger', 'l10n_ch_religious_denomination': 'reformedEvangelical', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_sv_as_number': "756.6555.6617.29", 'gender': 'male', 'country_id': cls.env.ref('base.de').id, 'birthday': date(1980, 6, 23), 'marital': 'married', 'l10n_ch_marital_from': date(2021, 11, 25), 'private_street': 'Via Lugano 40', 'private_zip': '6500', 'private_city': 'Bellinzona', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': '5002', 'l10n_ch_canton': 'TI', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'l10n_ch_has_withholding_tax': True, 'l10n_ch_tax_scale': 'B'},
                {'registration_number': '25', 'company_id': company.id, 'certificate': 'vocEducationCompl', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], "l10n_ch_religious_denomination": "christianCatholic", 'name': 'Nadine Lehmann', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_residence_type': 'Daily', 'l10n_ch_sv_as_number': "756.3558.3266.93", 'gender': 'female', 'country_id': cls.env.ref('base.de').id, 'birthday': date(1997, 7, 28), 'marital': 'single', 'l10n_ch_marital_from': date(1997, 7, 28), 'private_street': 'Via Pisanello 2', 'private_zip': '20146', 'private_city': 'Milano', 'private_country_id': cls.env.ref('base.it').id, 'l10n_ch_municipality': False, 'l10n_ch_canton': 'EX', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'is_non_resident': True, 'l10n_ch_has_withholding_tax': True, 'l10n_ch_tax_scale': 'A'},
                {'registration_number': '26', 'company_id': company.id, 'certificate': 'universityEntranceCertificate', "l10n_ch_foreign_tax_id": "JNZMCL72A01Z112Y", "place_of_birth": "DE", "l10n_ch_cross_border_start": date(2023, 7, 18), "l10n_ch_cross_border_commuter": True, "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'l10n_ch_religious_denomination': 'romanCatholic', 'name': 'Marcel Jenzer', 'l10n_ch_residence_type': 'Daily', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_sv_as_number': "756.6408.6518.22", 'gender': 'male', 'country_id': cls.env.ref('base.de').id, 'birthday': date(1972, 1, 1), 'marital': 'single', 'l10n_ch_marital_from': date(1972, 1, 1), 'private_street': 'viale misurata 56', 'private_zip': '20146', 'private_city': 'Milano', 'private_country_id': cls.env.ref('base.it').id, 'l10n_ch_municipality': False, 'l10n_ch_canton': 'EX', 'l10n_ch_residence_category': 'othersNotSwiss', 'lang': 'fr_FR', 'l10n_ch_tax_scale': 'R', 'l10n_ch_has_withholding_tax': True},
                {'registration_number': '27', 'company_id': company.id, 'certificate': 'enterpriseEducation', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'name': 'Eva Rast', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_residence_type': 'Daily', 'l10n_ch_sv_as_number': "756.3627.5282.70", 'gender': 'female', 'country_id': cls.env.ref('base.de').id, 'birthday': date(1988, 11, 1), 'marital': 'single', 'l10n_ch_marital_from': date(1988, 11, 1), 'private_street': 'Opelstrasse 1', 'private_zip': '78467', 'private_city': 'Konstanz', 'private_country_id': cls.env.ref('base.de').id, 'l10n_ch_municipality': False, 'l10n_ch_canton': 'EX', 'l10n_ch_residence_category': 'crossBorder-G', 'lang': 'fr_FR', 'is_non_resident': True, 'l10n_ch_has_withholding_tax': True, 'l10n_ch_tax_scale': 'L'},
                {'registration_number': '28', 'company_id': company.id, 'certificate': 'higherVocEducationMaster', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'l10n_ch_religious_denomination': 'romanCatholic', 'name': 'Esther Arbenz', 'l10n_ch_residence_type': 'Weekly', 'l10n_ch_weekly_residence_canton': 'BE', 'l10n_ch_weekly_residence_municipality': '351', "l10n_ch_weekly_residence_address_street": "Laupenstrasse 10", "l10n_ch_weekly_residence_address_city": "Bern", "l10n_ch_weekly_residence_address_zip": "3008", 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_sv_as_number': "756.1853.0576.49", 'gender': 'female', 'country_id': cls.env.ref('base.de').id, 'birthday': date(1974, 4, 13), 'marital': 'single', 'l10n_ch_marital_from': date(1974, 4, 13), 'private_street': 'via Vedano 1', 'private_zip': '20900', 'private_city': 'Monza', 'private_country_id': cls.env.ref('base.it').id, 'l10n_ch_municipality': False, 'l10n_ch_canton': 'EX', 'l10n_ch_residence_category': 'crossBorder-G', 'lang': 'fr_FR', 'l10n_ch_has_withholding_tax': True, 'l10n_ch_tax_scale': 'A', 'l10n_ch_other_employment': True, 'l10n_ch_total_activity_type': 'percentage', 'l10n_ch_other_activity_percentage': 20},
                {'registration_number': '29', 'company_id': company.id, 'certificate': 'enterpriseEducation', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'l10n_ch_religious_denomination': 'romanCatholic', 'name': 'Moreno Forster', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_residence_type': 'Daily', 'l10n_ch_sv_as_number': "756.6361.0022.59", 'gender': 'male', 'country_id': cls.env.ref('base.it').id, 'birthday': date(1974, 7, 13), 'marital': 'single', 'l10n_ch_marital_from': date(1974, 7, 13), 'private_street': 'Via Como 12', 'private_zip': '21100', 'private_city': 'Varese', 'private_country_id': cls.env.ref('base.it').id, 'l10n_ch_municipality': False, 'l10n_ch_canton': 'EX', 'l10n_ch_residence_category': 'crossBorder-G', 'lang': 'fr_FR', 'l10n_ch_tax_scale': 'R', 'l10n_ch_has_withholding_tax': True, 'l10n_ch_other_employment': True, 'l10n_ch_total_activity_type': 'percentage', 'l10n_ch_other_activity_percentage': 20},
                {'registration_number': '30', 'company_id': company.id, 'certificate': 'universityEntranceCertificate', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'name': 'Heinrich Müller', 'l10n_ch_religious_denomination': 'romanCatholic', 'l10n_ch_tax_scale_type': 'CategoryPredefined', 'l10n_ch_pre_defined_tax_scale': 'MEN', 'l10n_ch_residence_type': 'Daily', 'l10n_ch_sv_as_number': False, 'gender': 'male', 'country_id': cls.env.ref('base.de').id, 'birthday': date(1974, 7, 13), 'marital': 'single', 'l10n_ch_marital_from': date(1974, 7, 13), 'private_street': 'Lilienstrasse 22', 'private_zip': '81669', 'private_city': 'München', 'private_country_id': cls.env.ref('base.de').id, 'l10n_ch_municipality': False, 'l10n_ch_canton': 'EX', 'l10n_ch_residence_category': 'othersNotSwiss', 'lang': 'fr_FR', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
                {'registration_number': '31', 'company_id': company.id, 'certificate': 'vocEducationCompl', **tf31_additional_particular, "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'l10n_ch_religious_denomination': 'romanCatholic', 'name': 'Franca Bolletto', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_sv_as_number': "756.6508.6893.67", 'gender': 'female', 'country_id': cls.env.ref('base.it').id, 'birthday': date(1992, 6, 6), 'marital': 'single', 'l10n_ch_marital_from': date(1992, 6, 6), 'private_street': 'Route de chavannes 11 ', 'private_zip': '1007', 'private_city': 'Lausanne', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': '5586', 'l10n_ch_canton': 'VD', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
                {'registration_number': '32', 'company_id': company.id, 'certificate': 'vocEducationCompl', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'l10n_ch_religious_denomination': 'romanCatholic', 'name': 'Laura Armanini', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_sv_as_number': "756.3728.4917.63", 'gender': 'female', 'country_id': cls.env.ref('base.it').id, 'birthday': date(1977, 10, 4), 'marital': 'single', 'l10n_ch_marital_from': date(1977, 10, 4), 'private_street': 'Kehrgasse 8', 'private_zip': '3018', 'private_city': 'Bern', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': '351', 'l10n_ch_canton': 'BE', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
                {'registration_number': '33', 'company_id': company.id, 'certificate': 'universityEntranceCertificate', **tf33_additional_particular, "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'name': 'Pierre Châtelain', 'l10n_ch_religious_denomination': 'romanCatholic', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_sv_as_number': "756.3434.5129.12", 'gender': 'male', 'country_id': cls.env.ref('base.it').id, 'birthday': date(1972, 4, 11), 'marital': 'single', 'l10n_ch_marital_from': date(1972, 4, 11), 'private_street': 'Wiesenstrasse 14', 'private_zip': '3098', 'private_city': 'Köniz', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': '355', 'l10n_ch_canton': 'BE', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
                {'registration_number': '34', 'company_id': company.id, 'certificate': 'doctorate', **tf34_additional_particular, "l10n_ch_foreign_tax_id": "RNLMSM67D11A794W", "place_of_birth": "Bergamo", "l10n_ch_cross_border_start": date(2023, 8, 1), "l10n_ch_cross_border_commuter": True, "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'l10n_ch_religious_denomination': 'romanCatholic', 'name': 'Massimo Rinaldi', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_residence_type': 'Weekly', "l10n_ch_weekly_residence_address_street": "Via Aeroporto 2", "l10n_ch_weekly_residence_address_city": "Agno", "l10n_ch_weekly_residence_address_zip": "6982", 'l10n_ch_weekly_residence_canton': 'TI', 'l10n_ch_weekly_residence_municipality': '5141', 'l10n_ch_sv_as_number': "756.6412.9848.00", 'gender': 'male', 'country_id': cls.env.ref('base.it').id, 'birthday': date(1967, 4, 11), 'marital': 'single', 'l10n_ch_marital_from': date(1967, 4, 11), 'private_street': 'Piazza Marconi 7', 'private_zip': '24122', 'private_city': 'Bergamo', 'private_country_id': cls.env.ref('base.it').id, 'l10n_ch_municipality': False, 'l10n_ch_canton': 'EX', 'l10n_ch_residence_category': 'crossBorder-G', 'lang': 'fr_FR', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
                {'registration_number': '35', 'company_id': company.id, 'certificate': 'vocEducationCompl', **tf35_additional_particular, "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'name': 'Roland Roos', 'l10n_ch_religious_denomination': 'reformedEvangelical', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_sv_as_number': "756.6498.9438.07", 'gender': 'male', 'country_id': cls.env.ref('base.fr').id, 'birthday': date(1967, 5, 16), 'marital': 'divorced', 'l10n_ch_marital_from': date(2018, 6, 15), 'private_street': 'Via Ospedale 10', 'private_zip': '6500', 'private_city': 'Bellinzona', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': '5002', 'l10n_ch_canton': 'TI', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
                {'registration_number': '36', 'company_id': company.id, 'certificate': 'enterpriseEducation', **tf36_additional_particular, "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'name': 'Fabio Maldini', 'l10n_ch_religious_denomination': 'romanCatholic', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_sv_as_number': "756.3641.0372.46", 'gender': 'male', 'country_id': cls.env.ref('base.it').id, 'birthday': date(1988, 6, 17), 'marital': 'single', 'l10n_ch_marital_from': date(1988, 6, 17), 'private_street': 'Blockweg 2', 'private_zip': '3007', 'private_city': 'Bern', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': '351', 'l10n_ch_canton': 'BE', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
                {'registration_number': '37', 'company_id': company.id, 'certificate': 'enterpriseEducation', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'name': 'Christine Oberli', 'l10n_ch_religious_denomination': 'jewishCommunity', 'l10n_ch_concubinage': 'SoleCustody', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_sv_as_number': "756.6462.6899.46", 'gender': 'female', 'country_id': cls.env.ref('base.de').id, 'birthday': date(1990, 10, 15), 'marital': 'divorced', 'l10n_ch_marital_from': date(2020, 6, 20), 'children': 1, 'private_street': 'Hopfenweg 22', 'private_zip': '3007', 'private_city': 'Bern', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': '351', 'l10n_ch_canton': 'BE', 'l10n_ch_residence_category': 'shortTerm-L', 'lang': 'fr_FR', 'l10n_ch_tax_scale': 'H', 'l10n_ch_has_withholding_tax': True, **tf37_additional_particular},
                {'registration_number': '38', 'company_id': company.id, 'certificate': 'enterpriseEducation', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True, **c_r})], 'name': 'Claude Jung', 'l10n_ch_religious_denomination': 'romanCatholic', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_sv_as_number': "756.3514.6025.02", 'gender': 'male', 'country_id': cls.env.ref('base.fr').id, 'birthday': date(1977, 12, 11), 'marital': 'single', 'l10n_ch_marital_from': date(1977, 12, 11), 'private_street': 'Bahnhofplatz 1', 'private_zip': '2502', 'private_city': 'Biel/Bienne', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': '371', 'l10n_ch_canton': 'BE', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
                {'registration_number': '39', 'company_id': company.id, 'certificate': 'doctorate', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'name': 'Harald Hasler', 'l10n_ch_religious_denomination': 'romanCatholic', 'l10n_ch_tax_scale_type': 'CategoryPredefined', 'l10n_ch_pre_defined_tax_scale': 'HEN', 'l10n_ch_residence_type': 'Daily', 'l10n_ch_sv_as_number': "756.3466.0443.68", 'gender': 'male', 'country_id': cls.env.ref('base.de').id, 'birthday': date(1967, 1, 1), 'marital': 'single', 'l10n_ch_marital_from': date(1967, 1, 1), 'private_street': 'Maffeistrasse 5', 'private_zip': '80333', 'private_city': 'München', 'private_country_id': cls.env.ref('base.de').id, 'l10n_ch_municipality': False, 'l10n_ch_canton': 'EX', 'l10n_ch_residence_category': 'othersNotSwiss', 'lang': 'fr_FR', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
                {'registration_number': '40', 'company_id': company.id, 'certificate': 'higherEducationBachelor', **tf40_additional_particular, "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, **c_r, "l10n_ch_source_tax_settlement_letter": True, 'l10n_ch_cs_free_meals': True, **m_a, 'l10n_ch_cs_employee_participation_taxable_income': True, 'l10n_ch_cs_employee_participation_taxable_income_locked': True, 'l10n_ch_cs_employee_participation_taxable_income_unlisted': True})], 'l10n_ch_religious_denomination': 'reformedEvangelical', 'name': 'Corinne Farine', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_sv_as_number': "756.3438.2653.71", 'gender': 'female', 'country_id': cls.env.ref('base.fr').id, 'birthday': date(1996, 6, 17), 'marital': 'single', 'l10n_ch_marital_from': date(1996, 6, 17), 'private_street': 'Blockweg 2', 'private_zip': '3007', 'private_city': 'Bern', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': '351', 'l10n_ch_canton': 'BE', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True, 'children': 1},
                {'registration_number': '41', 'company_id': company.id, 'certificate': 'universityMaster', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'name': 'Max Meier', 'l10n_ch_religious_denomination': 'romanCatholic', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_sv_as_number': "756.3572.1419.82", 'gender': 'male', 'country_id': cls.env.ref('base.de').id, 'birthday': date(1990, 2, 22), 'marital': 'single', 'l10n_ch_marital_from': date(1990, 2, 22), 'private_street': 'Via Cantonale 31', 'private_zip': '6815', 'private_city': 'Melide', 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': '5198', 'l10n_ch_canton': 'TI', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
                {'registration_number': '42', 'company_id': company.id, 'certificate': 'enterpriseEducation', "l10n_ch_foreign_tax_id": "PTRTTO91S11A182V", "place_of_birth": "Alessandria", "l10n_ch_cross_border_start": date(2023, 10, 1), "l10n_ch_cross_border_commuter": True, "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'l10n_ch_religious_denomination': 'romanCatholic', 'name': 'Otto Peters', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_residence_type': 'Daily', 'l10n_ch_sv_as_number': "756.1949.3782.69", 'gender': 'male', 'country_id': cls.env.ref('base.it').id, 'birthday': date(1991, 11, 11), 'marital': 'single', 'l10n_ch_marital_from': date(1991, 11, 11), 'private_street': 'Corso Galileo Ferraris, 14', 'private_zip': '10121', 'private_city': 'Torino', 'private_country_id': cls.env.ref('base.it').id, 'l10n_ch_municipality': False, 'l10n_ch_canton': 'EX', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
                {'registration_number': '43', 'company_id': company.id, 'certificate': 'enterpriseEducation', "l10n_ch_salary_certificate_profiles": [(0, 0, {**f_b, 'certificate_template_id': salary_certificate_profile.id, "l10n_ch_source_tax_settlement_letter": True})], 'name': 'Lea Ochsenbein', 'l10n_ch_religious_denomination': 'reformedEvangelical', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode', 'l10n_ch_residence_type': 'Daily', 'l10n_ch_sv_as_number': "756.6491.7043.37", 'gender': 'female', 'country_id': cls.env.ref('base.de').id, 'birthday': date(1993, 10, 10), 'marital': 'single', 'l10n_ch_marital_from': date(1993, 10, 10), 'private_street': 'Marienplatz 1', 'private_zip': '80331', 'private_city': 'München', 'private_country_id': cls.env.ref('base.de').id, 'l10n_ch_municipality': False, 'l10n_ch_canton': 'EX', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True}
            ])
            mapped_employees = {}
            for index, employee in enumerate(employees, start=1):
                mapped_employees[f"employee_tf{str(index).zfill(2)}"] = employee


            cdi_hourly = {"contract_type_id": cls.env.ref('l10n_ch_hr_payroll.l10n_ch_contract_type_indefiniteSalaryHrs').id}
            cdd_hourly = {"contract_type_id": cls.env.ref('l10n_ch_hr_payroll.l10n_ch_contract_type_fixedSalaryHrs').id}
            cdi_month = {"contract_type_id": cls.env.ref('l10n_ch_hr_payroll.l10n_ch_contract_type_indefiniteSalaryMth').id}
            cdd_month = {"contract_type_id": cls.env.ref('l10n_ch_hr_payroll.l10n_ch_contract_type_fixedSalaryMth').id}
            cdi_month_awt = {"contract_type_id": cls.env.ref('l10n_ch_hr_payroll.l10n_ch_contract_type_indefiniteSalaryMthAWT').id}
            cdi_ntc = {"contract_type_id": cls.env.ref('l10n_ch_hr_payroll.l10n_ch_contract_type_indefiniteSalaryNoTimeConstraint').id}
            cdi_fntc = {"contract_type_id": cls.env.ref('l10n_ch_hr_payroll.l10n_ch_contract_type_fixedSalaryNoTimeConstraint').id}
            apprentice = {"contract_type_id": cls.env.ref('l10n_ch_hr_payroll.l10n_ch_contract_type_apprentice').id}
            internship = {"contract_type_id": cls.env.ref('l10n_ch_hr_payroll.l10n_ch_contract_type_internshipContract').id}
            administrative = {"contract_type_id": cls.env.ref('l10n_ch_hr_payroll.l10n_ch_contract_type_administrativeBoard').id}

            info_m = cls.env['hr.job'].create({
                "name": "Informaticien"
            })

            info_f = cls.env['hr.job'].create({
                "name": "Informaticienne"
            })

            edb = cls.env['hr.job'].create({
                "name": "Employé de bureau"
            })

            teacher = cls.env['hr.job'].create({
                "name": "Enseignant du primaire"
            })

            comm = cls.env['hr.job'].create({
                "name": "Apprenti de commerce"
            })

            journ = cls.env['hr.job'].create({
                "name": "Journaliste"
            })

            cons_cl = cls.env['hr.job'].create({
                "name": "Conseiller à la clientèle"
            })

            logist = cls.env['hr.job'].create({
                "name": "Logisticien"
            })

            commis_daff = cls.env['hr.job'].create({
                "name": "Commis d'affaires"
            })

            account = cls.env['hr.job'].create({
                "name": "Comptable financier"
            })

            pub_hol_comp = {'l10n_ch_contractual_holidays_rate': 8.33, 'l10n_ch_contractual_public_holidays_rate': 4}

            # Generate Contracts
            contracts = cls.env['hr.contract'].with_context(tracking_disable=True).create([
                # TF 01
                {"l10n_ch_job_type": "lowerCadre", **pub_hol_comp, "job_id": info_f.id, **cdi_hourly, 'name': "Contract For Monica Herz", 'employee_id': mapped_employees['employee_tf01'].id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 3, 31), 'wage_type': "hourly", 'l10n_ch_has_hourly': True, "l10n_ch_contractual_13th_month_rate": 8.33, 'wage': 0, 'hourly_wage': 50.0, 'l10n_ch_lesson_wage': 50.0, 'l10n_ch_has_lesson': True, 'state': "open", 'l10n_ch_location_unit_id': location_unit_1.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_1.line_ids[1].id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_1.line_ids[2].id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_lpp_entry_reason': 'interruptionOfEmployment', 'l10n_ch_lpp_withdrawal_reason': "interruptionOfEmployment", 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 0},
                # TF 02
                {"l10n_ch_job_type": "noCadre", "job_id": info_f.id, **cdd_hourly, 'name': "Contract For Maria Paganini", 'irregular_working_time': True, 'l10n_ch_lpp_entry_reason': 'entryCompany', 'employee_id': mapped_employees['employee_tf02'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'wage_type': "hourly", 'l10n_ch_has_hourly': True, "l10n_ch_contractual_13th_month_rate": 8.33, 'wage': 0, 'hourly_wage': 30.0, 'l10n_ch_lesson_wage': 30, 'l10n_ch_has_lesson': True, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_1.line_ids[1].id)], 'l10n_ch_location_unit_id': location_unit_1.id, 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_1.line_ids[1].id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 0, 'l10n_ch_contractual_holidays_rate': 13.04, 'l10n_ch_contractual_public_holidays_rate': 4},
                # TF 03
                {"l10n_ch_job_type": "noCadre", "job_id": edb.id, **cdi_month, 'name': "Contract For Pia Lusser", 'l10n_ch_location_unit_id': location_unit_1.id, 'lpp_employee_amount': 385, 'employee_id': mapped_employees['employee_tf03'].id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1 / 12) * 100, 'wage': 5500, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_1.line_ids[2].id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_1.line_ids[2].id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 30},
                # TF 04
                {"l10n_ch_job_type": "highestCadre", "job_id": info_m.id, **cdd_month, 'name': "Contract For Markus Fankhauser", 'l10n_ch_14th_month': True, **lpp_k2010, 'l10n_ch_location_unit_id': location_unit_2.id, 'lpp_employee_amount': 2450, 'employee_id': mapped_employees['employee_tf04'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1 / 12) * 100, 'wage': 30000, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_1.line_ids[2].id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_1.line_ids[2].id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_be_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 25},
                # TF 05
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdi_month_awt, 'name': "Contract For Johann Moser", 'l10n_ch_weekly_hours': 16, 'l10n_ch_location_unit_id': location_unit_2.id, 'lpp_employee_amount': 102, 'employee_id': mapped_employees['employee_tf05'].id, 'resource_calendar_id': resource_calendar_16_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1 / 12) * 100, 'wage': 1350, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_1.line_ids[1].id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_1.line_ids[1].id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_be_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 30},
                # TF 06
                {"l10n_ch_job_type": "lowestCadre", "job_id": info_f.id, **cdd_month, 'name': "Contract Full time For Anita Zahnd", **lpp_22, 'l10n_ch_location_unit_id': location_unit_2.id, 'lpp_employee_amount': 945, 'employee_id': mapped_employees['employee_tf06'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 10, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1 / 12) * 100, 'wage': 13500.00, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_1.line_ids[1].id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_1.line_ids[1].id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_be_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20},
                # TF 07
                {"l10n_ch_job_type": "noCadre", "job_id": teacher.id, **cdi_month, 'name': "Contract Full Time For Heidi Burri", **lpp_22, "l10n_ch_lpp_withdrawal_reason": "retirement", 'l10n_ch_location_unit_id': location_unit_2.id, 'lpp_employee_amount': 560, 'employee_id': mapped_employees['employee_tf07'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2021, 11, 1), 'date_end': date(2021, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1 / 12) * 100, 'wage': 8000, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_be_1.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 30},
                # TF 08
                {"l10n_ch_job_type": "lowerCadre", "job_id": info_m.id, **cdd_hourly, **pub_hol_comp, 'name': "Contract For René Lamon", **lpp_22, 'l10n_ch_lesson_wage': 50.0, 'l10n_ch_has_lesson': True, 'l10n_ch_location_unit_id': location_unit_2.id, 'lpp_employee_amount': 724, 'employee_id': mapped_employees['employee_tf08'].id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "hourly", 'l10n_ch_has_hourly': True, "l10n_ch_contractual_13th_month_rate": 8.33, 'wage': 0, 'hourly_wage': 50.0, 'state': "open", 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_be_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 0},
                # TF 09
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdi_month, 'name': "Contract full time For Michael Estermann", 'l10n_ch_location_unit_id': location_unit_1.id, 'employee_id': mapped_employees['employee_tf09'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1 / 12) * 100, 'wage': 2000, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '3', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_12.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 30, 'l10n_ch_avs_status': 'retired'},
                # TF 10,
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdi_month, 'name': "Contract For Heinz Ganz", **lpp_21, "l10n_ch_lpp_withdrawal_reason": "others", 'l10n_ch_location_unit_id': location_unit_1.id, 'lpp_employee_amount': 448, 'employee_id': mapped_employees['employee_tf10'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 10, 30), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1 / 12) * 100, 'wage': 6400, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20},
                # TF11,
                {"l10n_ch_job_type": "middleCadre", "job_id": info_m.id, **cdi_month, 'name': "Contract 3/10 For Bosshard Peter", **lpp_k2010, 'l10n_ch_lpp_entry_valid_as_of': date(2022, 1, 1), 'l10n_ch_weekly_hours': 12.60, 'lpp_employee_amount': 763, 'employee_id': mapped_employees['employee_tf11'].id, 'resource_calendar_id': resource_calendar_12_6_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'l10n_ch_location_unit_id': location_unit_1.id, 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 9600, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id), (4, laac_12.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id), (4, ijm_12.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20},
                # TF12,
                {"l10n_ch_job_type": "lowerCadre", "job_id": info_m.id, **cdi_month, 'name': "Regular Contract 42 Hours For Casanova Renato", **lpp_11, 'l10n_ch_location_unit_id': location_unit_1.id, 'lpp_employee_amount': 840, 'employee_id': mapped_employees['employee_tf12'].id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 2, 27), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 12000.00, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '2', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20},
                # TF13,
                {"l10n_ch_job_type": "noCadre", "job_id": comm.id, **apprentice, 'name': "Contract For Renato Combertaldi", 'employee_id': mapped_employees['employee_tf13'].id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1 / 12) * 100, 'wage': 2000.00, 'hourly_wage': 0.0, 'l10n_ch_lesson_wage': 0.0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_1.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '0', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_lpp_not_insured': True, 'l10n_ch_avs_status': 'youth'},
                # TF14,
                {"l10n_ch_job_type": "lowestCadre", "job_id": info_f.id, **cdd_hourly, 'name': "Contract For Anna Egli", 'irregular_working_time': True, 'employee_id': mapped_employees['employee_tf14'].id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2021, 11, 1), 'wage_type': "hourly", 'l10n_ch_has_hourly': True, "l10n_ch_contractual_13th_month_rate": 8.33, 'wage': 0.0, 'hourly_wage': 25, 'l10n_ch_lesson_wage': 25, 'l10n_ch_has_lesson': True, 'state': "open", 'l10n_ch_location_unit_id': location_unit_1.id, 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_compensation_fund_id': caf_lu_1.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 0, 'l10n_ch_lpp_not_insured': True, 'l10n_ch_avs_status': 'exempted', 'l10n_ch_contractual_holidays_rate': 8.33, 'l10n_ch_contractual_public_holidays_rate': 4},
                # TF15,
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdd_hourly, 'name': "Contract For Lorenz Degelo", 'l10n_ch_contractual_holidays_rate': 0, 'l10n_ch_contractual_public_holidays_rate': 0, 'l10n_ch_weekly_lessons': 10.5, 'l10n_ch_weekly_hours': 0, 'employee_id': mapped_employees['employee_tf15'].id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 2, 28), 'date_end': date(2022, 3, 1), 'wage_type': "hourly", 'l10n_ch_has_hourly': True, "l10n_ch_contractual_13th_month_rate": 8.33, 'wage': 0.0, 'hourly_wage': 133.35, 'l10n_ch_lesson_wage': 133.35, 'l10n_ch_has_lesson': True, 'state': "open", 'l10n_ch_location_unit_id': location_unit_1.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '3', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_lpp_not_insured': True},
                # TF16,
                {"l10n_ch_job_type": "middleCadre", "job_id": journ.id, **cdi_ntc, 'name': "Contract For Anna Aebi", 'l10n_ch_location_unit_id': location_unit_1.id, 'employee_id': mapped_employees['employee_tf16'].id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2021, 11, 1), 'date_end': date(2021, 12, 20), 'wage_type': "NoTimeConstraint", "l10n_ch_contractual_13th_month_rate": (1 / 12) * 100, 'wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_12.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_lpp_not_insured': True, 'l10n_ch_compensation_fund_id': caf_lu_1.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_contractual_holidays_rate': 0, 'l10n_ch_contractual_public_holidays_rate': 0, 'l10n_ch_yearly_holidays': 30, 'irregular_working_time': True},
                {"l10n_ch_job_type": "middleCadre", "job_id": journ.id, **cdi_ntc, 'name': "Contract For Anna Aebi", 'l10n_ch_location_unit_id': location_unit_1.id, 'employee_id': mapped_employees['employee_tf16'].id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 15), 'date_end': date(2022, 3, 27), 'wage_type': "NoTimeConstraint", "l10n_ch_contractual_13th_month_rate": (1 / 12) * 100, 'wage': 0, 'state': "draft", 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_12.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_lpp_not_insured': True, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_contractual_holidays_rate': 0, 'l10n_ch_contractual_public_holidays_rate': 0, 'l10n_ch_yearly_holidays': 30, 'l10n_ch_avs_status': 'retired', 'irregular_working_time': True},
                # TF17,
                {"l10n_ch_job_type": "noCadre", "job_id": cons_cl.id, **cdi_month, 'name': "Contract For Fritz Binggeli", 'employee_id': mapped_employees['employee_tf17'].id, 'resource_calendar_id': resource_calendar_70_percent.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1 / 12) * 100, 'wage': 4550, 'hourly_wage': 0.0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_compensation_fund_id': caf_ti_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 25, 'l10n_ch_lpp_not_insured': True, 'l10n_ch_other_employers': True, 'l10n_ch_other_employers_occupation_rate': 30, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly', 'l10n_ch_weekly_hours': 28},
                # TF18,
                {"l10n_ch_job_type": "noCadre", "job_id": logist.id, **cdi_hourly, **pub_hol_comp, 'name': "Contract For Pierre Blanc", **lpp_11, 'l10n_ch_weekly_hours': 8.4, 'lpp_employee_amount': 117, 'employee_id': mapped_employees['employee_tf18'].id, 'resource_calendar_id': resource_calendar_8_4_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'l10n_ch_lesson_wage': 30.0, 'l10n_ch_has_lesson': True, 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2023, 2, 28), 'wage_type': "hourly", 'l10n_ch_has_hourly': True, "l10n_ch_contractual_13th_month_rate": 8.33, 'wage': 0, 'hourly_wage': 30, 'state': "open", 'l10n_ch_location_unit_id': location_unit_1.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '3', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 0, 'l10n_ch_other_employers': True, 'l10n_ch_other_employers_occupation_rate': 60, 'l10n_ch_has_withholding_tax': True},
                # TF19,
                {"l10n_ch_job_type": "noCadre", "job_id": info_f.id, **cdi_month, 'name': "Contract For Melanie Andrey", 'employee_id': mapped_employees['employee_tf19'].id, 'resource_calendar_id': resource_calendar_50_percent.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1 / 12) * 100, 'wage': 2600, 'hourly_wage': 0.0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_compensation_fund_id': caf_ti_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 25, 'l10n_ch_lpp_not_insured': True, 'l10n_ch_other_employers': True, 'l10n_ch_other_employers_occupation_rate': 40, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly', 'l10n_ch_weekly_hours': 20},
                # TF20,
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdd_month, 'name': "Contract For Lukas Arnold", 'employee_id': mapped_employees['employee_tf20'].id, 'resource_calendar_id': resource_calendar_16_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 3, 15), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1 / 12) * 100, 'wage': 2000, 'state': "open", 'l10n_ch_location_unit_id': location_unit_2.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_be_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_other_employers': True, 'l10n_ch_has_withholding_tax': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_weekly_hours': 16},
                # TF21,
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdd_month, 'name': "Contract For Christian Meier", 'employee_id': mapped_employees['employee_tf21'].id, 'resource_calendar_id': resource_calendar_40_percent.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 3, 15), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1 / 12) * 100, 'wage': 2000, 'hourly_wage': 0.0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_compensation_fund_id': caf_ti_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 25, 'l10n_ch_lpp_not_insured': True, 'l10n_ch_other_employers': True, 'l10n_ch_other_employers_occupation_rate': 50, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly', 'l10n_ch_weekly_hours': 16},
                # TF22,
                {"l10n_ch_job_type": "noCadre", "job_id": info_f.id, **cdi_hourly, **pub_hol_comp, 'name': "Contract For Elisabeth Bucher", 'l10n_ch_lesson_wage': 35.0, 'l10n_ch_has_lesson': True, 'irregular_working_time': True, 'employee_id': mapped_employees['employee_tf22'].id, 'resource_calendar_id': resource_calendar_8_4_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'wage_type': "hourly", 'l10n_ch_has_hourly': True, "l10n_ch_contractual_13th_month_rate": 8.33, 'wage': 0, 'hourly_wage': 35, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_ti_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 0, 'l10n_ch_other_employers': False, 'l10n_ch_has_withholding_tax': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
                # TF23,
                {"l10n_ch_job_type": "lowestCadre", "job_id": info_m.id, **cdi_month, 'name': "Contract For Ludwig Koller", 'lpp_employee_amount': 379, 'employee_id': mapped_employees['employee_tf23'].id, 'resource_calendar_id': resource_calendar_40_percent.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1 / 12) * 100, 'wage': 5000, 'hourly_wage': 0.0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_ti_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_other_employers': False, 'l10n_ch_other_employers_occupation_rate': 0, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
                # TF24,
                {"l10n_ch_job_type": "middleCadre", "job_id": info_m.id, **cdi_month, 'name': "Contract For Jan Utzinger", 'lpp_employee_amount': 607, 'employee_id': mapped_employees['employee_tf24'].id, 'resource_calendar_id': resource_calendar_8_4_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1 / 12) * 100, 'wage': 8000, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_ti_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_other_employers': False, 'l10n_ch_has_withholding_tax': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
                # TF25,
                {"l10n_ch_job_type": "lowestCadre", "job_id": info_f.id, **cdi_month, 'name': "Contract For Nadine Lehmann", 'employee_id': mapped_employees['employee_tf25'].id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 2, 10), 'date_end': date(2022, 6, 15), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1 / 12) * 100, 'wage': 12000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_1.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_12.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_12.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20},
                # TF26,
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdi_month, 'name': "Contract For Marcel Jenzer", 'l10n_ch_lpp_not_insured': True, 'employee_id': mapped_employees['employee_tf26'].id, 'resource_calendar_id': resource_calendar_8_4_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 2, 10), 'date_end': date(2022, 6, 15), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1 / 12) * 100, 'wage': 12000, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_12.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_12.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_ti_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 25, 'l10n_ch_other_employers': False, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
                # TF27,
                {"l10n_ch_job_type": "noCadre", "job_id": logist.id, **cdi_month, 'name': "Contract For Rast Eva", **lpp_k2010, 'lpp_employee_amount': 700, 'employee_id': mapped_employees['employee_tf27'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 5, 1), 'date_end': date(2023, 2, 28), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 10000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_2.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_be_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_lpp_not_insured': False, 'l10n_ch_monthly_effective_days': 20},
                # TF28,
                {"l10n_ch_job_type": "lowestCadre", "job_id": info_f.id, **cdi_month, 'name': "Contract For Arbenz Esther", 'employee_id': mapped_employees['employee_tf28'].id, 'resource_calendar_id': resource_calendar_24_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 6000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_2.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_compensation_fund_id': caf_be_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_lpp_not_insured': False, 'l10n_ch_other_employers_occupation_rate': 20, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_weekly_hours': 24},
                # TF29,
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdi_month, 'name': "Contract For Forster Moreno", 'employee_id': mapped_employees['employee_tf29'].id, 'resource_calendar_id': resource_calendar_60_percent.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 6000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_ti_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_other_employers': True, 'l10n_ch_other_employers_occupation_rate': 20, 'l10n_ch_is_model': 'yearly', 'l10n_ch_weekly_hours': 24},
                # TF30,
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdi_ntc, 'name': "Contract For Müller Heinrich", 'employee_id': mapped_employees['employee_tf30'].id, 'resource_calendar_id': resource_calendar_0_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 9, 30),'irregular_working_time' : True, 'wage_type': "NoTimeConstraint", "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 0, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_2.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '0', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_be_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly', 'l10n_ch_is_predefined_category': 'ME', 'l10n_ch_contractual_holidays_rate': 0, 'l10n_ch_contractual_public_holidays_rate': 0},
                # TF31,
                {"l10n_ch_job_type": "noCadre", "job_id": info_f.id, **cdi_month, 'name': "Contract For Bolletto Franca", 'employee_id': mapped_employees['employee_tf31'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 5000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_3.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_vd_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
                # TF32,
                {"l10n_ch_job_type": "noCadre", "job_id": logist.id, **cdi_month, 'name': "Contract For Armanini Laura", **lpp_21, 'lpp_employee_amount': 350, 'employee_id': mapped_employees['employee_tf32'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 9, 1), 'date_end': date(2023, 2, 28), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 5000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_2.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_be_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly'},
                # TF33,
                {"l10n_ch_job_type": "lowerCadre", "job_id": info_m.id, **cdi_month, 'name': "Contract For Châtelain Pierre", 'employee_id': mapped_employees['employee_tf33'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 5000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_2.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_be_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 25, 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly'},
                # TF34,
                {"l10n_ch_job_type": "lowerCadre", "job_id": info_m.id, **cdi_month, 'name': "Contract For Rinaldi Massimo", 'employee_id': mapped_employees['employee_tf34'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 5000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_ti_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 25, 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
                # TF35,
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdi_month, 'name': "Contract For Roos Roland", **lpp_21, 'lpp_employee_amount': 379, 'employee_id': mapped_employees['employee_tf35'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 5000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_ti_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 25, 'l10n_ch_lpp_not_insured': False, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
                # TF36,
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdi_month, 'name': "Contract For Maldini Fabio", 'employee_id': mapped_employees['employee_tf36'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 5000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_2.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_be_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly'},
                # TF37,
                {"l10n_ch_job_type": "noCadre", "job_id": commis_daff.id, **cdi_month, 'name': "Contract For Oberli Christine", 'lpp_employee_amount': 0, 'employee_id': mapped_employees['employee_tf37'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2021, 11, 16), 'date_end': date(2021, 12, 10), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": 0, 'wage': 10000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_2.id, 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_compensation_fund_id': caf_be_1.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_lpp_not_insured': False, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly'},
                {"l10n_ch_job_type": "noCadre", "job_id": commis_daff.id, **cdi_month, 'name': "Contract For Oberli Christine", 'lpp_employee_amount': 0, 'employee_id': mapped_employees['employee_tf37'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2021, 12, 21), 'date_end': date(2022, 1, 18), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": 0, 'wage': 8000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "draft", 'l10n_ch_location_unit_id': location_unit_2.id, 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_compensation_fund_id': caf_be_1.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_lpp_not_insured': False, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly'},
                # TF38,
                {"l10n_ch_job_type": "noCadre", "job_id": logist.id, **cdi_month, 'name': "Contract For Jung Claude", 'lpp_employee_amount': 362, 'employee_id': mapped_employees['employee_tf38'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 3000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_2.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_be_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly'},
                # TF39,
                {"l10n_ch_job_type": "noCadre", "job_id": account.id, **administrative, 'name': "Contract For Hasler Harald", 'l10n_ch_contractual_holidays_rate': 0, 'l10n_ch_contractual_public_holidays_rate': 0, 'irregular_working_time': True, 'employee_id': mapped_employees['employee_tf39'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "NoTimeConstraint", "l10n_ch_contractual_13th_month_rate": 0, 'wage': 0, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_2.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '0', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_be_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 0, 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly', 'l10n_ch_avs_status': 'exempted', 'l10n_ch_is_predefined_category': 'HE'},
                # TF40,
                {"l10n_ch_job_type": "noCadre", "job_id": edb.id, **cdd_month, 'name': "Contract For Farine Corinne", 'lpp_employee_amount': 303, 'employee_id': mapped_employees['employee_tf40'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 3, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 4000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_2.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_12.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_compensation_fund_id': caf_be_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_lpp_withdrawal_valid_as_of': date(2022, 2, 28), 'l10n_ch_lpp_withdrawal_reason': 'interruptionOfEmployment' , 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly'},
                {"l10n_ch_job_type": "noCadre", "job_id": edb.id, **cdd_month, 'name': "Contract For Farine Corinne", 'lpp_employee_amount': 303, 'employee_id': mapped_employees['employee_tf40'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 10, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 4000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "draft",'l10n_ch_location_unit_id': location_unit_3.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_compensation_fund_id': caf_vd_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_lpp_entry_reason': 'interruptionOfEmployment', 'l10n_ch_lpp_withdrawal_reason': 'interruptionOfEmployment' , 'l10n_ch_is_model': 'yearly'},
                {"l10n_ch_job_type": "noCadre", "job_id": edb.id, **cdd_month, 'name': "Contract For Farine Corinne", 'lpp_employee_amount': 303, 'employee_id': mapped_employees['employee_tf40'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 12, 1), 'date_end': date(2023, 2, 28), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 4000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "draft", 'l10n_ch_location_unit_id': location_unit_3.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_compensation_fund_id': caf_vd_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_lpp_entry_reason': 'interruptionOfEmployment', 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
                # TF41,
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdi_month, 'name': "Contract For Meier Max", 'employee_id': mapped_employees['employee_tf41'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 3, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 10000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_ti_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
                {"l10n_ch_job_type": "noCadre", "job_id": info_m.id, **cdi_month, 'name': "Contract For Meier Max", 'employee_id': mapped_employees['employee_tf41'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 7, 1), 'date_end': date(2022, 7, 31), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 10000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "draft", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_ti_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
                # TF42,
                {"l10n_ch_job_type": "noCadre", "job_id": account.id, **cdd_month, 'name': "Contract For Peters Otto", 'employee_id': mapped_employees['employee_tf42'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 11, 1), 'date_end': date(2022, 12, 15), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1/12)*100, 'wage': 6666.65, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_ti_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
                # TF43,
                {"l10n_ch_job_type": "noCadre", "job_id": info_f.id, **cdd_month, 'name': "Contract For Lea Ochsenbein", 'employee_id': mapped_employees['employee_tf43'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': company.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 11, 1), 'date_end': date(2022, 12, 15), 'wage_type': "monthly", 'l10n_ch_has_monthly': True, "l10n_ch_contractual_13th_month_rate": (1 / 12) * 100, 'wage': 6666.65, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_2.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1', 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_be_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly'},
            ])
            contracts_by_employee = defaultdict(lambda: cls.env['hr.contract'])
            for contract in contracts:
                contracts_by_employee[contract.employee_id] += contract
            mapped_contracts = {}
            for eidx, employee in enumerate(employees, start=1):
                for cidx, contract in enumerate(contracts_by_employee[employee], start=1):
                    mapped_contracts[f"contract_tf{str(eidx).zfill(2)}_{str(cidx).zfill(2)}"] = contract

            all_emps = cls.env["hr.employee"]
            for emp in mapped_employees:
                all_emps += mapped_employees[emp]
            # Generate Payslips
            mapped_payslips = {}

            cls.env['l10n.ch.hr.contract.wage'].create([
                # TF01
                {'description': 'Salaire horaire', 'amount': 160.0, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf01_01'].id},
                {'description': 'Salaire horaire', 'amount': 160.0, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf01_01'].id},
                {'description': 'Salaire horaire', 'amount': 170.0, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf01_01'].id},
                {'description': 'Gratification', 'amount': 20000, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1204').id, 'contract_id': mapped_contracts['contract_tf01_01'].id},
                {'description': 'Part facultative employeurs LPP', 'amount': 682, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1972').id, 'contract_id': mapped_contracts['contract_tf01_01'].id},
                {'description': 'Part facultative employeurs LPP', 'amount': 682, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1972').id, 'contract_id': mapped_contracts['contract_tf01_01'].id},
                {'description': 'Part facultative employeurs LPP', 'amount': 682, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1972').id, 'contract_id': mapped_contracts['contract_tf01_01'].id},
                {'description': 'Compensation cotisations LPP employeur', 'amount': 682, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_5111').id, 'contract_id': mapped_contracts['contract_tf01_01'].id},
                {'description': 'Compensation cotisations LPP employeur', 'amount': 682, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_5111').id, 'contract_id': mapped_contracts['contract_tf01_01'].id},
                {'description': 'Compensation cotisations LPP employeur', 'amount': 682, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_5111').id, 'contract_id': mapped_contracts['contract_tf01_01'].id},
                {'description': 'Indemnité APG', 'amount': 1200, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2000').id, 'contract_id': mapped_contracts['contract_tf01_01'].id},
                {'description': 'Indemnité APG', 'amount': 1300, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2000').id, 'contract_id': mapped_contracts['contract_tf01_01'].id},
                {'description': 'Prestation compensation mil. (CCM)', 'amount': 1000, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2005').id, 'contract_id': mapped_contracts['contract_tf01_01'].id},
                {'description': 'Indemnité journalière accident', 'amount': 1250, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2030').id, 'contract_id': mapped_contracts['contract_tf01_01'].id},
                {'description': 'Indemnité journalière accident', 'amount': 1250, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2030').id, 'contract_id': mapped_contracts['contract_tf01_01'].id},
                {'description': 'Indemnité maladie', 'amount': 250, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2035').id, 'contract_id': mapped_contracts['contract_tf01_01'].id},
                {'description': 'Indemnité maladie', 'amount': 250, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2035').id, 'contract_id': mapped_contracts['contract_tf01_01'].id},
                {'description': 'Indemnité maladie', 'amount': 1000, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2035').id, 'contract_id': mapped_contracts['contract_tf01_01'].id},
                {'contract_id': mapped_contracts['contract_tf01_01'].id, 'amount': 0, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2050').id},
                {'contract_id': mapped_contracts['contract_tf01_01'].id, 'amount': 0, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2050').id},
                {'contract_id': mapped_contracts['contract_tf01_01'].id, 'amount': 0, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2050').id},
                {'contract_id': mapped_contracts['contract_tf01_01'].id, 'amount': 0, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2050').id},
                # TF02
                {'description': 'Salaire horaire', 'amount': 150.0, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Salaire horaire', 'amount': 70.0, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Salaire horaire', 'amount': 70.0, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Salaire horaire', 'amount': 142.0, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Salaire horaire', 'amount': 20.0, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Salaire horaire', 'amount': 100.0, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Salaire horaire', 'amount': 120.0, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Salaire horaire', 'amount': 130.0, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Salaire horaire', 'amount': 162.0, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Salaire horaire', 'amount': 50.0, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Salaire horaire', 'amount': 162.0, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Salaire horaire', 'amount': 150.0, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Salaire horaire', 'amount': 120.0, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Salaire horaire', 'amount': 50.0, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Salaire à la leçon', 'amount': 20.0, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Salaire à la leçon', 'amount': 20.0, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Salaire à la leçon', 'amount': 40.0, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Salaire à la leçon', 'amount': 20.0, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Salaire à la leçon', 'amount': 20.0, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Salaire à la leçon', 'amount': 20.0, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Salaire à la leçon', 'amount': 20.0, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Salaire à la leçon', 'amount': 20.0, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 90, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 50, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 25, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 35, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 40, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 35, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 105, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 89, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 81, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 95, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Commission', 'amount': 2044, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1218').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Perte de gain RHT/ITP (SH)', 'amount': 3000, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2065').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Perte de gain RHT/ITP (SH)', 'amount': 3000, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2065').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Indemnité de chômage', 'amount': 2200, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2070').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Indemnité de chômage', 'amount': 2200, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2070').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Délai de carence RHT/ITP', 'amount': 200, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2075').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Délai de carence RHT/ITP', 'amount': 200, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2075').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 200, 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf02_01'].id},
                # TF03
                {'description': 'Indemnité spéciale', 'amount': 3200, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1212').id, 'contract_id': mapped_contracts['contract_tf03_01'].id},
                {'description': 'Indemnité spéciale', 'amount': 3200, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1212').id, 'contract_id': mapped_contracts['contract_tf03_01'].id},
                {'description': 'Cadeau pour ancienneté de service', 'amount': 22000, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1230').id, 'contract_id': mapped_contracts['contract_tf03_01'].id},
                {'description': 'Prestation en capital à caractère de prévoyance', 'amount': 6000, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1410').id, 'contract_id': mapped_contracts['contract_tf03_01'].id},
                # TF04
                {'description': 'Cadeau pour ancienneté de service', 'amount': 40000, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1230').id, 'contract_id': mapped_contracts['contract_tf04_01'].id},
                {'description': 'Cadeau pour ancienneté de service', 'amount': 40000, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1230').id, 'contract_id': mapped_contracts['contract_tf04_01'].id},
                # TF05
                {'description': 'Indemnité de dimanche', 'amount': 6000, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1073').id, 'contract_id': mapped_contracts['contract_tf05_01'].id},
                {'description': 'Indemnité de dimanche', 'amount': 6000, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1073').id, 'contract_id': mapped_contracts['contract_tf05_01'].id},
                {'description': 'Indemnité journalière accident', 'amount': 10000, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2030').id, 'contract_id': mapped_contracts['contract_tf05_01'].id},
                {'description': 'Indemnité journalière accident', 'amount': 10000, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2030').id, 'contract_id': mapped_contracts['contract_tf05_01'].id},
                # TF06
                {'description': 'Indemnité APG', 'amount': 4800, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2000').id, 'contract_id': mapped_contracts['contract_tf06_01'].id},
                {'description': 'Indemnité APG', 'amount': 4800, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2000').id, 'contract_id': mapped_contracts['contract_tf06_01'].id},
                {'description': 'Indemnité journalière accident', 'amount': 15200, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2030').id, 'contract_id': mapped_contracts['contract_tf06_01'].id},
                {'description': 'Indemnité journalière accident', 'amount': 15200, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2030').id, 'contract_id': mapped_contracts['contract_tf06_01'].id},
                # TF 07
                {'description': 'Heures supplémentaires après le départ', 'amount': 15000, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_1067').id, 'contract_id': mapped_contracts['contract_tf07_01'].id},
                {'description': 'Indemnité journalière accident', 'amount': 9500, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2030').id, 'contract_id': mapped_contracts['contract_tf07_01'].id},
                # TF08
                {'description': 'Salaire horaire', 'amount': 170.0, 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Salaire horaire', 'amount': 350.0, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 25, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 35, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 40, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 35, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 105, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 89, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 81, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 44, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 95, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Indemnité travail par équipes', 'amount': 44, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1070').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Indemnité de dimanche', 'amount': 20000, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1073').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Commission', 'amount': 2044, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1218').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf08_01'].id},
                # TF09
                {'description': 'Gratification', 'amount': 1700, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1204').id, 'contract_id': mapped_contracts['contract_tf09_01'].id},
                {'description': 'Gratification', 'amount': 200, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1204').id, 'contract_id': mapped_contracts['contract_tf09_01'].id},
                {'description': 'Indemnité spéciale', 'amount': 35000, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1212').id, 'contract_id': mapped_contracts['contract_tf09_01'].id},
                {'description': 'Indemnité journalière accident', 'amount': 30000, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2030').id, 'contract_id': mapped_contracts['contract_tf09_01'].id},
                {'description': 'Indemnité journalière accident', 'amount': 32000, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2030').id, 'contract_id': mapped_contracts['contract_tf09_01'].id},
                # TF10
                {'description': 'Heures supplémentaires 125%', 'amount': 1200, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1061').id, 'contract_id': mapped_contracts['contract_tf10_01'].id},
                {'description': 'Indemnité spéciale', 'amount': 31000, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1212').id, 'contract_id': mapped_contracts['contract_tf10_01'].id},
                {'description': 'Indemnité spéciale', 'amount': 7000, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1212').id, 'contract_id': mapped_contracts['contract_tf10_01'].id},
                {'description': 'Indemnité APG', 'amount': 1000, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2000').id, 'contract_id': mapped_contracts['contract_tf10_01'].id},
                {'description': 'Prestation compensation mil. (CCM)', 'amount': 800, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2005').id, 'contract_id': mapped_contracts['contract_tf10_01'].id},
                {'description': 'Indemnité journalière accident', 'amount': 2000, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2030').id, 'contract_id': mapped_contracts['contract_tf10_01'].id},
                {'description': 'Indemnité maladie', 'amount': 2500, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2035').id, 'contract_id': mapped_contracts['contract_tf10_01'].id},
                {'description': 'Déduction RHT/ITP (SM)', 'amount': 3000, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2060').id, 'contract_id': mapped_contracts['contract_tf10_01'].id},
                {'description': 'Versement salaire après décès', 'amount': 6400, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1420').id, 'contract_id': mapped_contracts['contract_tf10_01'].id},
                {'description': 'Versement salaire après décès', 'amount': 6400, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1420').id, 'contract_id': mapped_contracts['contract_tf10_01'].id},
                {'description': 'Indemnité de chômage', 'amount': 2200, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2070').id, 'contract_id': mapped_contracts['contract_tf10_01'].id},
                {'description': 'Délai de carence RHT/ITP', 'amount': 200, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2075').id, 'contract_id': mapped_contracts['contract_tf10_01'].id},
                # TF11
                {'description': 'Honoraires', 'amount': 20000, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1010').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Honoraires', 'amount': 15000, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1010').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Indemnité de résidence', 'amount': 500, 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1033').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Gratification', 'amount': 5000, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1204').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Indemnité spéciale', 'amount': 3400, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1212').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Indemnité spéciale', 'amount': 1200, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1212').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Indemnité spéciale', 'amount': 500, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1212').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Prestation en capital à caractère de prévoyance', 'amount': 50000, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1410').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Part privée voiture de service', 'amount': 250, 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1910').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Réduction loyer logement locatif', 'amount': 1200, 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1950').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Actions de collaborateurs', 'amount': 20000, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1961').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Actions de collaborateurs', 'amount': -20000, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1961').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Part facultative employeurs rachat LPP', 'amount': 5000, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1973').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Compensation rachat LPP employeur', 'amount': 5000, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_5112').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 250, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 250, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 450, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 450, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 450, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 450, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 450, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 450, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 450, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 450, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 200, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 200, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 200, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 200, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Allocation de naissance', 'amount': 1000, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3034').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Correction prestations en nature', 'amount': 1200, 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5100').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Correction avantage en argent', 'amount': 250, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5110').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Correction avantage en argent', 'amount': 250, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5110').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Correction avantage en argent', 'amount': 20250, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5110').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Correction avantage en argent', 'amount': 250, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5110').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Correction avantage en argent', 'amount': 250, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5110').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Correction avantage en argent', 'amount': 19750, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5110').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': 'Correction avantage en argent', 'amount': 250, 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5110').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                {'description': '13e Mois', 'amount': 4000, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1200').id, 'contract_id': mapped_contracts['contract_tf11_01'].id},
                # TF12
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 1000, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1218').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 10000, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1218').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 25000, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1218').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 200, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1900').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 200, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1900').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 200, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1900').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 200, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1900').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 200, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1900').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 200, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1900').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 200, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1900').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 200, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1900').id},
                {"description": "Logement gratuit", 'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 650, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1902').id},
                {"description": "Logement gratuit", 'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 650, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1902').id},
                {"description": "Logement gratuit", 'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 650, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1902').id},
                {"description": "Logement gratuit", 'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 650, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1902').id},
                {"description": "Logement gratuit", 'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 650, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1902').id},
                {"description": "Logement gratuit", 'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 650, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1902').id},
                {"description": "Logement gratuit", 'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 650, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1902').id},
                {"description": "Logement gratuit", 'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 650, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1902').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 7000, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1962').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 2000, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1980').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 2000, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2000').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 1500, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2005').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 3000, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_2030').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 850, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5100').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 850, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5100').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 850, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5100').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 850, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5100').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 850, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5100').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 850, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5100').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 850, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5100').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 850, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5100').id},
                {'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 7000, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5110').id},
                {"description": "Frais effectifs expatriés", 'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 1000, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6020').id},
                {"description": "Frais effectifs expatriés", 'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 1000, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6020').id},
                {"description": "Frais effectifs expatriés", 'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 1000, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6020').id},
                {"description": "Frais effectifs expatriés", 'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 1000, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6020').id},
                {"description": "Frais effectifs expatriés", 'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 1000, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6020').id},
                {"description": "Frais effectifs expatriés", 'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 1000, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6020').id},
                {"description": "Frais effectifs expatriés", 'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 1000, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6020').id},
                {"description": "Frais effectifs expatriés", 'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 1000, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6020').id},
                {"description": "Frais forfaitaires de voiture", 'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 800, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6050').id},
                {"description": "Frais forfaitaires de voiture", 'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 800, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6050').id},
                {"description": "Frais forfaitaires de voiture", 'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 800, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6050').id},
                {"description": "Autres frais forfaitaires",'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 300, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6070').id},
                {"description": "Autres frais forfaitaires",'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 300, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6070').id},
                {"description": "Autres frais forfaitaires",'contract_id': mapped_contracts['contract_tf12_01'].id, 'amount': 300, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6070').id},
                # TF13
                {'description': 'Indemnité de résidence', 'amount': 200, 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1033').id, 'contract_id': mapped_contracts['contract_tf13_01'].id},
                {'description': 'Heures supplémentaires', 'amount': 180, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1065').id, 'contract_id': mapped_contracts['contract_tf13_01'].id},
                {'description': 'Heures supplémentaires', 'amount': 300, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1065').id, 'contract_id': mapped_contracts['contract_tf13_01'].id},
                {'description': 'Heures supplémentaires', 'amount': 80, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1065').id, 'contract_id': mapped_contracts['contract_tf13_01'].id},
                {'description': 'Heures supplémentaires', 'amount': 250, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1065').id, 'contract_id': mapped_contracts['contract_tf13_01'].id},
                {'description': 'Commission', 'amount': 1000, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1218').id, 'contract_id': mapped_contracts['contract_tf13_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 200, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf13_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 200, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf13_01'].id},
                {'description': 'Frais de voyage', 'amount': 500, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6000').id, 'contract_id': mapped_contracts['contract_tf13_01'].id},
                {'description': 'Frais de voyage', 'amount': 500, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6000').id, 'contract_id': mapped_contracts['contract_tf13_01'].id},
                {'description': 'Frais de voyage', 'amount': 500, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6000').id, 'contract_id': mapped_contracts['contract_tf13_01'].id},
                {'description': 'Frais de voyage', 'amount': 500, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6000').id, 'contract_id': mapped_contracts['contract_tf13_01'].id},
                {'description': 'Frais de voyage', 'amount': 500, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6000').id, 'contract_id': mapped_contracts['contract_tf13_01'].id},
                {'description': 'Frais de voyage', 'amount': 500, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6000').id, 'contract_id': mapped_contracts['contract_tf13_01'].id},
                {'description': 'Frais de voyage', 'amount': 500, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6000').id, 'contract_id': mapped_contracts['contract_tf13_01'].id},
                {'description': 'Frais de voyage', 'amount': 500, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6000').id, 'contract_id': mapped_contracts['contract_tf13_01'].id},
                {'description': 'Frais de voyage', 'amount': 500, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6000').id, 'contract_id': mapped_contracts['contract_tf13_01'].id},
                {'description': 'Frais de voyage', 'amount': 500, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6000').id, 'contract_id': mapped_contracts['contract_tf13_01'].id},
                {'description': 'Frais de voyage', 'amount': 500, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6000').id, 'contract_id': mapped_contracts['contract_tf13_01'].id},
                # TF14
                {'description': 'Salaire horaire', 'amount': 75.0, 'date_start': date(2021, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf14_01'].id},
                {'description': 'Salaire horaire', 'amount': 130.0, 'date_start': date(2021, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf14_01'].id},
                {'description': 'Salaire horaire', 'amount': 120.0, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf14_01'].id},
                {'description': 'Salaire horaire', 'amount': 115.0, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf14_01'].id},
                {'description': 'Salaire horaire', 'amount': 160.0, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf14_01'].id},
                {'description': 'Salaire horaire', 'amount': 95.0, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf14_01'].id},
                {'description': 'Salaire horaire', 'amount': 140.0, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf14_01'].id},
                {'description': 'Salaire horaire', 'amount': 140.0, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf14_01'].id},
                {'description': 'Salaire horaire', 'amount': 125.0, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf14_01'].id},
                {'description': 'Salaire horaire', 'amount': 170.0, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf14_01'].id},
                {'description': 'Options de collaborateurs', 'amount': 10000, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1962').id, 'contract_id': mapped_contracts['contract_tf14_01'].id},
                {'description': 'Correction avantage en argent', 'amount': 10000, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5110').id, 'contract_id': mapped_contracts['contract_tf14_01'].id},
                {'description': 'Frais de voyage', 'amount': 200, 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6000').id, 'contract_id': mapped_contracts['contract_tf14_01'].id},
                # TF15
                {'description': 'Salaire à la leçon', 'amount': 21, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_lessons').id, 'contract_id': mapped_contracts['contract_tf15_01'].id},
                {'description': 'Frais de voyage', 'amount': 257.5, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6000').id, 'contract_id': mapped_contracts['contract_tf15_01'].id},
                # TF16
                {'contract_id': mapped_contracts['contract_tf16_01'].id, 'amount': 9458.35, 'date_start': date(2021, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1010').id},
                {'contract_id': mapped_contracts['contract_tf16_01'].id, 'amount': 8895, 'date_start': date(2021, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1010').id},
                {'contract_id': mapped_contracts['contract_tf16_02'].id, 'amount': 14350.6, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1010').id},
                {'contract_id': mapped_contracts['contract_tf16_02'].id, 'amount': 10214.45, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1010').id},
                {'description': 'Indemnité spéciale', 'contract_id': mapped_contracts['contract_tf16_01'].id, 'amount': 3000, 'date_start': date(2021, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1212').id},
                {'description': 'Indemnité spéciale', 'contract_id': mapped_contracts['contract_tf16_02'].id, 'amount': 5000, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1212').id},
                {'description': 'Indemnité spéciale', 'contract_id': mapped_contracts['contract_tf16_02'].id, 'amount': 4000, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1212').id},
                {'description': 'Part facultative employeurs IJM','contract_id': mapped_contracts['contract_tf16_01'].id, 'amount': 250, 'date_start': date(2021, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1971').id},
                {'description': '3ème pilier b payé par employeur', 'contract_id': mapped_contracts['contract_tf16_01'].id, 'amount': 150, 'date_start': date(2021, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1977').id},
                {'description': '3ème pilier b payé par employeur', 'contract_id': mapped_contracts['contract_tf16_01'].id, 'amount': 150, 'date_start': date(2021, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1977').id},
                {'description': '3ème pilier b payé par employeur', 'contract_id': mapped_contracts['contract_tf16_02'].id, 'amount': 150, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1977').id},
                {'description': '3ème pilier b payé par employeur', 'contract_id': mapped_contracts['contract_tf16_02'].id, 'amount': 150, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1977').id},
                {'description': '3ème pilier a payé par employeur','contract_id': mapped_contracts['contract_tf16_01'].id, 'amount': 350, 'date_start': date(2021, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1978').id},
                {'description': '3ème pilier a payé par employeur','contract_id': mapped_contracts['contract_tf16_01'].id, 'amount': 350, 'date_start': date(2021, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1978').id},
                {'description': '3ème pilier a payé par employeur','contract_id': mapped_contracts['contract_tf16_02'].id, 'amount': 350, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1978').id},
                {'description': '3ème pilier a payé par employeur','contract_id': mapped_contracts['contract_tf16_02'].id, 'amount': 350, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1978').id},
                {'contract_id': mapped_contracts['contract_tf16_01'].id, 'amount': 500, 'date_start': date(2021, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5110').id},
                {'contract_id': mapped_contracts['contract_tf16_01'].id, 'amount': 750, 'date_start': date(2021, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5110').id},
                {'contract_id': mapped_contracts['contract_tf16_02'].id, 'amount': 500, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5110').id},
                {'contract_id': mapped_contracts['contract_tf16_02'].id, 'amount': 500, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_5110').id},
                {'contract_id': mapped_contracts['contract_tf16_01'].id, 'amount': 300, 'date_start': date(2021, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6000').id},
                {'contract_id': mapped_contracts['contract_tf16_01'].id, 'amount': 300, 'date_start': date(2021, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6000').id},
                {'contract_id': mapped_contracts['contract_tf16_02'].id, 'amount': 600, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6000').id},
                {'contract_id': mapped_contracts['contract_tf16_02'].id, 'amount': 300, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6000').id},
                # TF17
                {'contract_id': mapped_contracts['contract_tf17_01'].id, 'amount': 2000, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1210').id, 'description': 'Bonus'},

                # TF18
                {'description': 'Salaire horaire', 'amount': 35.0, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Salaire horaire', 'amount': 35.0, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Salaire horaire', 'amount': 35.0, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Salaire horaire', 'amount': 35.0, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Salaire horaire', 'amount': 35.0, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Salaire horaire', 'amount': 35.0, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Salaire horaire', 'amount': 35.0, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Salaire horaire', 'amount': 35.0, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Salaire horaire', 'amount': 75, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Salaire horaire', 'amount': 62, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Salaire horaire', 'amount': 53, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Salaire horaire', 'amount': 71, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Salaire horaire', 'amount': 35, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Salaire horaire', 'amount': 35, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Activity Rate', 'amount': 19.23, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ACTIVITYRATE').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Activity Rate', 'amount': 19.23, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ACTIVITYRATE').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Activity Rate', 'amount': 19.23, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ACTIVITYRATE').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Activity Rate', 'amount': 19.23, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ACTIVITYRATE').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Activity Rate', 'amount': 19.23, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ACTIVITYRATE').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Activity Rate', 'amount': 19.23, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ACTIVITYRATE').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Activity Rate', 'amount': 19.23, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ACTIVITYRATE').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Activity Rate', 'amount': 19.23, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ACTIVITYRATE').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Activity Rate', 'amount': 41.21, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ACTIVITYRATE').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Activity Rate', 'amount': 34.07, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ACTIVITYRATE').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Activity Rate', 'amount': 29.12, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ACTIVITYRATE').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Activity Rate', 'amount': 39.01, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ACTIVITYRATE').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Activity Rate', 'amount': 19.23, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ACTIVITYRATE').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                {'description': 'Activity Rate', 'amount': 19.23, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ACTIVITYRATE').id, 'contract_id': mapped_contracts['contract_tf18_01'].id},
                # TF19
                # TF20
                {'description': 'Indemnité de départ (soumis AVS)', 'amount': 500, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1401').id, 'contract_id': mapped_contracts['contract_tf20_01'].id},
                {'description': '13e Mois', 'amount': 416.65, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1200').id, 'contract_id': mapped_contracts['contract_tf20_01'].id},
                # TF21
                {'description': 'Indemnité de départ (soumis AVS)', 'contract_id': mapped_contracts['contract_tf21_01'].id, 'amount': 500, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1401').id,},
                {'description': '13e Mois', 'amount': 416.65, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1200').id, 'contract_id': mapped_contracts['contract_tf21_01'].id},

                # TF22
                {'description': 'Salaire horaire', 'amount': 130.0, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf22_01'].id},
                {'description': 'Salaire horaire', 'amount': 120.0, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf22_01'].id},
                {'description': 'Salaire horaire', 'amount': 125.0, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf22_01'].id},
                {'description': 'Salaire horaire', 'amount': 135.0, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf22_01'].id},
                {'description': 'Salaire horaire', 'amount': 115.0, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf22_01'].id},
                {'description': 'Salaire horaire', 'amount': 100.0, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf22_01'].id},
                {'description': 'Salaire horaire', 'amount': 140.0, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf22_01'].id},
                {'description': 'Salaire horaire', 'amount': 115.0, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf22_01'].id},
                {'description': 'Salaire horaire', 'amount': 130.0, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf22_01'].id},
                {'description': 'Salaire horaire', 'amount': 90.0, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf22_01'].id},
                {'description': 'Salaire horaire', 'amount': 120.0, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf22_01'].id},
                {'description': 'Salaire horaire', 'amount': 130.0, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf22_01'].id},
                {'description': 'Salaire horaire', 'amount': 40.0, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf22_01'].id},
                {'description': 'Salaire horaire', 'amount': 96.0, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_hours').id, 'contract_id': mapped_contracts['contract_tf22_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 200, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf22_01'].id},
                {'description': 'Allocation de naissance', 'amount': 3000, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3034').id, 'contract_id': mapped_contracts['contract_tf22_01'].id},
                # TF23
                {'description': 'Bonus', 'amount': 30000, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1210').id, 'contract_id': mapped_contracts['contract_tf23_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 200, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf23_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 200, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf23_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 200, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf23_01'].id},
                # TF25
                {'description': "CH Days", 'amount': 10, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf25_01'].id},
                {'description': "CH Days", 'amount': 9, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf25_01'].id},
                {'description': "CH Days", 'amount': 18, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf25_01'].id},
                {'description': "CH Days", 'amount': 10, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf25_01'].id},
                {'description': "Monthly Salary", 'amount': 8000, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1000').id, 'contract_id': mapped_contracts['contract_tf25_01'].id},
                {'description': '13e Mois', 'amount': 4166.65, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1200').id, 'contract_id': mapped_contracts['contract_tf25_01'].id},

                # TF26
                {'description': "CH Days", 'amount': 10, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf26_01'].id},
                {'description': "CH Days", 'amount': 9, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf26_01'].id},
                {'description': "CH Days", 'amount': 18, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf26_01'].id},
                {'description': "CH Days", 'amount': 0, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf26_01'].id},
                {'description': "CH Days", 'amount': 7, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf26_01'].id},
                {'description': "Monthly Salary", 'amount': 8000, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1000').id, 'contract_id': mapped_contracts['contract_tf26_01'].id},
                {'description': '13e Mois', 'amount': 4166.65, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1200').id, 'contract_id': mapped_contracts['contract_tf26_01'].id},

                # TF27
                {'description': 'Bonus', 'amount': 30000, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1210').id, 'contract_id': mapped_contracts['contract_tf27_01'].id},
                # TF28
                {'description': "Prime pour proposition d'amélioration", 'amount': 20000, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1216').id, 'contract_id': mapped_contracts['contract_tf28_01'].id},
                {'description': 'Heures supplémentaires après le départ', 'amount': 2000, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_1067').id, 'contract_id': mapped_contracts['contract_tf28_01'].id},
                {'description': 'Paiement des vacances après le départ', 'amount': 3000, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1163').id, 'contract_id': mapped_contracts['contract_tf28_01'].id},
                {'description': "Paiement de la prime l'année précédente", 'amount': 15000, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_1209').id, 'contract_id': mapped_contracts['contract_tf28_01'].id},
                {'description': "CH Days", 'amount': 15, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf28_01'].id},
                {'description': "CH Days", 'amount': 10, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf28_01'].id},
                {'description': "CH Days", 'amount': 11, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf28_01'].id},
                {'description': "CH Days", 'amount': 14, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf28_01'].id},
                {'description': "CH Days", 'amount': 11, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf28_01'].id},
                {'description': "CH Days", 'amount': 8, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf28_01'].id},
                {'description': "CH Days", 'amount': 13, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf28_01'].id},
                {'description': "CH Days", 'amount': 7, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf28_01'].id},
                {'description': "CH Days", 'amount': 16, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf28_01'].id},
                {'description': "CH Days", 'amount': 9, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf28_01'].id},
                # TF29
                {'description': 'Correction des salaires', 'amount': 2000, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1001').id, 'contract_id': mapped_contracts['contract_tf29_01'].id},
                {'description': 'Heures supplémentaires après le départ', 'amount': 2000, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_1067').id, 'contract_id': mapped_contracts['contract_tf29_01'].id},
                {'description': 'Paiement des vacances après le départ', 'amount': 3000, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1163').id, 'contract_id': mapped_contracts['contract_tf29_01'].id},
                {'description': "Paiement de la prime l'année précédente", 'amount': 15000, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_1209').id, 'contract_id': mapped_contracts['contract_tf29_01'].id},
                {'description': "Prime pour proposition d'amélioration", 'amount': 20000, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1216').id, 'contract_id': mapped_contracts['contract_tf29_01'].id},
                {'description': "CH Days", 'amount': 15, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf29_01'].id},
                {'description': "CH Days", 'amount': 10, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf29_01'].id},
                {'description': "CH Days", 'amount': 11, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf29_01'].id},
                {'description': "CH Days", 'amount': 14, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf29_01'].id},
                {'description': "CH Days", 'amount': 11, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf29_01'].id},
                {'description': "CH Days", 'amount': 8, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf29_01'].id},
                {'description': "CH Days", 'amount': 13, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf29_01'].id},
                {'description': "CH Days", 'amount': 7, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf29_01'].id},
                {'description': "CH Days", 'amount': 16, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf29_01'].id},
                {'description': "CH Days", 'amount': 9, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf29_01'].id},
                # TF30
                {'description': 'Paiement des vacances', 'amount': 500, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1162').id, 'contract_id': mapped_contracts['contract_tf30_01'].id},
                {'description': 'Droits de participation imposables', 'amount': 5500, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1960').id, 'contract_id': mapped_contracts['contract_tf30_01'].id},
                {'description': 'Droits de participation imposables', 'amount': 5500, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1960').id, 'contract_id': mapped_contracts['contract_tf30_01'].id},
                {'description': 'Droits de participation imposables', 'amount': 5500, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1960').id, 'contract_id': mapped_contracts['contract_tf30_01'].id},
                {'description': 'Droits de participation imposables', 'amount': 5500, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1960').id, 'contract_id': mapped_contracts['contract_tf30_01'].id},
                # TF33
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf33_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf33_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf33_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf33_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf33_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf33_01'].id},
                {'description': 'Paiement pour Allocation pour enfant', 'amount': 690, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3001').id, 'contract_id': mapped_contracts['contract_tf33_01'].id},
                # TF34
                {'description': 'Allocation pour enfant', 'amount': 200, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf34_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 200, 'date_start': date(2022, 8, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf34_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 200, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf34_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 200, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf34_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 200, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf34_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 200, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf34_01'].id},
                {'description': 'Paiement pour Allocation pour enfant', 'amount': 600, 'date_start': date(2022, 7, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3001').id, 'contract_id': mapped_contracts['contract_tf34_01'].id},
                # TF35
                {'description': "Paiement de la prime l'année précédente", 'amount': 30000, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_1209').id, 'contract_id': mapped_contracts['contract_tf35_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf35_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf35_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf35_01'].id},
                # TF36
                {'description': "Paiement de la prime l'année précédente", 'amount': 30000, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_1209').id, 'contract_id': mapped_contracts['contract_tf36_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 200, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf36_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 200, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf36_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 200, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf36_01'].id},
                # TF37
                {'description': 'Bonus', 'amount': 2000, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1210').id, 'contract_id': mapped_contracts['contract_tf37_02'].id},
                {'description': 'Cotisations LPP', 'amount': 175*2, 'date_start': date(2021, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_5050').id, 'contract_id': mapped_contracts['contract_tf37_01'].id},
                {'description': 'Cotisations LPP', 'amount': 175*2, 'date_start': date(2021, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_5050').id, 'contract_id': mapped_contracts['contract_tf37_02'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2021, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf37_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2021, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf37_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2021, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf37_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf37_02'].id},
                {'description': 'Cotisations LPP', 'amount': 362, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_5050').id, 'contract_id': mapped_contracts['contract_tf37_02'].id},
                {'description': "Monthly Salary", 'amount': 3000, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1000').id, 'contract_id': mapped_contracts['contract_tf37_02'].id},
                # TF38
                {'description': 'Commission', 'amount': 5000, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1218').id, 'contract_id': mapped_contracts['contract_tf38_01'].id},
                {'description': 'Commission', 'amount': 6500, 'date_start': date(2022, 6, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1218').id, 'contract_id': mapped_contracts['contract_tf38_01'].id},
                {'description': 'Commission', 'amount': 3800, 'date_start': date(2022, 9, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1218').id, 'contract_id': mapped_contracts['contract_tf38_01'].id},
                {'description': 'Commission', 'amount': 5500, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1218').id, 'contract_id': mapped_contracts['contract_tf38_01'].id},
                {'description': 'Frais forfaitaires de voiture', 'amount': 300, 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_6050').id, 'contract_id': mapped_contracts['contract_tf38_01'].id},
                # TF39
                {'description': 'Honoraires CA', 'amount': 10000, 'date_start': date(2022, 4, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1500').id, 'contract_id': mapped_contracts['contract_tf39_01'].id},
                # TF40
                {'description': 'Indemnité pour service de piquet', 'amount': 30500, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1071').id, 'contract_id': mapped_contracts['contract_tf40_03'].id},
                {'description': 'Indemnité spéciale', 'amount': 20000, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1212').id, 'contract_id': mapped_contracts['contract_tf40_01'].id},
                {'description': 'Indemnité spéciale', 'amount': 500, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1212').id, 'contract_id': mapped_contracts['contract_tf40_03'].id},
                {'description': 'Honoraires CA', 'amount': 300, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1500').id, 'contract_id': mapped_contracts['contract_tf40_01'].id},
                {'description': 'Honoraires CA', 'amount': 4000, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1500').id, 'contract_id': mapped_contracts['contract_tf40_01'].id},
                {'description': 'Honoraires CA', 'amount': 6150, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1500').id, 'contract_id': mapped_contracts['contract_tf40_03'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf40_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf40_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 230, 'date_start': date(2022, 3, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf40_01'].id},
                {'description': 'Allocation pour enfant', 'amount': 300, 'date_start': date(2022, 10, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf40_02'].id},
                {'description': 'Allocation pour enfant', 'amount': 300, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf40_03'].id},
                {'description': 'Allocation pour enfant', 'amount': 300, 'date_start': date(2023, 1, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf40_03'].id},
                {'description': 'Allocation pour enfant', 'amount': 300, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000').id, 'contract_id': mapped_contracts['contract_tf40_03'].id},
                # TF41
                {'description': 'Gratification', 'amount': 20000, 'date_start': date(2022, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1204').id, 'contract_id': mapped_contracts['contract_tf41_01'].id},
                {'description': 'Cadeau pour ancienneté de service', 'amount': 30000, 'date_start': date(2022, 5, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1230').id, 'contract_id': mapped_contracts['contract_tf41_01'].id},
                # TF42
                {'description': 'Bonus', 'amount': 30000, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1210').id, 'contract_id': mapped_contracts['contract_tf42_01'].id},
                {'description': "CH Days", 'amount': 12, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf42_01'].id},
                {'description': "CH Days", 'amount': 8, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf42_01'].id},
                # TF43
                {'description': 'Bonus', 'amount': 30000, 'date_start': date(2023, 2, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_1210').id, 'contract_id': mapped_contracts['contract_tf43_01'].id},
                {'description': "CH Days", 'amount': 12, 'date_start': date(2022, 11, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf43_01'].id},
                {'description': "CH Days", 'amount': 8, 'date_start': date(2022, 12, 1), 'input_type_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_ISWORKEDDAYSINCH').id, 'contract_id': mapped_contracts['contract_tf43_01'].id},
            ])

        with freeze_time("2021-11-26"):
            cls.nov_11_batch = cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2021, 11, 1))
            mapped_employees['employee_tf14'].write(
                {'l10n_ch_tax_scale_type': 'CategoryPredefined', 'l10n_ch_pre_defined_tax_scale': 'NON'})

            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 11/2021",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.ema.declaration'].create({
                "name": "EMA 11/2021",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.is.report'].create({
                "name": f"Monthly Total {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.statistic.report'].create({
                "name": f"Statistic {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        with freeze_time("2021-12-26"):
            mapped_employees['employee_tf14'].write(
                {'l10n_ch_residence_category': 'settled-C'})
            mapped_employees['employee_tf14'].l10n_ch_salary_certificate_profiles.write({
                "l10n_ch_source_tax_settlement_letter": False,
            })
            mapped_contracts['contract_tf37_02'].write({
                'state': 'open'
            })
            mapped_contracts['contract_tf40_03'].write({
                'state': 'open'
            })

            correction_9 = cls.env['hr.employee.is.line'].create(
                {'employee_id': mapped_employees['employee_tf14'].id,
                 'valid_as_of': date(2021, 11, 1),
                 'correction_type': 'aci',
                 'payslips_to_correct': [(6, 0, [cls.env['hr.payslip'].search([('employee_id', '=', mapped_employees['employee_tf14'].id), ('date_from', '=', date(2021, 11, 1))]).id])],
                 'is_ema_ids': [Command.create({"employee_id": mapped_employees["employee_tf14"].id, "reason": "withdrawalSettled", "valid_as_of": date(2021, 11, 1)})]
                 })
            cls.env.flush_all()
            correction_9.action_pending()

            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2021, 12, 1))

            mapped_contracts["contract_tf07_01"].write({
                "l10n_ch_lpp_not_insured": True,
                "l10n_ch_lpp_withdrawal_reason": "retirement",
                "l10n_ch_lpp_withdrawal_valid_as_of": date(2021, 12, 31)
            })
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 12/2021",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.ema.declaration'].create({
                "name": "EMA 12/2021",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.is.report'].create({
                "name": f"Monthly Total {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.statistic.report'].create({
                "name": f"Statistic {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
            mapped_employees['employee_tf14'].write(
                {'l10n_ch_has_withholding_tax': False})

        with freeze_time("2022-01-26"):

            for key, c in mapped_contracts.items():
                if c.l10n_ch_social_insurance_id.id == avs_1.id and (c.date_start >= date(2022, 1, 1) or not c.date_end or c.date_end >= date(2022, 1, 1)):
                    c.write({
                        "l10n_ch_social_insurance_id": avs_2.id
                    })
                if c.l10n_ch_compensation_fund_id.id == caf_be_1.id and (c.date_start >= date(2022, 1, 1) or not c.date_end or c.date_end >= date(2022, 1, 1)):
                    c.write({
                        "l10n_ch_compensation_fund_id": caf_be_2.id
                    })
                if c.l10n_ch_compensation_fund_id.id == caf_lu_1.id and (c.date_start >= date(2022, 1, 1) or not c.date_end or c.date_end >= date(2022, 1, 1)):
                    c.write({
                        "l10n_ch_compensation_fund_id": caf_lu_2.id
                    })
            mapped_contracts["contract_tf16_02"].write({
                "state": "open"
            })
            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 1, 1))
            mapped_payslips['payslip_tf07_2022_01'] = cls._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf07_01'], date(2022, 1, 1), date(2022, 1, 31), company=company.id, after_payment="N")
            mapped_employees['employee_tf16'].l10n_ch_salary_certificate_profiles.write({
                "l10n_ch_cs_additional_text": "Testfall 16 - Rectificate",
            })
            mapped_declarations['rectificate_2022_01'] = cls.env['l10n.ch.salary.certificate'].create({
                "company_id": company.id,
                "year": datetime.now().year,
                "month": str(datetime.now().month),
                "name": "Aebi Anna Rectificate",
                "previous_declaration": mapped_declarations['yearly_retrospective_2021_12'].id,
                "original_date": date(2021, 12, 31),
                "tax_rectificate_type": "individual",
                "tax_rectificate_employee_ids": [(6, 0, [mapped_employees['employee_tf16'].id])]
            })

            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 01/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.ema.declaration'].create({
                "name": "EMA 01/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.is.report'].create({
                "name": f"Monthly Total {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.statistic.report'].create({
                "name": f"Statistic {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations['rectificate_2022_01'].action_prepare_data()
            cls.env.flush_all()

            mapped_employees['employee_tf16'].l10n_ch_salary_certificate_profiles.write({
                "l10n_ch_cs_additional_text": "",
            })


        with freeze_time("2022-02-26"):
            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 2, 1))
            mapped_payslips['payslip_tf07_2022_02'] = cls._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf07_01'], date(2022, 2, 1), date(2022, 2, 28), company=company.id, after_payment="N")

            mapped_contracts["contract_tf03_01"].write({
                "l10n_ch_lpp_not_insured": True,
                "l10n_ch_lpp_withdrawal_reason": "retirement",
                "l10n_ch_lpp_withdrawal_valid_as_of": date(2022, 2, 28)
            })
            mapped_contracts['contract_tf40_01'].write({'l10n_ch_lpp_not_insured': True})
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 02/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.ema.declaration'].create({
                "name": "EMA 02/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.is.report'].create({
                "name": f"Monthly Total {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.statistic.report'].create({
                "name": f"Statistic {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()

            cls.env.flush_all()
        with freeze_time("2022-03-26"):
            mapped_contracts["contract_tf03_01"].write({
                'resource_calendar_id': resource_calendar_8_4_hours_per_week.id,
                'wage': 1500,
                'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '3',
                'l10n_ch_additional_accident_insurance_line_ids': [(6, 0, [laac_10.id])],
                'l10n_ch_sickness_insurance_line_ids': [(6, 0, [ijm_11.id])],
                'l10n_ch_avs_status': 'retired',
                'l10n_ch_weekly_hours': 8.4
            })

            mapped_contracts["contract_tf13_01"].write({
                'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1',
                'l10n_ch_additional_accident_insurance_line_ids': [(6, 0, [laac_11.id])],
            })

            mapped_contracts["contract_tf16_02"].write({
                'l10n_ch_additional_accident_insurance_line_ids': [(6, 0, [laac_11.id])],
            })

            mapped_contracts["contract_tf40_01"].write({
                'irregular_working_time': True,
                "wage_type": "NoTimeConstraint",
                'l10n_ch_contractual_holidays_rate': 0,
                'l10n_ch_contractual_public_holidays_rate': 0,
                'l10n_ch_thirteen_month': False,
                **administrative,
                'wage': 0,
                'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '0',
                'l10n_ch_additional_accident_insurance_line_ids': [(6, 0, [laac_10.id])],
                'l10n_ch_sickness_insurance_line_ids': [(6, 0, [ijm_10.id])],
                'l10n_ch_lpp_not_insured': True,
                'l10n_ch_lpp_withdrawal_reason': 'interruptionOfEmployment',
                'l10n_ch_lpp_withdrawal_valid_as_of': date(2022, 2, 28)
            })

            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 3, 1))

            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 03/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.ema.declaration'].create({
                "name": "EMA 03/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.is.report'].create({
                "name": f"Monthly Total {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.statistic.report'].create({
                "name": f"Statistic {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
            mapped_employees['employee_tf19'].write({
                'l10n_ch_other_employment': False,
                'l10n_ch_other_activity_percentage': 0
            })
        with freeze_time("2022-04-26"):
            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 4, 1))

            mapped_employees['employee_tf30'].write(
                {'private_street': 'Junkerngasse 42', 'private_zip': '3011', 'private_city': 'Bern',
                 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 351, 'l10n_ch_canton': 'BE',
                 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'l10n_ch_tax_scale_type': 'TaxAtSourceCode',
                 'l10n_ch_tax_scale': 'A'})
            mapped_employees['employee_tf25'].write(
                {'private_street': 'Hauptstrasse 4', 'private_zip': '6102', 'private_city': 'Malters',
                 'private_country_id': cls.env.ref('base.ch').id, 'l10n_ch_municipality': 1062,
                 'l10n_ch_residence_category': 'annual-B', "l10n_ch_canton": "LU"})

            mapped_contracts["contract_tf05_01"].write({
                "l10n_ch_lpp_not_insured": True,
                "l10n_ch_lpp_withdrawal_reason": "retirement",
                "l10n_ch_lpp_withdrawal_valid_as_of": date(2022, 4, 30)
            })

            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 04/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.ema.declaration'].create({
                "name": "EMA 04/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.is.report'].create({
                "name": f"Monthly Total {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.statistic.report'].create({
                "name": f"Statistic {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        with freeze_time("2022-05-26"):

            mapped_contracts["contract_tf05_01"].write({
                'l10n_ch_avs_status': 'retired',
                'l10n_ch_lpp_not_insured': True,
                'l10n_ch_lpp_withdrawal_reason': 'retirement',
                'l10n_ch_lpp_withdrawal_valid_as_of': date(2022, 4, 30)
            })
            mapped_contracts["contract_tf30_01"].write({
                "wage_type": "monthly", "l10n_ch_has_monthly": True,
                **cdi_month,
                'irregular_working_time': False,
                'l10n_ch_weekly_hours': 40,
                'wage': 5500,
                'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1',
                'l10n_ch_additional_accident_insurance_line_ids': [(6, 0, [laac_11.id])],
                'l10n_ch_sickness_insurance_line_ids': [(6, 0, [ijm_11.id])],
                'l10n_ch_is_predefined_category': False
            })

            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 5, 1))
            mapped_payslips['payslip_tf01_2022_05'] = cls._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf01_01'], date(2022, 5, 1), date(2022, 5, 31), company=company.id, after_payment="N")
            mapped_payslips['payslip_tf41_2022_05'] = cls._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf41_01'], date(2022, 5, 1), date(2022, 5, 31), company=company.id, after_payment='N')

            mapped_employees['employee_tf35'].write(
                {'l10n_ch_tax_scale': 'B', "marital": "married", 'l10n_ch_marital_from': date(2022, 5, 25)})
            mapped_employees['employee_tf36'].write(
                {'l10n_ch_tax_scale': 'B', "marital": "married", 'l10n_ch_marital_from': date(2022, 5, 25)})

            mapped_employees['employee_tf23'].write(
                {'marital': 'married', 'l10n_ch_marital_from': date(2022, 5, 8), 'l10n_ch_tax_scale': 'B'})

            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 05/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.ema.declaration'].create({
                "name": "EMA 05/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.is.report'].create({
                "name": f"Monthly Total {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.statistic.report'].create({
                "name": f"Statistic {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        with freeze_time("2022-06-26"):
            mapped_contracts["contract_tf11_01"].write({
                "resource_calendar_id": resource_calendar_42_hours_per_week.id,
                "wage": 30000,
                "l10n_ch_weekly_hours": 42,
                "lpp_employee_amount": 2514,
            })
            mapped_employees['employee_tf31'].write(
                {"l10n_ch_tax_scale": 'B', 'marital': 'married', 'l10n_ch_marital_from': date(2022, 3, 26)})

            correction_1 = cls.env['hr.employee.is.line'].create(
                {'employee_id': mapped_employees['employee_tf31'].id,
                 'payslips_to_correct': [(6, 0, cls.env['hr.payslip'].search([('employee_id', '=', mapped_employees['employee_tf31'].id), ('date_from', 'in', [date(2022, 4, 1), date(2022, 5, 1)])]).ids)],
                 'is_ema_ids': [Command.create({"employee_id": mapped_employees["employee_tf31"].id, "reason": "civilstate", "valid_as_of": date(2022, 4, 1)})]
                 })
            mapped_employees['employee_tf33'].write(
                {"l10n_ch_tax_scale": 'B', 'marital': 'married', 'l10n_ch_marital_from': date(2022, 3, 26)})

            correction_2 = cls.env['hr.employee.is.line'].create(
                {'employee_id': mapped_employees['employee_tf33'].id,
                 'payslips_to_correct': [(6, 0, cls.env['hr.payslip'].search([('employee_id', '=', mapped_employees['employee_tf33'].id), ('date_from', 'in', [date(2022, 4, 1), date(2022, 5, 1)])]).ids)],
                 'is_ema_ids': [Command.create({"employee_id": mapped_employees["employee_tf33"].id, "reason": "civilstate", "valid_as_of": date(2022, 4, 1)})]
                 })
            mapped_employees['employee_tf34'].write(
                {"l10n_ch_tax_scale": 'B', 'marital': 'married', 'l10n_ch_marital_from': date(2022, 3, 26)})

            correction_3 = cls.env['hr.employee.is.line'].create(
                {'employee_id': mapped_employees['employee_tf34'].id,
                 'payslips_to_correct': [(6, 0, cls.env['hr.payslip'].search([('employee_id', '=', mapped_employees['employee_tf34'].id), ('date_from', 'in', [date(2022, 4, 1), date(2022, 5, 1)])]).ids)],
                 'is_ema_ids': [Command.create({"employee_id": mapped_employees["employee_tf34"].id, "reason": "civilstate", "valid_as_of": date(2022, 4, 1)})]
                 })
            cls.env.flush_all()

            correction_1.action_pending()
            correction_2.action_pending()
            correction_3.action_pending()
            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 6, 1))
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 06/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.ema.declaration'].create({
                "name": "EMA 06/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.is.report'].create({
                "name": f"Monthly Total {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.statistic.report'].create({
                "name": f"Statistic {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        with freeze_time("2022-06-28"):
            mapped_employees['employee_tf22'].write(
                {'marital': 'married', 'l10n_ch_marital_from': date(2022, 6, 26), 'l10n_ch_tax_scale': 'C',
                 "l10n_ch_spouse_residence_canton": "TI", "l10n_ch_spouse_work_start_date": date(2022, 6, 28),  "l10n_ch_spouse_revenues": "work_wage",
                 "l10n_ch_spouse_work_canton": "TI", **tf22_additional_particular})
        with freeze_time("2022-07-26"):

            mapped_contracts['contract_tf24_01'].write({'wage': 11000})
            mapped_contracts['contract_tf41_02'].write({'state': 'open'})
            mapped_employees['employee_tf33'].write({"children": 1,'l10n_ch_children':  [(0, 0, {
                'name': 'Tonino',
                'last_name': 'Châtelain',
                'birthdate': date(2022, 4, 23),
                'deduction_start': date(2022, 5, 1),
                'deduction_end': date(2040, 4, 30),
            })]})
            correction_4 = cls.env['hr.employee.is.line'].create({'employee_id': mapped_employees['employee_tf33'].id,
                                                                  'payslips_to_correct': [(6, 0, cls.env['hr.payslip'].search([('employee_id', '=', mapped_employees['employee_tf33'].id), ('date_from', 'in', [date(2022, 5, 1), date(2022, 6, 1)])]).ids)],
                                                                  'is_ema_ids': [Command.create({"employee_id":mapped_employees[
                                                                      "employee_tf33"].id,
                                                                                                 "reason": "childrenDeduction",
                                                                                                 "valid_as_of": date(
                                                                                                     2022, 5, 1)})]

                                                                  })
            mapped_employees['employee_tf34'].write({"children": 1, 'l10n_ch_children':  [(0, 0, {
                'name': 'Marc',
                'last_name': 'Rinaldi',
                'birthdate': date(2022, 4, 23),
                'deduction_start': date(2022, 5, 1),
                'deduction_end': date(2040, 4, 30),
            })]})
            correction_5 = cls.env['hr.employee.is.line'].create({'employee_id': mapped_employees['employee_tf34'].id,
                                                                  'valid_as_of': date(2022, 5, 1),
                                                                  'payslips_to_correct': [(6, 0, cls.env['hr.payslip'].search([('employee_id', '=', mapped_employees['employee_tf34'].id), ('date_from', 'in', [date(2022, 5, 1), date(2022, 6, 1)])]).ids)],
                                                                  'is_ema_ids': [Command.create({"employee_id":mapped_employees["employee_tf34"].id, "reason": "childrenDeduction",
                                                                                                 "valid_as_of": date(2022, 5, 1)})]})
            cls.env.flush_all()
            correction_4.action_pending()
            correction_5.action_pending()
            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 7, 1))

            mapped_employees['employee_tf36'].write({'l10n_ch_tax_scale': 'C', "l10n_ch_spouse_work_start_date": date(2022, 7, 28), "l10n_ch_spouse_revenues": "work_wage",  "l10n_ch_spouse_work_canton": "TI"})

            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 07/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.ema.declaration'].create({
                "name": "EMA 07/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.is.report'].create({
                "name": f"Monthly Total {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.statistic.report'].create({
                "name": f"Statistic {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()        # 2022-08
        with freeze_time("2022-08-26"):
            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 8, 1))

            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 08/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.ema.declaration'].create({
                "name": "EMA 08/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.is.report'].create({
                "name": f"Monthly Total {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.statistic.report'].create({
                "name": f"Statistic {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        with freeze_time("2022-08-28"):
            mapped_contracts['contract_tf36_01'].write({
                'l10n_ch_location_unit_id': location_unit_4.id,
            })
            mapped_employees['employee_tf36'].write({'private_street': 'Via Milano 26', 'private_zip': '22100', 'private_city': 'Como', 'private_country_id': cls.env.ref('base.it').id,  'l10n_ch_residence_type': 'Daily', 'l10n_ch_municipality': False, 'l10n_ch_canton': 'EX', 'l10n_ch_residence_category': 'crossBorder-G', 'l10n_ch_tax_scale': "T", "l10n_ch_foreign_tax_id": "MLDFBA88H17C933G", "place_of_birth": "Como", "l10n_ch_cross_border_start": date(2023, 9, 1), "l10n_ch_cross_border_commuter": True,})
            cls.env.flush_all()
            mapped_employees['employee_tf35'].write({
                'private_street': "Blockweg 2",
                'private_zip': '3007',
                'private_city': 'Bern',
                'private_country_id': cls.env.ref('base.ch').id,
                'l10n_ch_municipality': '351',
                'l10n_ch_canton': 'BE',
                'l10n_ch_spouse_residence_canton': 'BE',
                'l10n_ch_spouse_street': 'Blockweg 2',
                'l10n_ch_spouse_zip': '3007',
                'l10n_ch_spouse_city': "Bern",
            })
            mapped_contracts["contract_tf35_01"].write({"l10n_ch_location_unit_id": location_unit_2.id})
            cls.env.flush_all()
        with freeze_time("2022-09-26"):

            mapped_contracts['contract_tf14_01'].write({
                'wage_type': "monthly", 'l10n_ch_has_monthly': True, 'l10n_ch_has_hourly': False,
                "l10n_ch_contractual_13th_month_rate": (1/12)*100,
                **internship,
                'wage': 2500.0,
                "l10n_ch_yearly_holidays": 20,
                'l10n_ch_thirteen_month': False,
                'l10n_ch_weekly_hours': 21,
                'irregular_working_time': False
            })
            mapped_contracts['contract_tf18_01'].write({'hourly_wage': 35, "l10n_ch_lesson_wage": 35})
            mapped_contracts['contract_tf35_01'].write({
                'l10n_ch_lpp_insurance_id': lpp_0.id,
                'l10n_ch_is_model': 'monthly',
                'l10n_ch_location_unit_id': location_unit_2.id,
                "l10n_ch_compensation_fund_id": caf_be_2.id,
                "l10n_ch_lpp_solutions": [(6, 0, [lpp_0.solutions_ids[2].id])]

            })
            mapped_contracts['contract_tf36_01'].write({
                'l10n_ch_location_unit_id': location_unit_4.id,
                'l10n_ch_is_model': 'yearly',
                "l10n_ch_compensation_fund_id": caf_ti_2.id,
            })

            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 9, 1))

            mapped_employees['employee_tf36'].write({'l10n_ch_tax_scale': "F",
                                                     "l10n_ch_spouse_work_canton": "EX",
                                                     'l10n_ch_spouse_residence_canton': 'EX',
                                                     'l10n_ch_spouse_street': 'Via Milano 26',
                                                     'l10n_ch_spouse_zip': '22100',
                                                     'l10n_ch_spouse_city': "Como",
                                                     'l10n_ch_spouse_country_id': cls.env.ref('base.it').id,
                                                     })
            mapped_employees['employee_tf24'].write({'l10n_ch_tax_scale': 'C', "l10n_ch_spouse_revenues": "work_wage", "l10n_ch_spouse_work_canton": "TI","l10n_ch_spouse_work_start_date": date(2022, 9, 20), "l10n_ch_spouse_residence_canton": "TI"})
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 09/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.ema.declaration'].create({
                "name": "EMA 09/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.is.report'].create({
                "name": f"Monthly Total {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.statistic.report'].create({
                "name": f"Statistic {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        with freeze_time("2022-09-28"):
            mapped_employees['employee_tf40'].write(
                {'l10n_ch_canton': "VD", 'private_street': 'Rue des Moulins 13', 'private_zip': '1800',
                 'private_city': 'Vevey', 'private_country_id': cls.env.ref('base.ch').id,
                 'l10n_ch_municipality': 5890})
        with freeze_time("2022-10-26"):

            mapped_contracts['contract_tf09_01'].write({'wage': 1000, 'resource_calendar_id': resource_calendar_21_hours_per_week.id, 'l10n_ch_weekly_hours': 21})
            mapped_contracts['contract_tf12_01'].write({'l10n_ch_additional_accident_insurance_line_ids': [(6, 0, [laac_12.id])],
                                                        'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '1',
                                                        "l10n_ch_sickness_insurance_line_ids": [(6, 0, [ijm_12.id])],
                                                        "l10n_ch_compensation_fund_id": caf_be_2.id,
                                                        "wage": 0,
                                                        "l10n_ch_location_unit_id": location_unit_2.id,
                                                        "wage_type": "NoTimeConstraint",
                                                        'l10n_ch_contractual_holidays_rate': 0,
                                                        'l10n_ch_contractual_public_holidays_rate': 0,
                                                        **cdi_fntc,
                                                        "l10n_ch_contractual_13th_month_rate": 8.33,
                                                        "irregular_working_time": True,
                                                        "l10n_ch_compensation_fund_id": caf_be_2.id})

            mapped_contracts['contract_tf02_01'].write({
                "l10n_ch_avs_status": "retired"
            })
            cls.env['l10n.ch.lpp.mutation'].create({"reason": "residence", "valid_as_of": date(2022, 10, 1), "employee_id": mapped_employees["employee_tf40"].id})
            mapped_contracts['contract_tf40_02'].write({'state': 'open'})

            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 10, 1))
            mapped_payslips['payslip_tf01_2022_10'] = cls._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf01_01'], date(2022, 10, 1), date(2022, 10, 31), company=company.id, after_payment="N")

            # 2022-10
            mapped_employees['employee_tf23'].write({
                'l10n_ch_children': [(0, 0, {
                    'name': 'Sven',
                    'last_name': 'Koller',
                    'birthdate': date(2022, 10, 9),
                    'deduction_start': date(2022, 11, 1),
                    'deduction_end': date(2040, 10, 31),
                })]})


            mapped_employees['employee_tf23'].write({'children': 1})
            mapped_employees['employee_tf35'].write({"children": 1, 'l10n_ch_children':  [(0, 0, {
                'name': 'Antonello',
                'last_name': 'Roos',
                'birthdate': date(2022, 10, 10),
                'deduction_start': date(2022, 11, 1),
                'deduction_end': date(2040, 10, 31),
            })]})
            mapped_employees['employee_tf36'].write({"children": 1,
                                                     'l10n_ch_children':  [(0, 0, {
                                                         'name': 'Marc',
                                                         'last_name': 'Maldini',
                                                         'birthdate': date(2022, 10, 22),
                                                         'deduction_end': date(2040, 10, 31),
                                                         'deduction_start': date(2022, 11, 1)
                                                     })]})
            mapped_contracts['contract_tf38_01'].write({'l10n_ch_is_predefined_category': "SF"})
            mapped_employees['employee_tf38'].write({"l10n_ch_cross_border_commuter": True, 'l10n_ch_residence_category': 'crossBorder-G', 'l10n_ch_tax_scale_type': 'CategoryPredefined', 'l10n_ch_pre_defined_tax_scale': 'SFN', 'l10n_ch_canton': 'EX', 'l10n_ch_residence_type': 'Daily', 'private_street': 'Grand Rue', 'private_zip': '90100', 'private_city': 'Delle', 'private_country_id': cls.env.ref('base.fr').id})
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 10/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.ema.declaration'].create({
                "name": "EMA 10/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.is.report'].create({
                "name": f"Monthly Total {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.statistic.report'].create({
                "name": f"Statistic {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        with freeze_time("2022-11-26"):
            mapped_employees['employee_tf24'].write({'l10n_ch_residence_category': 'settled-C'})
            mapped_employees['employee_tf10'].l10n_ch_salary_certificate_profiles.write({
                "l10n_ch_provision_salary": True,
                "l10n_ch_provision_salary_first_name": "Stephanie",
                "l10n_ch_provision_salary_last_name": "Ganz",
                "l10n_ch_provision_salary_street": "Neuhofstrasse 47",
                "l10n_ch_provision_salary_zip": "6020",
                "l10n_ch_provision_salary_city": "Emmenbrücke",
                "l10n_ch_provision_salary_country": cls.env.ref('base.ch').id,
            })
            mapped_contracts['contract_tf14_01'].write({'l10n_ch_laa_group': laa_group_A, 'laa_solution_number': '2',})
            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 11, 1))
            mapped_payslips['payslip_tf10_2022_11'] = cls._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf10_01'], date(2022, 11, 1), date(2022, 11, 30), company=company.id, after_payment='N')
            mapped_payslips['payslip_tf30_2022_11'] = cls._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf30_01'], date(2022, 11, 1), date(2022, 11, 30), company=company.id, after_payment='NK')
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 11/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.ema.declaration'].create({
                "name": "EMA 11/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.is.report'].create({
                "name": f"Monthly Total {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.statistic.report'].create({
                "name": f"Statistic {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
            mapped_employees['employee_tf24'].write({'l10n_ch_has_withholding_tax': False})
        with freeze_time("2022-12-26"):
            mapped_employees['employee_tf40'].write({'children': 2, "l10n_ch_tax_specially_approved": True})
            cls.env["l10n.ch.avs.splits"].create({
                "employee_id": mapped_employees["employee_tf09"].id,
                "year": datetime.now().year,
                "additional_delivery_date": date(2023, 2, 14),
                "state": "confirmed"
            })
            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2022, 12, 1))
            mapped_payslips['payslip_tf10_2022_12'] = cls._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf10_01'], date(2022, 12, 1), date(2022, 12, 31), company=company.id, after_payment='N')

            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 12/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.ema.declaration'].create({
                "name": "EMA 12/2022",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.is.report'].create({
                "name": f"Monthly Total {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.statistic.report'].create({
                "name": f"Statistic {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()

            cls.env.flush_all()
        with freeze_time("2022-12-28"):
            mapped_employees['employee_tf32'].write({
                "marital": "married",
                'l10n_ch_marital_from': date(2022, 10, 26),
                "l10n_ch_tax_scale": 'B',
                'l10n_ch_spouse_last_name': "Armanini",
                'l10n_ch_spouse_first_name': "Claudio",
                'l10n_ch_spouse_birthday': date(1976, 9, 18),
                'l10n_ch_spouse_residence_canton': 'BE',
                'l10n_ch_spouse_street': 'Gerberweg 10',
                'l10n_ch_spouse_zip': '2560',
                'l10n_ch_spouse_city': "Nidau",
                'l10n_ch_spouse_country_id': cls.env.ref('base.ch').id,
            })
            correction_7 = cls.env['hr.employee.is.line'].create({'employee_id': mapped_employees['employee_tf32'].id,
                                                                  'valid_as_of': date(2022, 11, 1),
                                                                  'payslips_to_correct': [(6, 0, cls.env['hr.payslip'].search([('employee_id', '=', mapped_employees['employee_tf32'].id), ('date_from', 'in', [date(2022, 11, 1), date(2022, 12, 1)])]).ids)],
                                                                  'is_ema_ids': [Command.create({"employee_id":mapped_employees["employee_tf32"].id, "reason": "civilstate", "valid_as_of": date(2022, 11, 1)})]
                                                                  })
            cls.env.flush_all()
            correction_7.action_pending()
        with freeze_time("2023-01-26"):
            mapped_contracts["contract_tf13_01"].write({
                'l10n_ch_sickness_insurance_line_ids': [(6, 0, [ijm_11.id])],
                'l10n_ch_avs_status': False
            }),
            mapped_contracts["contract_tf27_01"].write({
                'lpp_employee_amount': 875
            })
            mapped_contracts["contract_tf40_03"].write({
                'lpp_employee_amount': 1196,
            })

            mapped_declarations['yearly_prospective_2023_01'] = cls.env['l10n.ch.lpp.basis.report'].create({
                "year": datetime.now().year,
                "month": str(datetime.now().month),
                "company_id": company.id
            })

            mapped_declarations['yearly_prospective_2023_01'].action_prepare_data()

            mapped_declarations['yearly_prospective_2023_01'].lpp_basis_line_ids.filtered(lambda l: l.employee_id.registration_number == "11").write({
                "lpp_declared_basis": 431000.00
            })
            mapped_declarations['yearly_prospective_2023_01'].lpp_basis_line_ids.filtered(lambda l: l.employee_id.registration_number == "18").write({
                "lpp_declared_basis": 20000.00
            })
            mapped_declarations['yearly_prospective_2023_01'].lpp_basis_line_ids.filtered(lambda l: l.employee_id.registration_number == "27").write({
                "lpp_declared_basis": 150000
            })
            mapped_declarations['yearly_prospective_2023_01'].lpp_basis_line_ids.filtered(lambda l: l.employee_id.registration_number == "40").write({
                "lpp_declared_basis": 205000
            })
            mapped_declarations['yearly_prospective_2023_01'].lpp_basis_line_ids.filtered(lambda l: l.employee_id.registration_number == "32").write({
                "lpp_declared_basis": 65000
            })

            # 2023-01
            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2023, 1, 1))
            mapped_payslips['payslip_tf08_2023_01'] = cls._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf08_01'], date(2023, 1, 1), date(2023, 1, 31), company=company.id, after_payment='N')
            mapped_payslips['payslip_tf28_2023_01'] = cls._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf28_01'], date(2023, 1, 1), date(2023, 1, 31), company=company.id, after_payment='NK')
            mapped_payslips['payslip_tf29_2023_01'] = cls._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf29_01'], date(2023, 1, 1), date(2023, 1, 31), company=company.id, after_payment='NK')

            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 01/2023",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.ema.declaration'].create({
                "name": "EMA 01/2023",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.is.report'].create({
                "name": f"Monthly Total {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.statistic.report'].create({
                "name": f"Statistic {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()



            cls.env.flush_all()
        with freeze_time("2023-01-28"):
            mapped_employees['employee_tf29'].write({"l10n_ch_tax_scale": 'A', "l10n_ch_canton": 'BE', 'l10n_ch_municipality': 351, 'l10n_ch_residence_category': 'annual-B', 'private_street': "Laupenstrasse 5", 'private_zip': '3008', 'private_city': 'Bern', 'private_country_id': cls.env.ref('base.ch').id, })
        with freeze_time("2023-02-26"):
            cls._l10n_ch_compute_swissdec_demo_paylips(company, date(2023, 2, 1))
            mapped_payslips['payslip_tf04_2023_02'] = cls._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf04_01'], date(2023, 2, 1), date(2023, 2, 28), company=company.id, after_payment="N")
            mapped_payslips['payslip_tf05_2023_02'] = cls._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf05_01'], date(2023, 2, 1), date(2023, 2, 28), company=company.id, after_payment="N")
            mapped_payslips['payslip_tf06_2023_02'] = cls._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf06_01'], date(2023, 2, 1), date(2023, 2, 28), company=company.id, after_payment="N")
            mapped_payslips['payslip_tf08_2023_02'] = cls._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf08_01'], date(2023, 2, 1), date(2023, 2, 28), company=company.id, after_payment="N")
            mapped_payslips['payslip_tf28_2023_02'] = cls._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf28_01'], date(2023, 2, 1), date(2023, 2, 28), company=company.id, after_payment='N')
            mapped_payslips['payslip_tf29_2023_02'] = cls._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf29_01'], date(2023, 2, 1), date(2023, 2, 28), company=company.id, after_payment='N')
            mapped_payslips['payslip_tf42_2023_02'] = cls._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf42_01'], date(2023, 2, 1), date(2023, 2, 28), company=company.id, after_payment='N')
            mapped_payslips['payslip_tf43_2023_02'] = cls._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf43_01'], date(2023, 2, 1), date(2023, 2, 28), company=company.id, after_payment='N')

            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['ch.yearly.report'].create({
                "name": "Yearly Retrospective 02/2023",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.ema.declaration'].create({
                "name": "EMA 02/2023",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })

            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.is.report'].create({
                "name": f"Monthly Total {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'] = cls.env['l10n.ch.statistic.report'].create({
                "name": f"Statistic {datetime.now().year}/{str(datetime.now().month).zfill(2)}",
                "company_id": company.id,
                "month": str(datetime.now().month),
                "year": datetime.now().year,
            })
            mapped_declarations[f'statistic_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'ema_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'is_declaration_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            mapped_declarations[f'yearly_retrospective_{datetime.now().year}_{str(datetime.now().month).zfill(2)}'].action_prepare_data()
            cls.env.flush_all()
        return mapped_declarations

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        with patch.object(cls.env.registry['l10n.ch.employee.yearly.values'], '_generate_certificate_uuid', lambda self: "#DOC-ID"):
            with patch.object(cls.env.registry['l10n.ch.employee.monthly.values'], '_get_additional_txb_values', lambda self: {}):
                with patch.object(cls.env.registry['l10n.ch.employee.monthly.values'], '_get_additional_avs_values', lambda self, avs_base, avs_status: {}):
                    mapped_declarations = cls._l10n_ch_generate_swissdec_demo_data(cls.muster_ag_company)
        for indentifier, declaration in mapped_declarations.items():
            assert isinstance(indentifier, str)
            setattr(cls, indentifier, declaration)
