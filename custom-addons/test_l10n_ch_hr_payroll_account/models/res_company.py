# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import json

from collections import defaultdict
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import models
from odoo.tools import file_open

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    def _l10n_ch_generate_swissdec_demo_data(self):
        self.ensure_one()
        if self.env['hr.employee'].search([('name', '=', 'Herz Monica'), ('company_id', '=', self.id)], limit=1):
            return

        self.env["res.lang"]._activate_lang("fr_FR")

        self.env['res.company'].search([('name', '=', 'Muster AG')]).write({'name': 'Muster AG (Old)'})
        self.write({
            'name': 'Muster AG',
            'street': 'Bahnhofstrasse 1',
            'zip': '6003',
            'city': 'Luzern',
            'country_id': self.env.ref('base.ch').id,
            'l10n_ch_uid': 'CHE-999.999.996',
            'phone': '0412186532',
        })

        admin = self.env['res.users'].search([('login', '=', 'admin')])
        admin.write({
            'name': 'Hans Muster',
            'email': 'MusterAG@xxxxx.ch',
            'mobile': '041 218 65 32',
        })
        admin.company_ids |= self

        self.env.user.tz = 'Europe/Zurich'

        # Generate Location Units
        LocationUnit = self.env['l10n.ch.location.unit'].with_context(tracking_disable=True)
        location_unit_1 = LocationUnit.create({
            "company_id": self.id,
            "partner_id": self.env['res.partner'].create({
                'name': 'Hauptsitz',  # 'Siège principal - Lucerne',
                'street': 'Bahnhofstrasse 1',
                'zip': '6003',
                'city': 'Luzern',
                'country_id': self.env.ref('base.ch').id,
            }).id,
            "bur_ree_number": "A92978109",
            "canton": 'LU',
            "dpi_number": '158.87.6',
            "municipality": '1061',
            "weekly_hours": 42,
            "weekly_lessons": 21,
        })

        location_unit_2 = LocationUnit.create({
            "company_id": self.id,
            "partner_id": self.env['res.partner'].create({
                'name': 'Werkhof/Büro',  # 'Atelier/Bureau - Berne',
                'street': 'Zeughausgasse 9',
                'zip': '3011',
                'city': 'Bern',
                'country_id': self.env.ref('base.ch').id,
            }).id,
            "bur_ree_number": "A89058593",
            "canton": 'BE',
            "dpi_number": '9217.8',
            "municipality": '351',
            "weekly_hours": 40,
            "weekly_lessons": 20,
        })

        _location_unit_3 = LocationUnit.create({
            "company_id": self.id,
            "partner_id": self.env['res.partner'].create({
                'name': 'Verkauf',  # 'Vente - Vevey',
                'street': 'Rue des Moulins 9',
                'zip': '1800',
                'city': 'Vevey',
                'country_id': self.env.ref('base.ch').id,
            }).id,
            "bur_ree_number": "A89058588",
            "canton": 'VD',
            "dpi_number": '23.957.55.6',
            "municipality": '5890',
            "weekly_hours": 40,
            "weekly_lessons": 20,
        })

        location_unit_4 = LocationUnit.create({
            "company_id": self.id,
            "partner_id": self.env['res.partner'].create({
                'name': 'Beratung',  # 'Consultation - Bellinzone',
                'street': 'Via Canonico Ghiringhelli 19',
                'zip': '6500',
                'city': 'Bellinzona',
                'country_id': self.env.ref('base.ch').id,
            }).id,
            "bur_ree_number": "A92978114",
            "canton": 'TI',
            "dpi_number": '83189.7',
            "municipality": '5002',
            "weekly_hours": 40,
            "weekly_lessons": 20,
        })

        # Generate Resource Calendars
        ResourceCalendar = self.env['resource.calendar'].with_context(tracking_disable=True)
        resource_calendar_40_hours_per_week = ResourceCalendar.create([{
            'name': "Test Calendar : 40 Hours/Week",
            'company_id': self.id,
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
                'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id

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
            'company_id': self.id,
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
                'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id

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
            'company_id': self.id,
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
                'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id

            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 8.0, 12.0, "morning"),
                ("0", 12.0, 13.0, "lunch"),
                ("0", 13.0, 17.4, "afternoon"),
            ]],
        }])

        resource_calendar_24_hours_per_week = ResourceCalendar.create([{
            'name': "Test Calendar : 24 Hours/Week",
            'company_id': self.id,
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
                'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id

            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 8.0, 16.0, "morning"),
                ("1", 8.0, 16.0, "morning"),
                ("2", 8.0, 16.0, "morning"),
            ]],
        }])

        resource_calendar_16_hours_per_week = ResourceCalendar.create([{
            'name': "Test Calendar : 16 Hours/Week",
            'company_id': self.id,
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
                'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id

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
            'company_id': self.id,
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
                'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id

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
            'company_id': self.id,
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
                'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id

            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 8.0, 12.0, "morning"),
                ("0", 12.0, 13.0, "lunch"),
                ("0", 13.0, 17.0, "afternoon"),
                ("1", 8.0, 12.6, "morning"),
            ]],
        }])

        resource_calendar_70_percent = ResourceCalendar.create([{
            'name': "Test Calendar : 42 Hours/Week",
            'company_id': self.id,
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
                'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id

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
            'company_id': self.id,
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
                'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id

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
            'company_id': self.id,
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
                'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id

            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 8.0, 12.0, "morning"),
                ("1", 8.0, 12.0, "morning"),
                ("3", 8.0, 12.0, "morning"),
                ("4", 8.0, 12.0, "morning"),
            ]],
        }])

        resource_calendar_60_percent = ResourceCalendar.create([{
            'name': "Test Calendar : 24 Hours/Week",
            'company_id': self.id,
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
                'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id

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
            'company_id': self.id,
            'hours_per_day': 0,
            'tz': "Europe/Zurich",
            'two_weeks_calendar': False,
            'hours_per_week': 0.0,
            'full_time_required_hours': 0.0,
            'attendance_ids': [(5, 0, 0)],
        }])

        job_1 = self.env['hr.job'].create({'name': 'Informaticienne'})

        # Generate AVS
        avs_1 = self.env['l10n.ch.social.insurance'].create({
            'name': 'AVS 2021',
            'member_number': '7019.2',
            'member_subnumber': '2292490',
            'insurance_company': 'AVS 2021',
            'insurance_code': '079.000',
            'age_start': 18,
            'age_stop_male': 65,
            'age_stop_female': 64,
            'avs_line_ids': [(0, 0, {
                'date_from': date(2021, 1, 1),
                'date_to': date(2023, 12, 31),
                'employer_rate': 5.3,
                'employee_rate': 5.3,
            })],
            'ac_line_ids': [(0, 0, {
                'date_from': date(2021, 1, 1),
                'date_to': date(2023, 12, 31),
                'employer_rate': 1.1,
                'employee_rate': 1.1,
                'employee_additional_rate': 0.5,
                'employer_additional_rate': 0.5,
            })],
            'l10n_ch_avs_rente_ids': [(0, 0, {
                'date_from': date(2021, 1, 1),
                'date_to': date(2023, 12, 31),
                'amount': 1400
            })],
            'l10n_ch_avs_ac_threshold_ids': [(0, 0, {
                'date_from': date(2021, 1, 1),
                'date_to': date(2023, 12, 31),
                'amount': 148200
            })],
            'l10n_ch_avs_acc_threshold_ids': [(0, 0, {
                'date_from': date(2021, 1, 1),
                'date_to': date(2023, 12, 31),
                'amount': 370500
            })]
        })

        avs_2 = self.env['l10n.ch.social.insurance'].create({
            'name': 'AVS 2022',
            'member_number': '100-9976.9',
            'member_subnumber': '2292490',
            'insurance_company': 'AVS 2022',
            'insurance_code': '003.000',
            'age_start': 18,
            'age_stop_male': 65,
            'age_stop_female': 64,
            'avs_line_ids': [(0, 0, {
                'date_from': date(2021, 1, 1),
                'date_to': date(2023, 12, 31),
                'employer_rate': 5.3,
                'employee_rate': 5.3,
            })],
            'ac_line_ids': [(0, 0, {
                'date_from': date(2021, 1, 1),
                'date_to': date(2023, 12, 31),
                'employer_rate': 1.1,
                'employee_rate': 1.1,
                'employee_additional_rate': 0.5,
                'employer_additional_rate': 0.5,
            })],
            'l10n_ch_avs_rente_ids': [(0, 0, {
                'date_from': date(2021, 1, 1),
                'date_to': date(2023, 12, 31),
                'amount': 1400
            })],
            'l10n_ch_avs_ac_threshold_ids': [(0, 0, {
                'date_from': date(2021, 1, 1),
                'date_to': date(2023, 12, 31),
                'amount': 148200
            })],
            'l10n_ch_avs_acc_threshold_ids': [(0, 0, {
                'date_from': date(2021, 1, 1),
                'date_to': date(2023, 12, 31),
                'amount': 370500
            })]
        })

        # Generate LAA
        laa_1_partner = self.env['res.partner'].create({
            'name': "Backwork-Versicherungen",
            'street': "Bahnhofstrasse 7",
            'city': "Luzern",
            'zip': "6003",
            'country_id': self.env.ref('base.ch').id,
            'company_id': self.id,
        })

        laa_1 = self.env['l10n.ch.accident.insurance'].create({
            'name': "Backwork-Versicherungen",
            'customer_number': '12577.2',
            'contract_number': '125',
            'insurance_company': 'Backwork-Versicherungen',
            'insurance_code': 'S1000',
            'insurance_company_address_id': laa_1_partner.id,
            'line_ids': [
                (0, 0, {
                    "solution_name": "Backwork-Versicherungen solution A1",
                    "solution_type": "A",
                    "solution_number": "1",
                    "rate_ids": [(0, 0, {
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
                }),
                (0, 0, {
                    "solution_name": "Backwork-Versicherungen solution A3",
                    "solution_type": "A",
                    "solution_number": "3",
                    "rate_ids": [(0, 0, {
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
                }),
                (0, 0, {
                    "solution_name": "Backwork-Versicherungen solution A0",
                    "solution_type": "A",
                    "solution_number": "0",
                    "rate_ids": [(0, 0, {
                        "date_from": date(2021, 1, 1),
                        "date_to": False,
                        "threshold": 0,
                        "occupational_male_rate": 0,
                        "occupational_female_rate": 0,
                        "non_occupational_male_rate": 0,
                        "non_occupational_female_rate": 0,
                        "employer_occupational_part": "0",
                        "employer_non_occupational_part": "0",
                    })],
                }),
                (0, 0, {
                    "solution_name": "Backwork-Versicherungen solution A2",
                    "solution_type": "A",
                    "solution_number": "2",
                    "rate_ids": [(0, 0, {
                        "date_from": date(2021, 1, 1),
                        "date_to": False,
                        "threshold": 148200,
                        "occupational_male_rate": 0,
                        "occupational_female_rate": 0,
                        "non_occupational_male_rate": 0,
                        "non_occupational_female_rate": 0,
                        "employer_occupational_part": "0",
                        "employer_non_occupational_part": "0",
                    })],
                })
            ],
        })

        laa_A0 = laa_1.line_ids[2]
        laa_A1 = laa_1.line_ids[0]
        laa_A2 = laa_1.line_ids[3]
        laa_A3 = laa_1.line_ids[1]

        # Generate LAAC
        laac_1 = self.env['l10n.ch.additional.accident.insurance'].create({
            'name': 'Backwork-Versicherungen',
            'customer_number': '7651-873.1',
            'contract_number': '4566-4',
            'insurance_company': 'Backwork-Versicherungen',
            'insurance_code': 'S1000',
            'insurance_company_address_id': laa_1_partner.id,
            'line_ids': [
                (0, 0, {
                    'solution_name': 'Group 1, Category 0 - A0',
                    'solution_type': 'A',
                    'solution_number': '0',
                    'rate_ids': [(0, 0, {
                        'date_from': date(2021, 1, 1),
                        'date_to': date(2023, 12, 31),
                        'wage_from': 0,
                        'wage_to': 0,
                        'male_rate': 0,
                        'female_rate': 0,
                        'employer_part': '50',
                    })],
                }),
                (0, 0, {
                    'solution_name': 'Group 1, Category 1 - A1',
                    'solution_type': 'A',
                    'solution_number': '1',
                    'rate_ids': [(0, 0, {
                        'date_from': date(2021, 1, 1),
                        'date_to': date(2023, 12, 31),
                        'wage_from': 0,
                        'wage_to': 148200,
                        'male_rate': 0.774,
                        'female_rate': 0.774,
                        'employer_part': '0',
                    })],
                }),
                (0, 0, {
                    'solution_name': 'Group 1, Category 2 - A2',
                    'solution_type': 'A',
                    'solution_number': '2',
                    'rate_ids': [(0, 0, {
                        'date_from': date(2021, 1, 1),
                        'date_to': date(2023, 12, 31),
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
        ijm_1 = self.env['l10n.ch.sickness.insurance'].create({
            "name": 'Backwork-Versicherungen',
            "customer_number": '7651-873.1',
            "contract_number": '4567-4',
            "insurance_company": 'Backwork-Versicherungen',
            "insurance_code": 'S1000',
            "insurance_company_address_id": laa_1_partner.id,
            "line_ids": [
                (0, 0, {
                    "solution_name": "Group 1, Category 0 - A0",
                    "solution_type": "A",
                    "solution_number": "0",
                    "rate_ids": [(0, 0, {
                        'date_from': date(2021, 1, 1),
                        'date_to': date(2023, 12, 31),
                        "wage_from": 0,
                        "wage_to": 0,
                        "male_rate": 0,
                        "female_rate": 0,
                        "employer_part": '0',
                    })]
                }),
                (0, 0, {
                    "solution_name": "Group 1, Category 1 - A1",
                    "solution_type": "A",
                    "solution_number": "1",
                    "rate_ids": [(0, 0, {
                        'date_from': date(2021, 1, 1),
                        'date_to': date(2023, 12, 31),
                        "wage_from": 0,
                        "wage_to": 120000,
                        "male_rate": 0.9660,
                        "female_rate": 1.3090,
                        "employer_part": '0',
                    })]
                }),
                (0, 0, {
                    "solution_name": "Group 1, Category 2 - A2",
                    "solution_type": "A",
                    "solution_number": "2",
                    "rate_ids": [(0, 0, {
                        'date_from': date(2021, 1, 1),
                        'date_to': date(2023, 12, 31),
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
        lpp_partner = self.env['res.partner'].create({
            'name': "Pensionskasse Oldsoft",
            'street': "Fellerstrasse 23",
            'city': "Bern",
            'zip': "3027",
            'country_id': self.env.ref('base.ch').id,
            'company_id': self.id,
        })

        lpp_0 = self.env['l10n.ch.lpp.insurance'].create({
            "name": 'LPP No Fund',
            "customer_number": '1099-8777.1',
            "contract_number": '4500-0',
            'insurance_company': 'Pensionskasse Oldsoft',
            'insurance_code': 'L1200',
            "insurance_company_address_id": lpp_partner.id,
            "fund_number": False,
        })

        lpp_1 = self.env['l10n.ch.lpp.insurance'].create({
            "name": 'LPP Production',
            "customer_number": '1099-8777.1',
            "contract_number": '4500-0',
            'insurance_company': 'Pensionskasse Oldsoft',
            'insurance_code': 'L1200',
            "insurance_company_address_id": lpp_partner.id,
            "fund_number": '11',
        })

        lpp_2 = self.env['l10n.ch.lpp.insurance'].create({
            "name": 'LPP Sales',
            "customer_number": '1099-8777.1',
            "contract_number": '4500-0',
            'insurance_company': 'Pensionskasse Oldsoft',
            'insurance_code': 'L1200',
            "insurance_company_address_id": lpp_partner.id,
            "fund_number": '21',
        })

        lpp_3 = self.env['l10n.ch.lpp.insurance'].create({
            "name": 'LPP Admin',
            "customer_number": '1099-8777.1',
            "contract_number": '4500-0',
            'insurance_company': 'Pensionskasse Oldsoft',
            'insurance_code': 'L1200',
            "insurance_company_address_id": lpp_partner.id,
            "fund_number": '22',
        })

        lpp_4 = self.env['l10n.ch.lpp.insurance'].create({
            "name": 'LPP Cadres Surobligatoire',
            "customer_number": '1099-8777.1',
            "contract_number": '4500-0',
            'insurance_company': 'Pensionskasse Oldsoft',
            'insurance_code': 'L1200',
            "insurance_company_address_id": lpp_partner.id,
            "fund_number": 'K2010',
        })

        # Generate CAF
        caf_lu_1 = self.env['l10n.ch.compensation.fund'].create({
            "name": 'Spida',
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

        caf_lu_2 = self.env['l10n.ch.compensation.fund'].create({
            "name": 'Familienausgleichskassen Kanton Luzern',
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

        caf_be_1 = self.env['l10n.ch.compensation.fund'].create({
            "name": 'Spida',
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

        caf_be_2 = self.env['l10n.ch.compensation.fund'].create({
            "name": 'Familienausgleichskasse Kanton Bern',
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

        _caf_vd_1 = self.env['l10n.ch.compensation.fund'].create({
            "name": 'Spida',
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

        _caf_vd_2 = self.env['l10n.ch.compensation.fund'].create({
            "name": 'Caisse cantonale vaudoise de compensation',
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

        caf_ti_1 = self.env['l10n.ch.compensation.fund'].create({
            "name": 'Spida',
            "member_number": '',
            "member_subnumber": '',
            "insurance_company": 'Spida',
            "insurance_code": '',
            "caf_line_ids": [(0, 0, {
                'date_from': date(2021, 1, 1),
                'date_to': False,
                'employee_rate': 0,
                'company_rate': 0,
            })],
        })

        _caf_ti_2 = self.env['l10n.ch.compensation.fund'].create({
            "name": 'Istituto delle assicurazioni sociali',
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
            'lpp_insurance_id': lpp_1.id,
            'lpp_insurance_from': date(2021, 1, 1),
        })

        avs_2.write({
            'laa_insurance_id': laa_1.id,
            'laa_insurance_from': date(2021, 1, 1),
            'lpp_insurance_id': lpp_1.id,
            'lpp_insurance_from': date(2021, 1, 1),
        })

        # Load IS Rates
        rates_to_load = [
            ('LU_N_A_0', 'LU_A0N.json'),
            ('LU_N_N_0', 'LU_N0N.json'),
            ('BE_N_A_0', 'BE_A0N.json'),
            ('BE_N_A_1', 'BE_A1N.json'),
            ('BE_N_B_0', 'BE_B0N.json'),
            ('BE_N_C_0', 'BE_C0N.json'),
            ('BE_N_B_1', 'BE_B1N.json'),
            ('BE_N_H_1', 'BE_H1N.json'),
            ('BE_N_L_0', 'BE_L0N.json'),
            ('BE_HE_N', 'BE_HEN.json'),
            ('BE_ME_N', 'BE_MEN.json'),
            ('BE_SF_N', 'BE_SFN.json'),
            ('TI_N_A_0', 'TI_A0N.json'),
            ('TI_N_B_0', 'TI_B0N.json'),
            ('TI_N_B_1', 'TI_B1N.json'),
            ('TI_N_C_0', 'TI_C0N.json'),
            ('TI_N_F_0', 'TI_F0N.json'),
            ('TI_N_F_1', 'TI_F1N.json'),
            ('TI_N_R_0', 'TI_R0N.json'),
            ('TI_N_T_0', 'TI_T0N.json'),
            ('VD_N_A_0', 'VD_A0N.json'),
            ('VD_N_A_1', 'VD_A1N.json'),
            ('VD_N_A_2', 'VD_A2N.json'),
            ('VD_N_B_0', 'VD_B0N.json'),
        ]
        rates_to_unlink = self.env['hr.rule.parameter']
        for xml_id, file_name in rates_to_load:
            rates_to_unlink += self.env['hr.rule.parameter'].search([('code', '=', f'l10n_ch_withholding_tax_rates_{xml_id}')])
        if rates_to_unlink:
            rates_to_unlink.unlink()
        for xml_id, file_name in rates_to_load:
            self.env['hr.rule.parameter'].search([('code', '=', f'l10n_ch_withholding_tax_rates_{xml_id}')]).unlink()
            rule_parameter = self.env['hr.rule.parameter'].create({
                'name': f'CH Withholding Tax: {xml_id}',
                'code': f'l10n_ch_withholding_tax_rates_{xml_id}',
                'country_id': self.env.ref('base.ch').id,
            })
            self.env['hr.rule.parameter.value'].create({
                'parameter_value': json.load(file_open(f'test_l10n_ch_hr_payroll_account/data/is_rates/{file_name}')),
                'rule_parameter_id': rule_parameter.id,
                'date_from': date(2021, 1, 1),
            })

        # Generate Employees
        employees = self.env['hr.employee'].with_context(tracking_disable=True).create([
            {'name': "Herz Monica", 'gender': 'female', 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'country_id': self.env.ref('base.ch').id, 'l10n_ch_sv_as_number': False, 'birthday': date(1976, 6, 30), 'marital': 'married', 'l10n_ch_marital_from': date(2001, 5, 25), 'private_street': 'Bahnhofstrasse 1', 'private_zip': '6020', 'private_city': 'Emmenbrücke', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': 1024, 'l10n_ch_residence_category': False, 'l10n_ch_canton': 'LU', 'lang': 'fr_FR', 'certificate': 'higherVocEducation'},
            {'name': "Paganini Maria", 'gender': 'female', 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'country_id': self.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.3598.1127.37', 'birthday': date(1958, 9, 30), 'marital': 'married', 'l10n_ch_marital_from': date(1992, 3, 13), 'private_street': 'Zentralstrasse 17', 'private_zip': '6030', 'private_city': 'Ebikon', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': 1054, 'l10n_ch_residence_category': 'settled-C', 'l10n_ch_canton': 'LU', 'lang': 'fr_FR'},
            {'name': "Lusser Pia", 'gender': 'female', 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'country_id': self.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.6417.0995.23', 'birthday': date(1958, 2, 5), 'marital': 'married', 'l10n_ch_marital_from': date(1979, 8, 14), 'private_street': 'Buochserstrasse 4', 'private_zip': '6370', 'private_city': 'Stans', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': 1509, 'l10n_ch_residence_category': False, 'l10n_ch_canton': 'NW', 'lang': 'fr_FR'},
            {'name': "Frankhauser Markus", 'gender': 'male', 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'country_id': self.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.6353.2927.43', 'birthday': date(1966, 10, 19), 'marital': 'single', 'private_street': 'Schmiedegasse 16', 'private_zip': '3150', 'private_city': 'Schwarzenburg', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': 855, 'l10n_ch_residence_category': False, 'l10n_ch_canton': 'BE', 'lang': 'fr_FR'},
            {'name': "Moser Johann", 'gender': 'male', 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'country_id': self.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.3574.4165.90', 'birthday': date(1957, 4, 15), 'marital': 'married', 'l10n_ch_marital_from': date(1981, 4, 23), 'private_street': 'Kramgasse 11', 'private_zip': '3011', 'private_city': 'Bern', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': 351, 'l10n_ch_residence_category': False, 'l10n_ch_canton': 'BE', 'lang': 'fr_FR'},
            {'name': "Zahnd Anita", 'gender': 'female', 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'country_id': self.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.6564.5197.21', 'birthday': date(1957, 4, 15), 'marital': 'married', 'l10n_ch_marital_from': date(1976, 5, 23), 'private_street': 'Lindenweg 10', 'private_zip': '3072', 'private_city': 'Ostermundigen', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': 363, 'l10n_ch_residence_category': False, 'l10n_ch_canton': 'BE', 'lang': 'fr_FR'},
            {'name': "Burri Heidi", 'gender': 'female', 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'country_id': self.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.1886.7922.72', 'birthday': date(1957, 12, 16), 'marital': 'married', 'l10n_ch_marital_from': date(1992, 12, 14), 'private_street': 'Laupenstrasse 45', 'private_zip': '3008', 'private_city': 'Bern', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': 351, 'l10n_ch_residence_category': False, 'l10n_ch_canton': 'BE', 'lang': 'fr_FR'},
            {'name': "Lamon René", 'gender': 'male', 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'country_id': self.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.3552.6511.80', 'birthday': date(1958, 9, 30), 'marital': 'married', 'l10n_ch_marital_from': date(1984, 3, 16), 'private_street': 'Effingerstrasse 87', 'private_zip': '3008', 'private_city': 'Bern', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': 351, 'l10n_ch_residence_category': 'settled-C', 'l10n_ch_canton': 'LU', 'l10n_ch_tax_scale': 'A', 'lang': 'fr_FR'},
            {'name': "Estermann Michael", 'gender': 'male', 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'country_id': self.env.ref('base.de').id, 'l10n_ch_sv_as_number': '756.1931.9954.43', 'birthday': date(1956, 1, 1), 'marital': 'married', 'l10n_ch_marital_from': date(1987, 4, 12), 'private_street': 'Seestrasse 3', 'private_zip': '6353', 'private_city': 'Weggis', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': 1069, 'l10n_ch_residence_category': 'settled-C', 'l10n_ch_canton': 'LU', 'lang': 'fr_FR'},
            {'name': "Ganz Heinz", 'gender': 'male', 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'country_id': self.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.6362.5066.57', 'birthday': date(1996, 12, 28), 'marital': 'married', 'l10n_ch_marital_from': date(2020, 7, 1), 'private_street': 'Neuhofstrasse 47', 'private_zip': '6020', 'private_city': 'Emmenbrücke', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': 1024, 'l10n_ch_residence_category': 'settled-C', 'l10n_ch_canton': 'LU', 'l10n_ch_tax_scale': 'A', 'lang': 'fr_FR'},
            {'name': "Bosshard Peter", 'gender': 'male', 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': self.id, 'country_id': self.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.3426.3448.04', 'birthday': date(1978, 4, 11), 'marital': 'married', 'l10n_ch_marital_from': date(1997, 9, 15), 'private_street': 'Brünigstrasse 20', 'private_zip': '6072', 'private_city': 'Sachseln', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': 1406, 'l10n_ch_residence_category': False, 'l10n_ch_canton': 'OW', 'l10n_ch_tax_scale': 'A', 'lang': 'fr_FR'},
            {'name': 'Casanova Renato', 'l10n_ch_sv_as_number': "756.3431.9824.73", 'gender': 'male', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1995, 1, 1), 'marital': 'partnership_dissolved_by_declaration_of_lost', 'l10n_ch_marital_from': date(2020, 6, 15), 'private_street': 'Bahnhofstrasse 6', 'private_zip': '6048', 'private_city': 'Horw', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': '1058', 'l10n_ch_canton': 'LU', 'l10n_ch_residence_category': False, 'lang': 'fr_FR', 'certificate': 'higherVocEducation'},
            {'name': "Combertaldi Renato", 'gender': 'male', 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': self.id, 'country_id': self.env.ref('base.it').id, 'l10n_ch_sv_as_number': '756.1925.1163.66', 'birthday': date(2005, 1, 1), 'marital': 'single', 'l10n_ch_marital_from': date(2005, 1, 1), 'private_street': 'Museggstrasse 4', 'private_zip': '6004', 'private_city': 'Luzern', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': 1061, 'l10n_ch_residence_category': 'settled-C', 'l10n_ch_canton': 'LU', 'l10n_ch_tax_scale': 'A', 'lang': 'fr_FR', 'certificate': 'higherVocEducation'},
            {'name': 'Egli Anna', 'l10n_ch_sv_as_number': "756.1927.3247.52", 'gender': 'female', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1977, 7, 13), 'marital': 'separated', 'l10n_ch_marital_from': date(2017, 4, 28), 'private_street': 'Seestrasse 5', 'private_zip': '6353', 'private_city': 'Weggis', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': '1069', 'l10n_ch_canton': 'LU', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
            {'name': "Degelo Lorenz", 'gender': 'male', 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': self.id, 'country_id': self.env.ref('base.ch').id, 'l10n_ch_sv_as_number': '756.3434.5392.78', 'birthday': date(1986, 2, 28), 'marital': 'registered_partnership', 'l10n_ch_marital_from': date(2011, 8, 17), 'private_street': 'Lopperstrasse 8', 'private_zip': '6010', 'private_city': 'Kriens', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': 1059, 'l10n_ch_residence_category': False, 'l10n_ch_canton': 'LU', 'l10n_ch_tax_scale': 'A', 'lang': 'fr_FR', 'certificate': 'higherVocEducation'},
            {'name': 'Aebi Anna', 'l10n_ch_sv_as_number': "756.3047.5009.62", 'gender': 'female', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1957, 12, 31), 'marital': 'single', 'l10n_ch_marital_from': date(1957, 12, 31), 'private_street': 'Bundesstrasse 5', 'private_zip': '6003', 'private_city': 'Luzern', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': '1061', 'l10n_ch_canton': 'LU', 'l10n_ch_residence_category': False, 'lang': 'fr_FR', 'certificate': 'higherVocEducation'},
            {'name': "Binggeli Fritz", 'gender': 'male', 'resource_calendar_id': resource_calendar_70_percent.id, 'company_id': self.id, 'country_id': self.env.ref('base.it').id, 'l10n_ch_sv_as_number': '756.3425.9630.75', 'birthday': date(1972, 4, 11), 'marital': 'single', 'l10n_ch_marital_from': date(1972, 4, 11), 'private_street': 'Via Monte Ceneri 17', 'private_zip': '6512', 'private_city': 'Giubiasco', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': 5002, 'l10n_ch_residence_category': "annual-B", 'l10n_ch_canton': 'TI', 'l10n_ch_tax_scale': 'A', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'is_non_resident': True, 'l10n_ch_has_withholding_tax': True},
            {'name': 'Blanc Pierre', 'l10n_ch_sv_as_number': "756.3729.5603.90", 'gender': 'male', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1982, 12, 11), 'marital': 'married', 'l10n_ch_marital_from': date(2021, 11, 1), 'private_street': 'Freiburgstrasse 312', 'private_zip': '3018', 'private_city': 'Bern', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': '351', 'l10n_ch_canton': 'BE', 'l10n_ch_residence_category': 'ProvisionallyAdmittedForeigners-F', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_tax_scale': 'B', 'l10n_ch_has_withholding_tax': True},
            {'name': "Andrey Melanie", 'gender': 'female', 'resource_calendar_id': resource_calendar_50_percent.id, 'company_id': self.id, 'country_id': self.env.ref('base.it').id, 'l10n_ch_sv_as_number': '756.1848.4786.64', 'birthday': date(1967, 5, 16), 'marital': 'single', 'l10n_ch_marital_from': date(1967, 5, 16), 'private_street': 'Via Lugano 4', 'private_zip': '6500', 'private_city': 'Bellinzona', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': 5002, 'l10n_ch_residence_category': "annual-B", 'l10n_ch_canton': 'TI', 'l10n_ch_tax_scale': 'A', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'is_non_resident': True, 'l10n_ch_has_withholding_tax': True},
            {'name': 'Arnold Lukas', 'l10n_ch_sv_as_number': "756.1859.2584.53", 'gender': 'male', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1993, 6, 17), 'marital': 'single', 'l10n_ch_marital_from': date(1993, 6, 17), 'private_street': 'Brünnenstrasse 66', 'private_zip': '3018', 'private_city': 'Bern', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': '351', 'l10n_ch_canton': 'BE', 'l10n_ch_residence_category': 'NotificationProcedureForShorttermWork90Days', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
            {'name': "Meier Christian", 'gender': 'male', 'resource_calendar_id': resource_calendar_40_percent.id, 'company_id': self.id, 'country_id': self.env.ref('base.it').id, 'l10n_ch_sv_as_number': '', 'birthday': date(1972, 1, 1), 'marital': 'single', 'l10n_ch_marital_from': date(1972, 1, 1), 'private_street': 'Via Campagna 5', 'private_zip': '6512', 'private_city': 'Giubiasco', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': 5002, 'l10n_ch_residence_category': "NotificationProcedureForShorttermWork120Days", 'l10n_ch_canton': 'TI', 'l10n_ch_tax_scale': 'A', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'is_non_resident': True, 'l10n_ch_has_withholding_tax': True},
            {'name': 'Bucher Elisabeth', 'l10n_ch_sv_as_number': "756.6319.2565.36", 'gender': 'female', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1997, 6, 6), 'marital': 'single', 'l10n_ch_marital_from': date(1997, 6, 6), 'private_street': 'Via Serafino Balestra 9', 'private_zip': '6900', 'private_city': 'Lugano', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': '5192', 'l10n_ch_canton': 'TI', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_has_withholding_tax': True, 'l10n_ch_tax_scale': 'A'},
            {'name': "Koller Ludwig", 'gender': 'male', 'resource_calendar_id': resource_calendar_40_percent.id, 'company_id': self.id, 'country_id': self.env.ref('base.de').id, 'l10n_ch_sv_as_number': '756.3539.3643.93', 'birthday': date(1989, 1, 10), 'marital': 'single', 'l10n_ch_marital_from': date(1989, 1, 10), 'private_street': 'Viale Stefano Franscini 17', 'private_zip': '6500', 'private_city': 'Bellinzona', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': 5002, 'l10n_ch_residence_category': "annual-B", 'l10n_ch_canton': 'TI', 'l10n_ch_tax_scale': 'A', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'is_non_resident': True, 'l10n_ch_has_withholding_tax': True},
            {'name': 'Utzinger Jan', 'l10n_ch_sv_as_number': "756.6555.6617.29", 'gender': 'male', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1980, 6, 23), 'marital': 'married', 'l10n_ch_marital_from': date(2021, 11, 25), 'private_street': 'Via Lugano 40', 'private_zip': '6500', 'private_city': 'Bellinzona', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': '5002', 'l10n_ch_canton': 'TI', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_has_withholding_tax': True, 'l10n_ch_tax_scale': 'B'},
            {'name': 'Lehmann Nadine', 'l10n_ch_sv_as_number': "756.3558.3266.93", 'gender': 'female', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1997, 7, 28), 'marital': 'single', 'l10n_ch_marital_from': date(1997, 7, 28), 'private_street': 'Via Pisanello 2', 'private_zip': '20146', 'private_city': 'Milano', 'private_country_id': self.env.ref('base.it').id, 'l10n_ch_municipality': 'nan', 'l10n_ch_canton': 'EX', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'is_non_resident': True, 'l10n_ch_has_withholding_tax': True, 'l10n_ch_tax_scale': 'A'},
            {'name': 'Jenzer Marcel', 'l10n_ch_sv_as_number': "756.6408.6518.22", 'gender': 'male', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1972, 1, 1), 'marital': 'single', 'l10n_ch_marital_from': date(1972, 1, 1), 'private_street': 'viale misurata 56', 'private_zip': '20146', 'private_city': 'Milano', 'private_country_id': self.env.ref('base.it').id, 'l10n_ch_municipality': 'nan', 'l10n_ch_canton': 'TI', 'l10n_ch_residence_category': 'othersNotSwiss', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_tax_scale': 'R', 'l10n_ch_has_withholding_tax': True},
            {'name': 'Rast Eva', 'l10n_ch_sv_as_number': "756.3627.5282.70", 'gender': 'female', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1988, 11, 1), 'marital': 'single', 'l10n_ch_marital_from': date(1988, 11, 1), 'private_street': 'Opelstrasse 1', 'private_zip': '78467', 'private_city': 'Konstanz', 'private_country_id': self.env.ref('base.de').id, 'l10n_ch_municipality': 'nan', 'l10n_ch_canton': 'EX', 'l10n_ch_residence_category': 'crossBorder-G', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'is_non_resident': True, 'l10n_ch_has_withholding_tax': True, 'l10n_ch_tax_scale': 'L'},
            {'name': 'Arbenz Esther', 'l10n_ch_sv_as_number': "756.1853.0576.49", 'gender': 'female', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1974, 4, 13), 'marital': 'single', 'l10n_ch_marital_from': date(1974, 4, 13), 'private_street': 'via Vedano 1', 'private_zip': '20900', 'private_city': 'Monza', 'private_country_id': self.env.ref('base.it').id, 'l10n_ch_municipality': 'nan', 'l10n_ch_canton': 'BE', 'l10n_ch_residence_category': 'crossBorder-G', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_has_withholding_tax': True, 'l10n_ch_tax_scale': 'A'},
            {'name': 'Forster Moreno', 'l10n_ch_sv_as_number': "756.6361.0022.59", 'gender': 'male', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1974, 7, 13), 'marital': 'single', 'l10n_ch_marital_from': date(1974, 7, 13), 'private_street': 'Via Como 12', 'private_zip': '21100', 'private_city': 'Varese', 'private_country_id': self.env.ref('base.it').id, 'l10n_ch_municipality': 'nan', 'l10n_ch_canton': 'EX', 'l10n_ch_residence_category': 'crossBorder-G', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_tax_scale': 'R', 'l10n_ch_has_withholding_tax': True},
            {'name': 'Müller Heinrich', 'l10n_ch_sv_as_number': False, 'gender': 'male', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1974, 7, 13), 'marital': 'single', 'l10n_ch_marital_from': date(1974, 7, 13), 'private_street': 'Lilienstrasse 22', 'private_zip': '81669', 'private_city': 'München', 'private_country_id': self.env.ref('base.de').id, 'l10n_ch_municipality': 'nan', 'l10n_ch_canton': 'EX', 'l10n_ch_residence_category': 'othersNotSwiss', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
            {'name': 'Bolletto Franca', 'l10n_ch_sv_as_number': "756.6508.6893.67", 'gender': 'female', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1992, 6, 6), 'marital': 'single', 'l10n_ch_marital_from': date(1992, 6, 6), 'private_street': 'Route de chavannes 11 ', 'private_zip': '1007', 'private_city': 'Lausanne', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': '5586', 'l10n_ch_canton': 'VD', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
            {'name': 'Armanini Laura', 'l10n_ch_sv_as_number': "756.3728.4917.63", 'gender': 'female', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1977, 10, 4), 'marital': 'single', 'l10n_ch_marital_from': date(1977, 10, 4), 'private_street': 'Kehrgasse 8', 'private_zip': '3018', 'private_city': 'Bern', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': '351', 'l10n_ch_canton': 'BE', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
            {'name': 'Châtelain Pierre', 'l10n_ch_sv_as_number': "756.3434.5129.12", 'gender': 'male', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1972, 4, 11), 'marital': 'single', 'l10n_ch_marital_from': date(1972, 4, 11), 'private_street': 'Wiesenstrasse 14', 'private_zip': '3098', 'private_city': 'Köniz', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': '355', 'l10n_ch_canton': 'BE', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
            {'name': 'Rinaldi Massimo', 'l10n_ch_sv_as_number': "756.6412.9848.00", 'gender': 'male', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1967, 4, 11), 'marital': 'single', 'l10n_ch_marital_from': date(1967, 4, 11), 'private_street': 'Piazza Marconi 7', 'private_zip': '24122', 'private_city': 'Bergamo', 'private_country_id': self.env.ref('base.it').id, 'l10n_ch_municipality': 'nan', 'l10n_ch_canton': 'EX', 'l10n_ch_residence_category': 'crossBorder-G', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
            {'name': 'Roos Roland', 'l10n_ch_sv_as_number': "756.6498.9438.07", 'gender': 'male', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1967, 5, 16), 'marital': 'divorced', 'l10n_ch_marital_from': date(2018, 6, 15), 'private_street': 'Via Ospedale 10', 'private_zip': '6500', 'private_city': 'Bellinzona', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': '5002', 'l10n_ch_canton': 'TI', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
            {'name': 'Maldini Fabio', 'l10n_ch_sv_as_number': "756.3641.0372.46", 'gender': 'male', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1988, 6, 17), 'marital': 'single', 'l10n_ch_marital_from': date(1988, 6, 17), 'private_street': 'Blockweg 2', 'private_zip': '3007', 'private_city': 'Bern', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': '351', 'l10n_ch_canton': 'BE', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
            {'name': 'Oberli Christine', 'l10n_ch_sv_as_number': "756.6462.6899.46", 'gender': 'female', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1990, 10, 15), 'marital': 'divorced', 'l10n_ch_marital_from': date(2020, 6, 20), 'children': 1, 'private_street': 'Hopfenweg 22', 'private_zip': '3007', 'private_city': 'Bern', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': '351', 'l10n_ch_canton': 'BE', 'l10n_ch_residence_category': 'shortTerm-L', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_tax_scale': 'H', 'l10n_ch_has_withholding_tax': True},
            {'name': 'Jung Claude', 'l10n_ch_sv_as_number': "756.3514.6025.02", 'gender': 'male', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1977, 12, 11), 'marital': 'single', 'l10n_ch_marital_from': date(1977, 12, 11), 'private_street': 'Bahnhofplatz 1', 'private_zip': '2502', 'private_city': 'Biel/Bienne', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': '371', 'l10n_ch_canton': 'BE', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
            {'name': 'Hasler Harald', 'l10n_ch_sv_as_number': "756.3466.0443.68", 'gender': 'male', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1967, 1, 1), 'marital': 'single', 'l10n_ch_marital_from': date(1967, 1, 1), 'private_street': 'Maffeistrasse 5', 'private_zip': '80333', 'private_city': 'München', 'private_country_id': self.env.ref('base.de').id, 'l10n_ch_municipality': 'nan', 'l10n_ch_canton': 'EX', 'l10n_ch_residence_category': 'othersNotSwiss', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
            {'name': 'Farine Corinne', 'l10n_ch_sv_as_number': "756.3438.2653.71", 'gender': 'female', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1996, 6, 17), 'marital': 'single', 'l10n_ch_marital_from': date(1996, 6, 17), 'private_street': 'Blockweg 2', 'private_zip': '3007', 'private_city': 'Bern', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': '351', 'l10n_ch_canton': 'BE', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True, 'children': 1},
            {'name': 'Meier Max', 'l10n_ch_sv_as_number': "756.3572.1419.82", 'gender': 'male', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1990, 2, 22), 'marital': 'single', 'l10n_ch_marital_from': date(1990, 2, 22), 'private_street': 'Via Cantonale 31', 'private_zip': '6815', 'private_city': 'Melide', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': '5198', 'l10n_ch_canton': 'TI', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
            {'name': 'Peters Otto', 'l10n_ch_sv_as_number': "756.1949.3782.69", 'gender': 'male', 'country_id': self.env.ref('base.ch').id, 'birthday': date(1991, 11, 11), 'marital': 'single', 'l10n_ch_marital_from': date(1991, 11, 11), 'private_street': 'Corso Galileo Ferraris, 14', 'private_zip': '10121', 'private_city': 'Torino', 'private_country_id': self.env.ref('base.it').id, 'l10n_ch_municipality': 'nan', 'l10n_ch_canton': 'EX', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True},
            {'name': 'Ochsenbein Lea', 'l10n_ch_sv_as_number': "756.6491.7043.37", 'gender': 'female', 'country_id': self.env.ref('base.de').id, 'birthday': date(1993, 2, 22), 'marital': 'single', 'l10n_ch_marital_from': date(1993, 2, 22), 'private_street': 'Marienplatz 1', 'private_zip': '80331', 'private_city': 'München', 'private_country_id': self.env.ref('base.de').id, 'l10n_ch_municipality': False, 'l10n_ch_canton': 'EX', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR', 'certificate': 'higherVocEducation', 'l10n_ch_tax_scale': 'A', 'l10n_ch_has_withholding_tax': True}
        ])
        mapped_employees = {}
        for index, employee in enumerate(employees, start=1):
            mapped_employees[f"employee_tf{str(index).zfill(2)}"] = employee

        # Generate Salary Attachments
        self.env['hr.salary.attachment'].create([
            # TF01
            {'description': 'Salaire horaire', 'monthly_amount': 160.0, 'total_amount': 320.0, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf01'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 170.0, 'total_amount': 170.0, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf01'].id)]},
            {'description': 'Gratification', 'monthly_amount': 20000, 'total_amount': 20000, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 10, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_gratification').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf01'].id)]},
            {'description': 'Part facultative employeurs LPP', 'monthly_amount': 682, 'total_amount': 2046, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_optional_lpp').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf01'].id)]},
            {'description': 'Indemnité APG', 'monthly_amount': 1200, 'total_amount': 1200, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_indemnity_apg').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf01'].id)]},
            {'description': 'Indemnité APG', 'monthly_amount': 1300, 'total_amount': 1300, 'date_start': date(2022, 5, 1), 'date_end': date(2022, 5, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_indemnity_apg').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf01'].id)]},
            {'description': 'Prestation compensation mil. (CCM)', 'monthly_amount': 1000, 'total_amount': 1000, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_military_wage').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf01'].id)]},
            {'description': 'Indemnité journalière accident', 'monthly_amount': 1250, 'total_amount': 2500, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_indemnity_accident').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf01'].id)]},
            {'description': 'Indemnité maladie', 'monthly_amount': 250, 'total_amount': 500, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_indemnity_illness').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf01'].id)]},
            {'description': 'Indemnité maladie', 'monthly_amount': 1000, 'total_amount': 1000, 'date_start': date(2022, 5, 1), 'date_end': date(2022, 5, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_indemnity_illness').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf01'].id)]},
            # TF02
            {'description': 'Salaire horaire', 'monthly_amount': 150.0, 'total_amount': 150.0, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 1, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 70.0, 'total_amount': 140.0, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 142.0, 'total_amount': 142.0, 'date_start': date(2022, 4, 1), 'date_end': date(2022, 4, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 20.0, 'total_amount': 20.0, 'date_start': date(2022, 5, 1), 'date_end': date(2022, 5, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 100.0, 'total_amount': 100.0, 'date_start': date(2022, 6, 1), 'date_end': date(2022, 6, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 120.0, 'total_amount': 120.0, 'date_start': date(2022, 7, 1), 'date_end': date(2022, 7, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 130.0, 'total_amount': 130.0, 'date_start': date(2022, 8, 1), 'date_end': date(2022, 8, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 162.0, 'total_amount': 162.0, 'date_start': date(2022, 9, 1), 'date_end': date(2022, 9, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 50.0, 'total_amount': 50.0, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 10, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 162.0, 'total_amount': 162.0, 'date_start': date(2022, 11, 1), 'date_end': date(2022, 11, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 150.0, 'total_amount': 150.0, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 120.0, 'total_amount': 120.0, 'date_start': date(2023, 1, 1), 'date_end': date(2023, 1, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 50.0, 'total_amount': 50.0, 'date_start': date(2023, 2, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Salaire à la leçon', 'monthly_amount': 20.0, 'total_amount': 20.0, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 1, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_lesson').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Salaire à la leçon', 'monthly_amount': 20.0, 'total_amount': 20.0, 'date_start': date(2022, 5, 1), 'date_end': date(2022, 5, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_lesson').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Salaire à la leçon', 'monthly_amount': 40.0, 'total_amount': 40.0, 'date_start': date(2022, 6, 1), 'date_end': date(2022, 6, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_lesson').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Salaire à la leçon', 'monthly_amount': 20.0, 'total_amount': 40.0, 'date_start': date(2022, 7, 1), 'date_end': date(2022, 8, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_lesson').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Salaire à la leçon', 'monthly_amount': 20.0, 'total_amount': 20.0, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 10, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_lesson').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Salaire à la leçon', 'monthly_amount': 20.0, 'total_amount': 20.0, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_lesson').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Salaire à la leçon', 'monthly_amount': 20.0, 'total_amount': 20.0, 'date_start': date(2023, 1, 1), 'date_end': date(2023, 1, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_lesson').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Indemnité travail par équipes', 'monthly_amount': 90, 'total_amount': 90, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 1, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_team_work').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Indemnité travail par équipes', 'monthly_amount': 50, 'total_amount': 50, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_team_work').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Indemnité travail par équipes', 'monthly_amount': 25, 'total_amount': 25, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_team_work').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Indemnité travail par équipes', 'monthly_amount': 35, 'total_amount': 35, 'date_start': date(2022, 4, 1), 'date_end': date(2022, 4, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_team_work').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Indemnité travail par équipes', 'monthly_amount': 40, 'total_amount': 40, 'date_start': date(2022, 5, 1), 'date_end': date(2022, 5, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_team_work').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Indemnité travail par équipes', 'monthly_amount': 35, 'total_amount': 35, 'date_start': date(2022, 7, 1), 'date_end': date(2022, 7, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_team_work').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Indemnité travail par équipes', 'monthly_amount': 105, 'total_amount': 105, 'date_start': date(2022, 8, 1), 'date_end': date(2022, 8, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_team_work').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Indemnité travail par équipes', 'monthly_amount': 89, 'total_amount': 89, 'date_start': date(2022, 9, 1), 'date_end': date(2022, 9, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_team_work').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Indemnité travail par équipes', 'monthly_amount': 81, 'total_amount': 81, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 10, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_team_work').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Indemnité travail par équipes', 'monthly_amount': 95, 'total_amount': 95, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_team_work').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Commission', 'monthly_amount': 2044, 'total_amount': 2044, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_commission').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Perte de gain RHT/ITP (SH)', 'monthly_amount': 3000, 'total_amount': 6000, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_indemnite_perte_gain').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Indemnité de chômage', 'monthly_amount': 2200, 'total_amount': 4400, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_indemnite_chomage').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Délai de carence RHT/ITP', 'monthly_amount': 200, 'total_amount': 400, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_delai_carence_rht_itp').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            {'description': 'Allocation pour enfant', 'monthly_amount': 200, 'total_amount': 2800, 'date_start': date(2022, 1, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_child_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf02'].id)]},
            # TF03
            {'description': 'Indemnité spéciale', 'monthly_amount': 3200, 'total_amount': 6400, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_special_indemnity').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf03'].id)]},
            {'description': 'Cadeau pour ancienneté de service', 'monthly_amount': 22000, 'total_amount': 22000, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_jubilee_gift').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf03'].id)]},
            {'description': 'Prestation en capital à caractère de prévoyance', 'monthly_amount': 6000, 'total_amount': 6000, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_pension_capital').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf03'].id)]},
            {'description': 'Cotisation LPP', 'monthly_amount': 385, 'total_amount': 770, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf03'].id)]},
            # TF04
            {'description': '14ème salaire', 'monthly_amount': 30000, 'total_amount': 30000, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_14th_month').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf04'].id)]},
            {'description': 'Cadeau pour ancienneté de service', 'monthly_amount': 40000, 'total_amount': 80000, 'date_start': date(2023, 1, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_jubilee_gift').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf04'].id)]},
            {'description': 'Cotisation LPP', 'monthly_amount': 2450, 'total_amount': 29400, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf04'].id)]},
            # TF05
            {'description': 'Indemnité de dimanche', 'monthly_amount': 6000, 'total_amount': 12000, 'date_start': date(2023, 1, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_sunday_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf05'].id)]},
            {'description': 'Indemnité journalière accident', 'monthly_amount': 10000, 'total_amount': 20000, 'date_start': date(2023, 1, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_indemnity_accident').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf05'].id)]},
            {'description': 'Correction indemnité de tiers', 'monthly_amount': 10000, 'total_amount': 20000, 'date_start': date(2023, 1, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_third_party_correction').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf05'].id)]},
            {'description': 'Cotisation LPP', 'monthly_amount': 102, 'total_amount': 408, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 4, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf05'].id)]},
            # TF06
            {'description': 'Indemnité APG', 'monthly_amount': 4800, 'total_amount': 9600, 'date_start': date(2023, 1, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_indemnity_apg').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf06'].id)]},
            {'description': 'Indemnité journalière accident', 'monthly_amount': 15200, 'total_amount': 30400, 'date_start': date(2023, 1, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_indemnity_accident').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf06'].id)]},
            {'description': 'Correction indemnité de tiers', 'monthly_amount': 20000, 'total_amount': 40000, 'date_start': date(2023, 1, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_third_party_correction').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf06'].id)]},
            {'description': 'Cotisation LPP', 'monthly_amount': 945, 'total_amount': 9450, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 10, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf06'].id)]},
            # TF 07
            {'description': 'Heures supplémentaires après le départ', 'monthly_amount': 15000, 'total_amount': 15000, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 1, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_overtime_after_departure').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf07'].id)]},
            {'description': 'Indemnité journalière accident', 'monthly_amount': 9500, 'total_amount': 9500, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_indemnity_accident').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf07'].id)]},
            {'description': 'Correction indemnité de tiers', 'monthly_amount': 9500, 'total_amount': 9500, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_third_party_correction').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf07'].id)]},
            {'description': 'Cotisation LPP', 'monthly_amount': 560, 'total_amount': 1120, 'date_start': date(2021, 11, 1), 'date_end': date(2021, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf07'].id)]},
            # TF08
            {'description': 'Salaire horaire', 'monthly_amount': 170.0, 'total_amount': 2040.0, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf08'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 350.0, 'total_amount': 350.0, 'date_start': date(2023, 2, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf08'].id)]},
            {'description': 'Indemnité travail par équipes', 'monthly_amount': 25, 'total_amount': 25, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_team_work').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf08'].id)]},
            {'description': 'Indemnité travail par équipes', 'monthly_amount': 35, 'total_amount': 35, 'date_start': date(2022, 4, 1), 'date_end': date(2022, 4, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_team_work').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf08'].id)]},
            {'description': 'Indemnité travail par équipes', 'monthly_amount': 40, 'total_amount': 40, 'date_start': date(2022, 5, 1), 'date_end': date(2022, 5, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_team_work').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf08'].id)]},
            {'description': 'Indemnité travail par équipes', 'monthly_amount': 35, 'total_amount': 35, 'date_start': date(2022, 7, 1), 'date_end': date(2022, 7, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_team_work').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf08'].id)]},
            {'description': 'Indemnité travail par équipes', 'monthly_amount': 105, 'total_amount': 105, 'date_start': date(2022, 8, 1), 'date_end': date(2022, 8, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_team_work').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf08'].id)]},
            {'description': 'Indemnité travail par équipes', 'monthly_amount': 89, 'total_amount': 89, 'date_start': date(2022, 9, 1), 'date_end': date(2022, 9, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_team_work').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf08'].id)]},
            {'description': 'Indemnité travail par équipes', 'monthly_amount': 81, 'total_amount': 81, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 10, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_team_work').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf08'].id)]},
            {'description': 'Indemnité travail par équipes', 'monthly_amount': 44, 'total_amount': 44, 'date_start': date(2022, 11, 1), 'date_end': date(2022, 11, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_team_work').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf08'].id)]},
            {'description': 'Indemnité travail par équipes', 'monthly_amount': 95, 'total_amount': 95, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_team_work').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf08'].id)]},
            {'description': 'Indemnité travail par équipes', 'monthly_amount': 44, 'total_amount': 44, 'date_start': date(2023, 2, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_team_work').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf08'].id)]},
            {'description': 'Indemnité de dimanche', 'monthly_amount': 20000, 'total_amount': 20000, 'date_start': date(2023, 1, 1), 'date_end': date(2023, 1, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_sunday_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf08'].id)]},
            {'description': 'Commission', 'monthly_amount': 2044, 'total_amount': 2044, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_commission').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf08'].id)]},
            {'description': 'Allocation pour enfant', 'monthly_amount': 230, 'total_amount': 2760, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_child_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf08'].id)]},
            {'description': 'Cotisation LPP', 'monthly_amount': 724, 'total_amount': 8688, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf08'].id)]},
            # TF09
            {'description': 'Gratification', 'monthly_amount': 1700, 'total_amount': 1700, 'date_start': date(2022, 11, 1), 'date_end': date(2022, 11, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_gratification').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf09'].id)]},
            {'description': 'Gratification', 'monthly_amount': 200, 'total_amount': 200, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_gratification').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf09'].id)]},
            {'description': 'Indemnité spéciale', 'monthly_amount': 35000, 'total_amount': 35000, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_special_indemnity').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf09'].id)]},
            {'description': 'Indemnité journalière accident', 'monthly_amount': 30000, 'total_amount': 30000, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 10, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_indemnity_accident').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf09'].id)]},
            {'description': 'Indemnité journalière accident', 'monthly_amount': 32000, 'total_amount': 32000, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_indemnity_accident').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf09'].id)]},
            {'description': 'Correction indemnité de tiers', 'monthly_amount': 30000, 'total_amount': 30000, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 10, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_third_party_correction').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf09'].id)]},
            {'description': 'Correction indemnité de tiers', 'monthly_amount': 32000, 'total_amount': 32000, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_third_party_correction').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf09'].id)]},
            # TF10
            {'description': 'Heures supplémentaires 125%', 'monthly_amount': 1200, 'total_amount': 1200, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_overtime_125').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf10'].id)]},
            {'description': 'Indemnité spéciale', 'monthly_amount': 31000, 'total_amount': 31000, 'date_start': date(2022, 9, 1), 'date_end': date(2022, 9, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_special_indemnity').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf10'].id)]},
            {'description': 'Indemnité spéciale', 'monthly_amount': 7000, 'total_amount': 7000, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_special_indemnity').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf10'].id)]},
            {'description': 'Indemnité APG', 'monthly_amount': 1000, 'total_amount': 1000, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_indemnity_apg').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf10'].id)]},
            {'description': 'Prestation compensation mil. (CCM)', 'monthly_amount': 800, 'total_amount': 800, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_military_wage').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf10'].id)]},
            {'description': 'Indemnité journalière accident', 'monthly_amount': 2000, 'total_amount': 2000, 'date_start': date(2022, 9, 1), 'date_end': date(2022, 9, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_indemnity_accident').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf10'].id)]},
            {'description': 'Indemnité maladie', 'monthly_amount': 2500, 'total_amount': 2500, 'date_start': date(2022, 9, 1), 'date_end': date(2022, 9, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_indemnity_illness').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf10'].id)]},
            {'description': 'Correction indemnité de tiers', 'monthly_amount': 1800, 'total_amount': 1800, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_third_party_correction').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf10'].id)]},
            {'description': 'Correction indemnité de tiers', 'monthly_amount': 4500, 'total_amount': 4500, 'date_start': date(2022, 9, 1), 'date_end': date(2022, 9, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_third_party_correction').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf10'].id)]},
            {'description': 'Déduction RHT/ITP (SM)', 'monthly_amount': 3000, 'total_amount': 3000, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_ded_rht_itp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf10'].id)]},
            {'description': 'Versement salaire après décès', 'monthly_amount': 6400, 'total_amount': 12800, 'date_start': date(2022, 11, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_dead_alw').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf10'].id)]},
            {'description': 'Indemnité de chômage', 'monthly_amount': 2200, 'total_amount': 2200, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_indemnite_chomage').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf10'].id)]},
            {'description': 'Délai de carence RHT/ITP', 'monthly_amount': 200, 'total_amount': 200, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_delai_carence_rht_itp').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf10'].id)]},
            {'description': 'Cotisation LPP', 'monthly_amount': 448, 'total_amount': 4032, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 10, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf10'].id)]},
            # TF11
            {'description': 'Honoraires', 'monthly_amount': 20000, 'total_amount': 20000, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 10, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_fee_ch').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Honoraires', 'monthly_amount': 15000, 'total_amount': 15000, 'date_start': date(2022, 11, 1), 'date_end': date(2022, 11, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_fee_ch').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Indemnité de résidence', 'monthly_amount': 500, 'total_amount': 7000, 'date_start': date(2022, 1, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_house_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Gratification', 'monthly_amount': 5000, 'total_amount': 5000, 'date_start': date(2022, 4, 1), 'date_end': date(2022, 4, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_gratification').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Indemnité spéciale', 'monthly_amount': 3400, 'total_amount': 3400, 'date_start': date(2022, 4, 1), 'date_end': date(2022, 4, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_special_indemnity').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Indemnité spéciale', 'monthly_amount': 1200, 'total_amount': 1200, 'date_start': date(2022, 7, 1), 'date_end': date(2022, 7, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_special_indemnity').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Indemnité spéciale', 'monthly_amount': 500, 'total_amount': 500, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 10, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_special_indemnity').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Prestation en capital à caractère de prévoyance', 'monthly_amount': 50000, 'total_amount': 50000, 'date_start': date(2022, 5, 1), 'date_end': date(2022, 5, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_pension_capital').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Part privée voiture de service', 'monthly_amount': 250, 'total_amount': 3500, 'date_start': date(2022, 1, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_company_car').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Réduction loyer logement locatif', 'monthly_amount': 1200, 'total_amount': 16800, 'date_start': date(2022, 1, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_rental_housing').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Actions de collaborateurs', 'monthly_amount': 20000, 'total_amount': 20000, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_action_collab').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Actions de collaborateurs', 'monthly_amount': 20000, 'total_amount': 20000, 'date_start': date(2022, 6, 1), 'date_end': date(2022, 6, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_action_collab').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Part facultative employeurs rachat LPP', 'monthly_amount': 5000, 'total_amount': 5000, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_optional_lpp_redemption').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Allocation pour enfant', 'monthly_amount': 250, 'total_amount': 500, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_child_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Allocation pour enfant', 'monthly_amount': 450, 'total_amount': 3600, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 10, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_child_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Allocation pour enfant', 'monthly_amount': 200, 'total_amount': 800, 'date_start': date(2022, 11, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_child_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Allocation de naissance', 'monthly_amount': 1000, 'total_amount': 1000, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_birth_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Cotisation LPP', 'monthly_amount': 763, 'total_amount': 3815, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 5, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Cotisation LPP', 'monthly_amount': 2514, 'total_amount': 22626, 'date_start': date(2022, 6, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Correction prestations en nature', 'monthly_amount': 1200, 'total_amount': 16800, 'date_start': date(2022, 1, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_bik_correction').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Correction avantage en argent', 'monthly_amount': 250, 'total_amount': 500, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_cash_correction').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Correction avantage en argent', 'monthly_amount': 20250, 'total_amount': 20250, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_cash_correction').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Correction avantage en argent', 'monthly_amount': 250, 'total_amount': 500, 'date_start': date(2022, 4, 1), 'date_end': date(2022, 5, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_cash_correction').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Correction avantage en argent', 'monthly_amount': 19750, 'total_amount': 19750, 'date_start': date(2022, 6, 1), 'date_end': date(2022, 6, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_cash_correction').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            {'description': 'Correction avantage en argent', 'monthly_amount': 250, 'total_amount': 2000, 'date_start': date(2022, 7, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_cash_correction').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf11'].id)]},
            # TF12
            {'employee_ids': [(4, mapped_employees['employee_tf12'].id)], 'monthly_amount': 1000, 'total_amount': 1000, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 10, 31), 'description': 'Commission', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_commission').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf12'].id)], 'monthly_amount': 10000, 'total_amount': 10000, 'date_start': date(2022, 11, 1), 'date_end': date(2022, 11, 30), 'description': 'Commission', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_commission').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf12'].id)], 'monthly_amount': 25000, 'total_amount': 25000, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'description': 'Commission', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_commission').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf12'].id)], 'monthly_amount': 200, 'total_amount': 1600, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 9, 30), 'description': 'Repas gratuit', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_free_meals').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf12'].id)], 'monthly_amount': 650, 'total_amount': 5200, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 9, 30), 'description': 'Logement gratuit', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_free_housing').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf12'].id)], 'monthly_amount': 7000, 'total_amount': 7000, 'date_start': date(2022, 8, 1), 'date_end': date(2022, 8, 31), 'description': 'Options de collaborateurs', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_optcollab').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf12'].id)], 'monthly_amount': 2000, 'total_amount': 2000, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'description': 'Perfectionnement (certificat de salaire)', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_improv').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf12'].id)], 'monthly_amount': 2000, 'total_amount': 2000, 'date_start': date(2022, 6, 1), 'date_end': date(2022, 6, 30), 'description': 'Indemnité APG', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_indemnity_apg').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf12'].id)], 'monthly_amount': 1500, 'total_amount': 1500, 'date_start': date(2022, 6, 1), 'date_end': date(2022, 6, 30), 'description': 'Prestation compensation mil. (CCM)', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_military_wage').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf12'].id)], 'monthly_amount': 3000, 'total_amount': 3000, 'date_start': date(2022, 6, 1), 'date_end': date(2022, 6, 30), 'description': 'Indemnité journalière accident', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_indemnity_accident').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf12'].id)], 'monthly_amount': 6500, 'total_amount': 6500, 'date_start': date(2022, 6, 1), 'date_end': date(2022, 6, 30), 'description': 'Correction indemnité de tiers', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_third_party_correction').id, 'is_refund': True},
            {'employee_ids': [(4, mapped_employees['employee_tf12'].id)], 'monthly_amount': 840, 'total_amount': 9240, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 12, 31), 'description': 'Cotisation LPP', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True},
            {'employee_ids': [(4, mapped_employees['employee_tf12'].id)], 'monthly_amount': 850, 'total_amount': 6800, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 9, 30), 'description': 'Correction prestations en nature', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_bik_correction').id, 'is_refund': True},
            {'employee_ids': [(4, mapped_employees['employee_tf12'].id)], 'monthly_amount': 7000, 'total_amount': 7000, 'date_start': date(2022, 8, 1), 'date_end': date(2022, 8, 31), 'description': 'Correction avantage en argent', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_cash_correction').id, 'is_refund': True},
            {'employee_ids': [(4, mapped_employees['employee_tf12'].id)], 'monthly_amount': 1000, 'total_amount': 8000, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 9, 30), 'description': 'Frais effectifs expatriés', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_effective_expatriate_costs').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf12'].id)], 'monthly_amount': 800, 'total_amount': 2400, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 12, 31), 'description': 'Frais forfaitaires de voiture', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_car_fees').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf12'].id)], 'monthly_amount': 300, 'total_amount': 900, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 12, 31), 'description': 'Autres frais forfaitaires', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_other_fees').id, 'is_refund': False},
            # TF13
            {'description': 'Indemnité de résidence', 'monthly_amount': 200, 'total_amount': 2800, 'date_start': date(2022, 1, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_house_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf13'].id)]},
            {'description': 'Heures supplémentaires', 'monthly_amount': 180, 'total_amount': 180, 'date_start': date(2022, 4, 1), 'date_end': date(2022, 4, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_overtime100').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf13'].id)]},
            {'description': 'Heures supplémentaires', 'monthly_amount': 300, 'total_amount': 300, 'date_start': date(2022, 7, 1), 'date_end': date(2022, 7, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_overtime100').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf13'].id)]},
            {'description': 'Heures supplémentaires', 'monthly_amount': 80, 'total_amount': 80, 'date_start': date(2022, 11, 1), 'date_end': date(2022, 11, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_overtime100').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf13'].id)]},
            {'description': 'Heures supplémentaires', 'monthly_amount': 250, 'total_amount': 250, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_overtime100').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf13'].id)]},
            {'description': 'Commission', 'monthly_amount': 1000, 'total_amount': 1000, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_commission').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf13'].id)]},
            {'description': 'Allocation pour enfant', 'monthly_amount': 200, 'total_amount': 400, 'date_start': date(2023, 1, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_child_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf13'].id)]},
            {'description': 'Frais de voyage', 'monthly_amount': 500, 'total_amount': 5500, 'date_start': date(2022, 4, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_travel_expense').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf13'].id)]},
            # TF14
            {'description': 'Salaire horaire', 'monthly_amount': 75.0, 'total_amount': 75.0, 'date_start': date(2021, 11, 1), 'date_end': date(2021, 11, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf14'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 130.0, 'total_amount': 130.0, 'date_start': date(2021, 12, 1), 'date_end': date(2021, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf14'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 120.0, 'total_amount': 120.0, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 1, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf14'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 115.0, 'total_amount': 115.0, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf14'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 160.0, 'total_amount': 160.0, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf14'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 95.0, 'total_amount': 95.0, 'date_start': date(2022, 4, 1), 'date_end': date(2022, 4, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf14'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 140.0, 'total_amount': 280.0, 'date_start': date(2022, 5, 1), 'date_end': date(2022, 6, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf14'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 125.0, 'total_amount': 125.0, 'date_start': date(2022, 7, 1), 'date_end': date(2022, 7, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf14'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 170.0, 'total_amount': 170.0, 'date_start': date(2022, 8, 1), 'date_end': date(2022, 8, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf14'].id)]},
            {'description': 'Options de collaborateurs', 'monthly_amount': 10000, 'total_amount': 10000, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 10, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_optcollab').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf14'].id)]},
            {'description': 'Correction avantage en argent', 'monthly_amount': 10000, 'total_amount': 10000, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 10, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_cash_correction').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf14'].id)]},
            {'description': 'Frais de voyage', 'monthly_amount': 200, 'total_amount': 3200, 'date_start': date(2021, 11, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_travel_expense').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf14'].id)]},
            # TF15
            {'description': 'Salaire à la leçon', 'monthly_amount': 21, 'total_amount': 21, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_lesson').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf15'].id)]},
            {'description': 'Frais de voyage', 'monthly_amount': 257.5, 'total_amount': 257.5, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_travel_expense').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf15'].id)]},
            # TF16
            {'employee_ids': [(4, mapped_employees['employee_tf16'].id)], 'monthly_amount': 9458.35, 'total_amount': 9458.35, 'date_start': date(2021, 11, 1), 'date_end': date(2021, 11, 30), 'description': 'Honoraires', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_fee_ch').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf16'].id)], 'monthly_amount': 8895, 'total_amount': 8895, 'date_start': date(2021, 12, 1), 'date_end': date(2021, 12, 31), 'description': 'Honoraires', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_fee_ch').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf16'].id)], 'monthly_amount': 14350.6, 'total_amount': 14350.6, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 2, 28), 'description': 'Honoraires', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_fee_ch').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf16'].id)], 'monthly_amount': 10214.45, 'total_amount': 10214.45, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'description': 'Honoraires', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_fee_ch').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf16'].id)], 'monthly_amount': 3000, 'total_amount': 3000, 'date_start': date(2021, 11, 1), 'date_end': date(2021, 11, 30), 'description': 'Indemnité spéciale', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_special_indemnity').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf16'].id)], 'monthly_amount': 5000, 'total_amount': 5000, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 2, 28), 'description': 'Indemnité spéciale', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_special_indemnity').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf16'].id)], 'monthly_amount': 4000, 'total_amount': 4000, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'description': 'Indemnité spéciale', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_special_indemnity').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf16'].id)], 'monthly_amount': 250, 'total_amount': 250, 'date_start': date(2021, 12, 1), 'date_end': date(2021, 12, 31), 'description': 'Part facultative employeurs IJM', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_optional_ijm').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf16'].id)], 'monthly_amount': 150, 'total_amount': 300, 'date_start': date(2021, 11, 1), 'date_end': date(2021, 12, 31), 'description': '3ème pilier b payé par employeur', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_thirdpillb').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf16'].id)], 'monthly_amount': 150, 'total_amount': 300, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 3, 31), 'description': '3ème pilier b payé par employeur', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_thirdpillb').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf16'].id)], 'monthly_amount': 350, 'total_amount': 700, 'date_start': date(2021, 11, 1), 'date_end': date(2021, 12, 31), 'description': '3ème pilier a payé par employeur', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_thirdpilla').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf16'].id)], 'monthly_amount': 350, 'total_amount': 700, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 3, 31), 'description': '3ème pilier a payé par employeur', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_thirdpilla').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf16'].id)], 'monthly_amount': 500, 'total_amount': 500, 'date_start': date(2021, 11, 1), 'date_end': date(2021, 11, 30), 'description': 'Correction avantage en argent', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_cash_correction').id, 'is_refund': True},
            {'employee_ids': [(4, mapped_employees['employee_tf16'].id)], 'monthly_amount': 750, 'total_amount': 750, 'date_start': date(2021, 12, 1), 'date_end': date(2021, 12, 31), 'description': 'Correction avantage en argent', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_cash_correction').id, 'is_refund': True},
            {'employee_ids': [(4, mapped_employees['employee_tf16'].id)], 'monthly_amount': 500, 'total_amount': 1000, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 3, 31), 'description': 'Correction avantage en argent', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_cash_correction').id, 'is_refund': True},
            {'employee_ids': [(4, mapped_employees['employee_tf16'].id)], 'monthly_amount': 300, 'total_amount': 600, 'date_start': date(2021, 11, 1), 'date_end': date(2021, 12, 31), 'description': 'Frais de voyage', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_travel_expense').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf16'].id)], 'monthly_amount': 600, 'total_amount': 600, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 2, 28), 'description': 'Frais de voyage', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_travel_expense').id, 'is_refund': False},
            {'employee_ids': [(4, mapped_employees['employee_tf16'].id)], 'monthly_amount': 300, 'total_amount': 300, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'description': 'Frais de voyage', 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_travel_expense').id, 'is_refund': False},
            # TF17
            {'employee_ids': [(4, mapped_employees['employee_tf17'].id)], 'monthly_amount': 2000, 'total_amount': 2000 * 1, 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_holiday_bonus').id, 'date_start': date(2022, 11, 1), 'date_end': date(2022, 11, 30), 'description': 'Bonus'},

             # TF18
            {'description': 'Salaire horaire', 'monthly_amount': 35.0, 'total_amount': 280.0, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 8, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf18'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 75, 'total_amount': 75, 'date_start': date(2022, 9, 1), 'date_end': date(2022, 9, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf18'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 62, 'total_amount': 62, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 10, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf18'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 53, 'total_amount': 53, 'date_start': date(2022, 11, 1), 'date_end': date(2022, 11, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf18'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 71, 'total_amount': 71, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf18'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 35, 'total_amount': 70, 'date_start': date(2023, 1, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf18'].id)]},
            {'description': 'Cotisation LPP', 'monthly_amount': 117, 'total_amount': 1638, 'date_start': date(2022, 1, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf18'].id)]},
            # TF19
            # TF20
            {'description': 'Indemnité de départ (soumis AVS)', 'monthly_amount': 500, 'total_amount': 500, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_sevpay').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf20'].id)]},
            # TF21
            {'description': 'Indemnité de départ soumis à l AVS', 'employee_ids': [(4, mapped_employees['employee_tf21'].id)], 'monthly_amount': 500, 'total_amount': 500 * 1, 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_sevpay').id, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31)},

            # TF22
            {'description': 'Salaire horaire', 'monthly_amount': 130.0, 'total_amount': 130.0, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 1, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf22'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 120.0, 'total_amount': 120.0, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf22'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 125.0, 'total_amount': 125.0, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf22'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 135.0, 'total_amount': 135.0, 'date_start': date(2022, 4, 1), 'date_end': date(2022, 4, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf22'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 115.0, 'total_amount': 115.0, 'date_start': date(2022, 5, 1), 'date_end': date(2022, 5, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf22'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 100.0, 'total_amount': 100.0, 'date_start': date(2022, 6, 1), 'date_end': date(2022, 6, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf22'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 140.0, 'total_amount': 140.0, 'date_start': date(2022, 7, 1), 'date_end': date(2022, 7, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf22'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 115.0, 'total_amount': 115.0, 'date_start': date(2022, 8, 1), 'date_end': date(2022, 8, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf22'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 130.0, 'total_amount': 130.0, 'date_start': date(2022, 9, 1), 'date_end': date(2022, 9, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf22'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 90.0, 'total_amount': 90.0, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 10, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf22'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 120.0, 'total_amount': 120.0, 'date_start': date(2022, 11, 1), 'date_end': date(2022, 11, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf22'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 130.0, 'total_amount': 130.0, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf22'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 40.0, 'total_amount': 40.0, 'date_start': date(2023, 1, 1), 'date_end': date(2023, 1, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf22'].id)]},
            {'description': 'Salaire horaire', 'monthly_amount': 96.0, 'total_amount': 96.0, 'date_start': date(2023, 2, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_hourly').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf22'].id)]},
            {'description': 'Allocation pour enfant', 'monthly_amount': 200, 'total_amount': 200, 'date_start': date(2023, 2, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_child_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf22'].id)]},
            {'description': 'Allocation de naissance', 'monthly_amount': 3000, 'total_amount': 3000, 'date_start': date(2023, 2, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_birth_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf22'].id)]},
            # TF23
            {'description': 'Bonus', 'monthly_amount': 30000, 'total_amount': 30000, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_holiday_bonus').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf23'].id)]},
            {'description': 'Allocation pour enfant', 'monthly_amount': 200, 'total_amount': 600, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_child_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf23'].id)]},
            {'description': 'Cotisation LPP', 'monthly_amount': 379, 'total_amount': 4548, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf23'].id)]},
            # TF24
            {'description': 'Cotisation LPP', 'monthly_amount': 607, 'total_amount': 7284, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf24'].id)]},
            # TF25
            # TF26
            # TF27
            {'description': 'Bonus', 'monthly_amount': 30000, 'total_amount': 30000, 'date_start': date(2023, 2, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_holiday_bonus').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf27'].id)]},
            {'description': 'Cotisation LPP', 'monthly_amount': 700, 'total_amount': 5600, 'date_start': date(2022, 5, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf27'].id)]},
            {'description': 'Cotisation LPP', 'monthly_amount': 875, 'total_amount': 1750, 'date_start': date(2023, 1, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf27'].id)]},
            # TF28
            {'description': 'Heures supplémentaires après le départ', 'monthly_amount': 2000, 'total_amount': 2000, 'date_start': date(2023, 1, 1), 'date_end': date(2023, 1, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_overtime_after_departure').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf28'].id)]},
            {'description': 'Paiement des vacances après le départ', 'monthly_amount': 3000, 'total_amount': 3000, 'date_start': date(2023, 1, 1), 'date_end': date(2023, 1, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_holiday_departure').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf28'].id)]},
            {'description': "Paiement de la prime l'année précédente", 'monthly_amount': 15000, 'total_amount': 15000, 'date_start': date(2023, 2, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_prevybonus').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf28'].id)]},
            {'description': "Prime pour proposition d'amélioration", 'monthly_amount': 20000, 'total_amount': 20000, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_impbonus').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf28'].id)]},
            # TF29
            {'description': 'Correction des salaires', 'monthly_amount': 2000, 'total_amount': 2000, 'date_start': date(2023, 1, 1), 'date_end': date(2023, 1, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_salary_correction').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf29'].id)]},
            {'description': 'Heures supplémentaires après le départ', 'monthly_amount': 2000, 'total_amount': 2000, 'date_start': date(2023, 1, 1), 'date_end': date(2023, 1, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_overtime_after_departure').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf29'].id)]},
            {'description': 'Paiement des vacances après le départ', 'monthly_amount': 3000, 'total_amount': 3000, 'date_start': date(2023, 1, 1), 'date_end': date(2023, 1, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_holiday_departure').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf29'].id)]},
            {'description': "Paiement de la prime l'année précédente", 'monthly_amount': 15000, 'total_amount': 15000, 'date_start': date(2023, 2, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_prevybonus').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf29'].id)]},
            {'description': "Prime pour proposition d'amélioration", 'monthly_amount': 20000, 'total_amount': 20000, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_impbonus').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf29'].id)]},
            # TF30
            {'description': 'Paiement des vacances', 'monthly_amount': 500, 'total_amount': 500, 'date_start': date(2022, 11, 1), 'date_end': date(2022, 11, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_vacalw').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf30'].id)]},
            {'description': 'Droits de participation imposables', 'monthly_amount': 5500, 'total_amount': 22000, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 4, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_taxpfee').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf30'].id)]},
            # TF31
            # TF32
            {'description': 'Cotisation LPP', 'monthly_amount': 350, 'total_amount': 2100, 'date_start': date(2022, 9, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf32'].id)]},
            {'description': 'Montant IS correction', 'monthly_amount': 372, 'total_amount': 372, 'date_start': date(2023, 1, 1), 'date_end': date(2023, 1, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_is_correction').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf32'].id)]},
            # TF33
            {'description': 'Allocation pour enfant', 'monthly_amount': 230, 'total_amount': 1380, 'date_start': date(2022, 7, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_child_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf33'].id)]},
            {'description': 'Paiement pour Allocation pour enfant', 'monthly_amount': 690, 'total_amount': 690, 'date_start': date(2022, 7, 1), 'date_end': date(2022, 7, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_childalwpay').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf33'].id)]},
            # TF34
            {'description': 'Allocation pour enfant', 'monthly_amount': 200, 'total_amount': 1200, 'date_start': date(2022, 7, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_child_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf34'].id)]},
            {'description': 'Paiement pour Allocation pour enfant', 'monthly_amount': 600, 'total_amount': 600, 'date_start': date(2022, 7, 1), 'date_end': date(2022, 7, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_childalwpay').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf34'].id)]},
            # TF35
            {'description': "Paiement de la prime l'année précédente", 'monthly_amount': 30000, 'total_amount': 30000, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_prevybonus').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf35'].id)]},
            {'description': 'Allocation pour enfant', 'monthly_amount': 230, 'total_amount': 690, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_child_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf35'].id)]},
            {'description': 'Cotisation LPP', 'monthly_amount': 379, 'total_amount': 4548, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf35'].id)]},
            # TF36
            {'description': "Paiement de la prime l'année précédente", 'monthly_amount': 30000, 'total_amount': 30000, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_prevybonus').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf36'].id)]},
            {'description': 'Allocation pour enfant', 'monthly_amount': 200, 'total_amount': 600, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_child_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf36'].id)]},
            # TF37
            {'description': 'Bonus', 'monthly_amount': 2000, 'total_amount': 2000, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 1, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_holiday_bonus').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf37'].id)]},
            {'description': 'Allocation pour enfant', 'monthly_amount': 230, 'total_amount': 690, 'date_start': date(2021, 11, 1), 'date_end': date(2022, 1, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_child_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf37'].id)]},
            {'description': 'Cotisation LPP', 'monthly_amount': 350, 'total_amount': 700, 'date_start': date(2021, 11, 1), 'date_end': date(2021, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf37'].id)]},
            {'description': 'Cotisation LPP', 'monthly_amount': 362, 'total_amount': 362, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 1, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf37'].id)]},
            # TF38
            {'description': 'Commission', 'monthly_amount': 5000, 'total_amount': 5000, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_commission').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf38'].id)]},
            {'description': 'Commission', 'monthly_amount': 6500, 'total_amount': 6500, 'date_start': date(2022, 6, 1), 'date_end': date(2022, 6, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_commission').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf38'].id)]},
            {'description': 'Commission', 'monthly_amount': 3800, 'total_amount': 3800, 'date_start': date(2022, 9, 1), 'date_end': date(2022, 9, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_commission').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf38'].id)]},
            {'description': 'Commission', 'monthly_amount': 5500, 'total_amount': 5500, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_commission').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf38'].id)]},
            {'description': 'Frais forfaitaires de voiture', 'monthly_amount': 300, 'total_amount': 3600, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_car_fees').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf38'].id)]},
            # TF39
            {'description': 'Honoraires CA', 'monthly_amount': 10000, 'total_amount': 10000, 'date_start': date(2022, 4, 1), 'date_end': date(2022, 4, 30), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_ca_fee').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf39'].id)]},
            # TF40
            {'description': 'Indemnité pour service de piquet', 'monthly_amount': 30500, 'total_amount': 30500, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_oncallalw').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf40'].id)]},
            {'description': 'Indemnité spéciale', 'monthly_amount': 20000, 'total_amount': 20000, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_special_indemnity').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf40'].id)]},
            {'description': 'Indemnité spéciale', 'monthly_amount': 500, 'total_amount': 500, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll_elm.hr_salary_attachment_type_special_indemnity').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf40'].id)]},
            {'description': 'Honoraires CA', 'monthly_amount': 300, 'total_amount': 300, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_ca_fee').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf40'].id)]},
            {'description': 'Honoraires CA', 'monthly_amount': 4000, 'total_amount': 4000, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_ca_fee').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf40'].id)]},
            {'description': 'Honoraires CA', 'monthly_amount': 6150, 'total_amount': 6150, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_ca_fee').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf40'].id)]},
            {'description': 'Allocation pour enfant', 'monthly_amount': 230, 'total_amount': 690, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 3, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_child_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf40'].id)]},
            {'description': 'Allocation pour enfant', 'monthly_amount': 300, 'total_amount': 300, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 10, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_child_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf40'].id)]},
            {'description': 'Allocation pour enfant', 'monthly_amount': 300, 'total_amount': 900, 'date_start': date(2022, 12, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_child_allowance').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf40'].id)]},
            {'description': 'Cotisation LPP', 'monthly_amount': 303, 'total_amount': 606, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf40'].id)]},
            {'description': 'Cotisation LPP', 'monthly_amount': 303, 'total_amount': 303, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 10, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf40'].id)]},
            {'description': 'Cotisation LPP', 'monthly_amount': 303, 'total_amount': 303, 'date_start': date(2022, 12, 1), 'date_end': date(2022, 12, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf40'].id)]},
            {'description': 'Cotisation LPP', 'monthly_amount': 1196, 'total_amount': 2392, 'date_start': date(2023, 1, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_lpp').id, 'is_refund': True, 'employee_ids': [(4, mapped_employees['employee_tf40'].id)]},
            # TF41
            {'description': 'Gratification', 'monthly_amount': 20000, 'total_amount': 20000, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_gratification').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf41'].id)]},
            {'description': 'Cadeau pour ancienneté de service', 'monthly_amount': 30000, 'total_amount': 30000, 'date_start': date(2022, 5, 1), 'date_end': date(2022, 5, 31), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_jubilee_gift').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf41'].id)]},
            # TF42
            {'description': 'Bonus', 'monthly_amount': 30000, 'total_amount': 30000, 'date_start': date(2023, 2, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_holiday_bonus').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf42'].id)]},
            # TF43
            {'description': 'Bonus', 'monthly_amount': 30000, 'total_amount': 30000, 'date_start': date(2023, 2, 1), 'date_end': date(2023, 2, 28), 'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_holiday_bonus').id, 'is_refund': False, 'employee_ids': [(4, mapped_employees['employee_tf43'].id)]},
        ])

        # Generate Contracts
        contracts = self.env['hr.contract'].with_context(tracking_disable=True).create([
            {'name': "Contract For Herz Monica", 'employee_id': mapped_employees['employee_tf01'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'contract_type_id': self.env.ref('l10n_ch_hr_payroll_elm.l10n_ch_contract_type_indefiniteSalaryHrs').id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 3, 31), 'wage_type': "hourly", 'wage': 0, 'hourly_wage': 50.0, 'l10n_ch_lesson_wage': 50.0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_1.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_1.line_ids[0].id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_1.line_ids[1].id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_1.line_ids[2].id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre'},
            {'name': "Contract For Paganini Maria", 'employee_id': mapped_employees['employee_tf02'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'wage_type': "hourly", 'wage': 0, 'hourly_wage': 30.0, 'l10n_ch_lesson_wage': 30, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_accident_insurance_line_id': laa_1.line_ids[0].id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_1.line_ids[1].id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_1.line_ids[1].id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_1.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 30},
            {'name': "Contract full time For Herz Monica", 'employee_id': mapped_employees['employee_tf03'].id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 2, 28), 'wage_type': "monthly", 'wage': 5500, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_accident_insurance_line_id': laa_1.line_ids[0].id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_1.line_ids[2].id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_1.line_ids[2].id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_1.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20},
            {'name': "Contract retired (1/5) For Herz Monica", 'employee_id': mapped_employees['employee_tf03'].id, 'resource_calendar_id': resource_calendar_8_4_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'wage': 1500, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_accident_insurance_line_id': laa_1.line_ids[1].id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_1.line_ids[0].id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_1.line_ids[1].id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_1.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_avs_status': 'retired'},
            {'name': "Contract full time For Frankhauser Markus", 'employee_id': mapped_employees['employee_tf04'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'wage': 30000, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_accident_insurance_line_id': laa_1.line_ids[0].id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_1.line_ids[2].id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_1.line_ids[2].id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_1.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20},
            {'name': "Contract 2/5 For Moser Johann", 'employee_id': mapped_employees['employee_tf05'].id, 'resource_calendar_id': resource_calendar_16_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 4, 30), 'wage_type': "monthly", 'wage': 1350, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_accident_insurance_line_id': laa_1.line_ids[0].id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_1.line_ids[1].id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_1.line_ids[1].id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_1.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20},
            {'name': "Contract Retired 2/5 time For Moser Johann", 'employee_id': mapped_employees['employee_tf05'].id, 'resource_calendar_id': resource_calendar_16_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 5, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'wage': 1350, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_accident_insurance_line_id': laa_1.line_ids[0].id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_1.line_ids[1].id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_1.line_ids[1].id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_1.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_avs_status': 'retired'},
            {'name': "Contract Full time For Zahnd Anita", 'employee_id': mapped_employees['employee_tf06'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 10, 31), 'wage_type': "monthly", 'wage': 13500.00, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_accident_insurance_line_id': laa_1.line_ids[0].id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_1.line_ids[1].id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_1.line_ids[1].id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_1.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20},
            # TF 07
            {'name': "Contract Full Time For Burri Heidi", 'employee_id': mapped_employees['employee_tf07'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2021, 11, 1), 'date_end': date(2021, 12, 31), 'wage_type': "monthly", 'wage': 8000, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_1.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20},
            # TF 08
            {'name': "Contract For Lamon René", 'employee_id': mapped_employees['employee_tf08'].id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "hourly", 'wage': 0, 'hourly_wage': 50.0, 'state': "open", 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_1.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20},
            # TF 09
            {'name': "Contract full time For Estermann Michael", 'employee_id': mapped_employees['employee_tf09'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 9, 30), 'wage_type': "monthly", 'wage': 2000, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_accident_insurance_line_id': laa_A3.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_12.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_1.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_avs_status': 'retired'},
            {'name': "Contract half time For Estermann Michael", 'employee_id': mapped_employees['employee_tf09'].id, 'resource_calendar_id': resource_calendar_21_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'wage': 1000, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_accident_insurance_line_id': laa_A3.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_12.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_1.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_avs_status': 'retired'},
            # TF 10,
            {'name': "Contract For Ganz Heinz", 'employee_id': mapped_employees['employee_tf10'].id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 2, 1), 'date_end': date(2022, 10, 31), 'wage_type': "monthly", 'wage': 6400, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_1.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20},
            # TF11,
            {'name': "Contract 3/10 For Bosshard Peter", 'employee_id': mapped_employees['employee_tf11'].id, 'resource_calendar_id': resource_calendar_12_6_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 5, 31), 'wage_type': "monthly", 'wage': 9600, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id), (4, laac_12.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id), (4, ijm_12.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_1.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20},
            {'name': "Contract 42 Hours For Bosshard Peter", 'employee_id': mapped_employees['employee_tf11'].id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 6, 1), 'wage_type': "monthly", 'wage': 30000.00, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id), (4, laac_12.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id), (4, ijm_12.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_1.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20},
            # TF12,
            {'name': "Regular Contract 42 Hours For Casanova Renato", 'employee_id': mapped_employees['employee_tf12'].id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 2, 27), 'date_end': date(2022, 9, 30), 'wage_type': "monthly", 'wage': 12000.00, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A2.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20},
            {'name': "Regular Contract 42 Hours For Casanova Renato", 'employee_id': mapped_employees['employee_tf12'].id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 12, 31), 'wage_type': "hourly", 'wage': 0, 'hourly_wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_12.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_be_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20},
            # TF13,
            {'name': "Contract For Combertaldi Renato", 'employee_id': mapped_employees['employee_tf13'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'contract_type_id': self.env.ref('l10n_ch_hr_payroll_elm.l10n_ch_contract_type_indefiniteSalaryHrs').id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 2, 28), 'wage_type': "monthly", 'wage': 2000.00, 'hourly_wage': 0.0, 'l10n_ch_lesson_wage': 0.0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_1.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A0.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_avs_status': 'youth'},
            {'name': "Contract For Combertaldi Renato", 'employee_id': mapped_employees['employee_tf13'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'contract_type_id': self.env.ref('l10n_ch_hr_payroll_elm.l10n_ch_contract_type_indefiniteSalaryHrs').id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'wage': 2000.00, 'hourly_wage': 0.0, 'l10n_ch_lesson_wage': 0.0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_1.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_avs_status': 'youth'},
            {'name': "Contract For Combertaldi Renato", 'employee_id': mapped_employees['employee_tf13'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'contract_type_id': self.env.ref('l10n_ch_hr_payroll_elm.l10n_ch_contract_type_indefiniteSalaryHrs').id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2023, 1, 1), 'date_end': False, 'wage_type': "monthly", 'wage': 2000.00, 'hourly_wage': 0.0, 'l10n_ch_lesson_wage': 0.0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_1.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True},
            # TF14,
            {'name': "Contract For Egli Anna", 'employee_id': mapped_employees['employee_tf14'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'contract_type_id': self.env.ref('l10n_ch_hr_payroll_elm.l10n_ch_contract_type_fixedSalaryHrs').id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2021, 11, 1), 'date_end': date(2022, 8, 31), 'wage_type': "hourly", 'wage': 0.0, 'hourly_wage': 25, 'l10n_ch_lesson_wage': 25, 'state': "open", 'l10n_ch_location_unit_id': location_unit_1.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_avs_status': 'exempted'},
            {'name': "Contract 2 For Egli Anna", 'employee_id': mapped_employees['employee_tf14'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_21_hours_per_week.id, 'contract_type_id': self.env.ref('l10n_ch_hr_payroll.l10n_ch_contract_type_internshipContract').id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 9, 1), 'wage_type': "monthly", 'wage': 2500.0, 'hourly_wage': 25, 'l10n_ch_lesson_wage': 25, 'state': "open", 'l10n_ch_location_unit_id': location_unit_1.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_avs_status': 'exempted'},
            # TF15,
            {'name': "Contract For Degelo Lorenz", 'employee_id': mapped_employees['employee_tf15'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'contract_type_id': self.env.ref('l10n_ch_hr_payroll_elm.l10n_ch_contract_type_indefiniteSalaryHrs').id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 2, 28), 'date_end': date(2022, 3, 1), 'wage_type': "hourly", 'wage': 0.0, 'hourly_wage': 0.0, 'l10n_ch_lesson_wage': 2800 / 21, 'state': "open", 'l10n_ch_location_unit_id': location_unit_1.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A3.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True},
            # TF16,
            {'name': "Contract for Aebi Anna", 'employee_id': mapped_employees['employee_tf16'].id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2021, 11, 1), 'date_end': date(2021, 12, 20), 'wage_type': "monthly", 'wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_1.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_12.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_1.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20},
            {'name': "Contract for Aebi Anna", 'employee_id': mapped_employees['employee_tf16'].id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 15), 'date_end': date(2022, 2, 28), 'wage_type': "monthly", 'wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_12.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_1.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_avs_status': 'retired'},
            {'name': "Contract for Aebi Anna", 'employee_id': mapped_employees['employee_tf16'].id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 27), 'wage_type': "monthly", 'wage': 0, 'state': "open", 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_1.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_avs_status': 'retired'},
            # TF17,
            {'name': "Contract For Binggeli Fritz", 'employee_id': mapped_employees['employee_tf17'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_70_percent.id, 'contract_type_id': self.env.ref('l10n_ch_hr_payroll_elm.l10n_ch_contract_type_indefiniteSalaryHrs').id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': False, 'wage_type': "monthly", 'wage': 4550, 'hourly_wage': 0.0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_1.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_other_employers': True, 'l10n_ch_other_employers_occupation_rate': 30, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
            # TF18,
            {'name': "Contract For Blanc Pierre", 'employee_id': mapped_employees['employee_tf18'].id, 'resource_calendar_id': resource_calendar_8_4_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2023, 2, 28), 'wage_type': "hourly", 'wage': 0, 'hourly_wage': 30, 'state': "open", 'l10n_ch_location_unit_id': location_unit_1.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A3.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_be_1.id, 'l10n_ch_thirteen_month': False, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_other_employers': True, 'l10n_ch_other_employers_occupation_rate': 60, 'l10n_ch_has_withholding_tax': True},
            # TF19,
            {'name': "Contract For Andrey Melanie", 'employee_id': mapped_employees['employee_tf19'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_50_percent.id, 'contract_type_id': self.env.ref('l10n_ch_hr_payroll_elm.l10n_ch_contract_type_indefiniteSalaryHrs').id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 3, 31), 'wage_type': "monthly", 'wage': 2600, 'hourly_wage': 0.0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_1.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_other_employers': True, 'l10n_ch_other_employers_occupation_rate': 40, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
            {'name': "Contract For Andrey Melanie", 'employee_id': mapped_employees['employee_tf19'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_50_percent.id, 'contract_type_id': self.env.ref('l10n_ch_hr_payroll_elm.l10n_ch_contract_type_indefiniteSalaryHrs').id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 4, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'wage': 2600, 'hourly_wage': 0.0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_1.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_other_employers': False, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
            # TF20,
            {'name': "Contract For Arnold Lukas", 'employee_id': mapped_employees['employee_tf20'].id, 'resource_calendar_id': resource_calendar_16_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 3, 15), 'wage_type': "monthly", 'wage': 2000, 'state': "open", 'l10n_ch_location_unit_id': location_unit_2.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_be_1.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_other_employers': True, 'l10n_ch_other_employers_occupation_rate': 50, 'l10n_ch_has_withholding_tax': True, 'l10n_ch_monthly_effective_days': 20},
            # TF21,
            {'name': "Contract For Meier Christian", 'employee_id': mapped_employees['employee_tf21'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_percent.id, 'contract_type_id': self.env.ref('l10n_ch_hr_payroll_elm.l10n_ch_contract_type_indefiniteSalaryHrs').id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 3, 15), 'wage_type': "monthly", 'wage': 2000, 'hourly_wage': 0.0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_1.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_other_employers': True, 'l10n_ch_other_employers_occupation_rate': 50, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
            # TF22,
            {'name': "Contract For Bucher Elisabeth", 'employee_id': mapped_employees['employee_tf22'].id, 'resource_calendar_id': resource_calendar_8_4_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'wage_type': "hourly", 'wage': 0, 'hourly_wage': 35, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_ti_1.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_other_employers': False, 'l10n_ch_has_withholding_tax': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
            # TF23,
            {'name': "Contract For Koller Ludwig", 'employee_id': mapped_employees['employee_tf23'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_percent.id, 'contract_type_id': self.env.ref('l10n_ch_hr_payroll_elm.l10n_ch_contract_type_indefiniteSalaryHrs').id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': False, 'wage_type': "monthly", 'wage': 5000, 'hourly_wage': 0.0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_1.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_0.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_other_employers': False, 'l10n_ch_other_employers_occupation_rate': 0, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
            # TF24,
            {'name': "Contract For Bucher Elisabeth", 'employee_id': mapped_employees['employee_tf24'].id, 'resource_calendar_id': resource_calendar_8_4_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'wage': 8000, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_1.id, 'l10n_ch_compensation_fund_id': caf_ti_1.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_other_employers': False, 'l10n_ch_has_withholding_tax': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
            # TF25,
            {'name': "Contract For Lehmann Nadine", 'employee_id': mapped_employees['employee_tf25'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_42_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 2, 10), 'date_end': date(2022, 6, 15), 'wage_type': "monthly", 'wage': 12000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_1.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_12.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_12.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20},
            # TF26,
            {'name': "Contract For Bucher Elisabeth", 'employee_id': mapped_employees['employee_tf26'].id, 'resource_calendar_id': resource_calendar_8_4_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 2, 10), 'date_end': date(2022, 6, 15), 'wage_type': "monthly", 'wage': 12000, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_12.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_12.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_ti_1.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_other_employers': False, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
            # TF27,
            {'name': "Contract For Lehmann Nadine", 'employee_id': mapped_employees['employee_tf27'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 5, 1), 'date_end': date(2023, 2, 28), 'wage_type': "monthly", 'wage': 10000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_2.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_4.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': False, 'l10n_ch_monthly_effective_days': 20},
            # TF28,
            {'name': "Contract For Arbenz Esther", 'employee_id': mapped_employees['employee_tf28'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_24_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'wage': 6000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_2.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_4.id, 'l10n_ch_compensation_fund_id': caf_be_1.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': False, 'l10n_ch_other_employers_occupation_rate': 20, 'l10n_ch_monthly_effective_days': 20},
            # TF29,
            {'name': "Contract For Lehmann Nadine", 'employee_id': mapped_employees['employee_tf29'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_60_percent.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'wage': 6000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_other_employers': True, 'l10n_ch_other_employers_occupation_rate': 20, 'l10n_ch_is_model': 'yearly'},
            # TF30,
            {'name': "Contract For Müller Heinrich", 'employee_id': mapped_employees['employee_tf30'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_0_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 4, 30), 'wage_type': "monthly", 'wage': 0, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_2.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A0.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly', 'l10n_ch_is_predefined_category': 'ME'},
            {'name': "Contract For Müller Heinrich", 'employee_id': mapped_employees['employee_tf30'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 5, 1), 'date_end': date(2022, 9, 30), 'wage_type': "monthly", 'wage': 5500, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_2.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly'},
            # TF31,
            {'name': "Contract For Bolletto Franca", 'employee_id': mapped_employees['employee_tf31'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'wage': 5000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
            # TF32,
            {'name': "Contract For Armanini Laura", 'employee_id': mapped_employees['employee_tf32'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 9, 1), 'date_end': date(2023, 2, 28), 'wage_type': "monthly", 'wage': 5000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_2.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_2.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly'},
            # TF33,
            {'name': "Contract For Châtelain Pierre", 'employee_id': mapped_employees['employee_tf33'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'wage': 5000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly'},
            # TF34,
            {'name': "Contract For Rinaldi Massimo", 'employee_id': mapped_employees['employee_tf34'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'wage': 5000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
            # TF35,
            {'name': "Contract For Roos Roland", 'employee_id': mapped_employees['employee_tf35'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'wage': 5000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_2.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': False, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
            # TF36,
            {'name': "Contract For Maldini Fabio", 'employee_id': mapped_employees['employee_tf36'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 8, 31), 'wage_type': "monthly", 'wage': 5000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly'},
            {'name': "Contract For Maldini Fabio", 'employee_id': mapped_employees['employee_tf36'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 9, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'wage': 5000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
            # TF37,
            {'name': "Contract For Oberli Christine", 'employee_id': mapped_employees['employee_tf37'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2021, 11, 16), 'date_end': date(2021, 12, 10), 'wage_type': "monthly", 'wage': 5000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_2.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': False, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly'},
            {'name': "Contract For Oberli Christine", 'employee_id': mapped_employees['employee_tf37'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2021, 12, 21), 'date_end': date(2022, 1, 18), 'wage_type': "monthly", 'wage': 6000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': lpp_2.id, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': False, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly'},
            # TF38,
            {'name': "Contract For Jung Claude", 'employee_id': mapped_employees['employee_tf38'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'wage': 3000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly'},
            # TF39,
            {'name': "Contract For Hasler Harald", 'employee_id': mapped_employees['employee_tf39'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 12, 31), 'wage_type': "monthly", 'wage': 0, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_2.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A0.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly', 'l10n_ch_avs_status': 'exempted', 'l10n_ch_is_predefined_category': 'HE'},
            # TF40,
            {'name': "Contract For Farine Corinne", 'employee_id': mapped_employees['employee_tf40'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 2, 28), 'wage_type': "monthly", 'wage': 4000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_12.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly'},
            {'name': "Contract For Farine Corinne", 'employee_id': mapped_employees['employee_tf40'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_0_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 3, 1), 'date_end': date(2022, 3, 31), 'wage_type': "monthly", 'wage': 0, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A0.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly'},
            {'name': "Contract For Farine Corinne", 'employee_id': mapped_employees['employee_tf40'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 10, 1), 'date_end': date(2022, 10, 31), 'wage_type': "monthly", 'wage': 4000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
            {'name': "Contract For Farine Corinne", 'employee_id': mapped_employees['employee_tf40'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 12, 1), 'date_end': date(2023, 2, 28), 'wage_type': "monthly", 'wage': 4000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_11.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_11.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
            # TF41,
            {'name': "Contract For Meier Max", 'employee_id': mapped_employees['employee_tf41'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 1, 1), 'date_end': date(2022, 3, 31), 'wage_type': "monthly", 'wage': 10000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
            {'name': "Contract For Meier Max", 'employee_id': mapped_employees['employee_tf41'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 7, 1), 'date_end': date(2022, 7, 31), 'wage_type': "monthly", 'wage': 10000, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
            # TF42,
            {'name': "Contract For Peters Otto", 'employee_id': mapped_employees['employee_tf42'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 11, 1), 'date_end': date(2022, 12, 15), 'wage_type': "monthly", 'wage': 6666.65, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_4.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'yearly'},
            # TF43,
            {'name': "Contract For Ochsenbein Lea", 'employee_id': mapped_employees['employee_tf43'].id, 'job_id': job_1.id, 'resource_calendar_id': resource_calendar_40_hours_per_week.id, 'company_id': self.id, 'date_generated_from': datetime(2020, 9, 1, 0, 0, 0), 'date_generated_to': datetime(2020, 9, 1, 0, 0, 0), 'structure_type_id': self.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id, 'date_start': date(2022, 11, 1), 'date_end': date(2022, 12, 15), 'wage_type': "monthly", 'wage': 6666.65, 'hourly_wage': 0, 'l10n_ch_lesson_wage': 0, 'state': "open", 'l10n_ch_location_unit_id': location_unit_2.id, 'l10n_ch_social_insurance_id': avs_2.id, 'l10n_ch_accident_insurance_line_id': laa_A1.id, 'l10n_ch_additional_accident_insurance_line_ids': [(4, laac_10.id)], 'l10n_ch_sickness_insurance_line_ids': [(4, ijm_10.id)], 'l10n_ch_lpp_insurance_id': False, 'l10n_ch_compensation_fund_id': caf_lu_2.id, 'l10n_ch_thirteen_month': True, 'l10n_ch_yearly_holidays': 20, 'l10n_ch_job_type': 'lowerCadre', 'l10n_ch_lpp_not_insured': True, 'l10n_ch_monthly_effective_days': 20, 'l10n_ch_is_model': 'monthly'},
        ])
        contracts_by_employee = defaultdict(lambda: self.env['hr.contract'])
        for contract in contracts:
            contracts_by_employee[contract.employee_id] += contract
        mapped_contracts = {}
        for eidx, employee in enumerate(employees, start=1):
            for cidx, contract in enumerate(contracts_by_employee[employee], start=1):
                mapped_contracts[f"contract_tf{str(eidx).zfill(2)}_{str(cidx).zfill(2)}"] = contract
        contracts.generate_work_entries(date(2021, 11, 1), date(2023, 2, 28))
        # after many insertions in work_entries, table statistics may be broken.
        # In this case, query plan may be randomly suboptimal leading to slow search
        # Analyzing the table is fast, and will transform a potential ~30 seconds
        # sql time for _mark_conflicting_work_entries into ~2 seconds
        self.env.cr.execute('ANALYZE hr_work_entry')

        # Generate Payslips

        # 2021-11
        mapped_payslips = {}
        mapped_payslips['payslip_tf07_2021_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf07_01'], date(2021, 11, 1), date(2021, 11, 30))
        mapped_payslips['payslip_tf14_2021_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf14_01'], date(2021, 11, 1), date(2021, 11, 30), thirteen_month=True)
        mapped_payslips['payslip_tf16_2021_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf16_01'], date(2021, 11, 1), date(2021, 11, 30))
        mapped_payslips['payslip_tf37_2021_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf37_01'], date(2021, 11, 1), date(2021, 11, 30), basic=5000)
        self._l10n_ch_compute_swissdec_demo_paylips(date(2021, 11, 1))

        # 2021-12
        mapped_employees['employee_tf14'].write({'l10n_ch_tax_scale': 'N', 'l10n_ch_has_withholding_tax': False})
        self.env['hr.employee.is.line'].create({'employee_id': mapped_employees['employee_tf14'].id, 'valid_as_of': date(2021, 11, 1), 'correction_date': date(2021, 12, 1), 'payslips_to_correct': mapped_payslips['payslip_tf14_2021_11'].ids})
        mapped_contracts['contract_tf18_01'].write({'l10n_ch_current_occupation_rate': 19.23})
        mapped_payslips['payslip_tf07_2021_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf07_01'], date(2021, 12, 1), date(2021, 12, 31))
        mapped_payslips['payslip_tf14_2021_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf14_01'], date(2021, 12, 1), date(2021, 12, 31), thirteen_month=True)
        mapped_payslips['payslip_tf16_2021_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf16_01'], date(2021, 12, 1), date(2021, 12, 31))
        mapped_payslips['payslip_tf37_2021_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf37_02'], date(2021, 12, 1), date(2021, 12, 31), basic=6000, as_days=20)  # this feels a bit hacky, find the logic behind
        self._l10n_ch_compute_swissdec_demo_paylips(date(2021, 12, 1))
        contracts.filtered(lambda c: not c.date_end or not c.date_end < date(2022, 1, 1)).write(
            {
                'l10n_ch_social_insurance_id': avs_2.id
            }
        )
        # 2022-01
        mapped_payslips['payslip_tf01_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf01_01'], date(2022, 1, 1), date(2022, 1, 31), thirteen_month=True)
        mapped_payslips['payslip_tf02_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf02_01'], date(2022, 1, 1), date(2022, 1, 31), thirteen_month=True)
        mapped_payslips['payslip_tf03_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf03_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf04_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf04_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf05_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf05_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf06_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf06_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf07_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf07_01'], date(2022, 1, 1), date(2022, 1, 31), after_payment="N")
        mapped_payslips['payslip_tf08_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf08_01'], date(2022, 1, 1), date(2022, 1, 31), thirteen_month=True)
        mapped_payslips['payslip_tf09_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf09_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf11_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf11_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf13_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf13_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf14_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf14_01'], date(2022, 1, 1), date(2022, 1, 31), thirteen_month=True)
        mapped_payslips['payslip_tf16_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf16_02'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf17_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf17_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf18_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf18_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf19_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf19_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf20_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf20_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf21_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf21_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf22_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf22_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf23_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf23_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf24_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf24_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf28_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf28_01'], date(2022, 1, 1), date(2022, 1, 31), ch_days=15)
        mapped_payslips['payslip_tf29_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf29_01'], date(2022, 1, 1), date(2022, 1, 31), ch_days=15)
        mapped_payslips['payslip_tf30_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf30_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf31_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf31_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf33_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf33_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf34_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf34_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf35_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf35_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf36_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf36_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf37_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf37_02'], date(2022, 1, 1), date(2022, 1, 31), basic=3000)
        mapped_payslips['payslip_tf38_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf38_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf39_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf39_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf40_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf40_01'], date(2022, 1, 1), date(2022, 1, 31))
        mapped_payslips['payslip_tf41_2022_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf41_01'], date(2022, 1, 1), date(2022, 1, 31))
        self._l10n_ch_compute_swissdec_demo_paylips(date(2022, 1, 1))

        # 2022-02
        mapped_payslips['payslip_tf01_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf01_01'], date(2022, 2, 1), date(2022, 2, 28), thirteen_month=True)
        mapped_payslips['payslip_tf02_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf02_01'], date(2022, 2, 1), date(2022, 2, 28), thirteen_month=True)
        mapped_payslips['payslip_tf03_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf03_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf04_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf04_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf05_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf05_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf06_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf06_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf07_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf07_01'], date(2022, 2, 1), date(2022, 2, 28), after_payment="N")
        mapped_payslips['payslip_tf08_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf08_01'], date(2022, 2, 1), date(2022, 2, 28), thirteen_month=True)
        mapped_payslips['payslip_tf09_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf09_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf10_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf10_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf11_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf11_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf12_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf12_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf13_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf13_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf14_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf14_01'], date(2022, 2, 1), date(2022, 2, 28), thirteen_month=True)
        mapped_payslips['payslip_tf15_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf15_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf16_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf16_02'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf17_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf17_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf18_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf18_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf19_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf19_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf20_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf20_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf21_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf21_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf22_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf22_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf23_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf23_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf24_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf24_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf25_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf25_01'], date(2022, 2, 1), date(2022, 2, 28), basic=8000, ch_days=10, work_days=14)
        mapped_payslips['payslip_tf26_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf26_01'], date(2022, 2, 1), date(2022, 2, 28), basic=8000, ch_days=10, work_days=14)
        mapped_payslips['payslip_tf28_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf28_01'], date(2022, 2, 1), date(2022, 2, 28), ch_days=10)
        mapped_payslips['payslip_tf29_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf29_01'], date(2022, 2, 1), date(2022, 2, 28), ch_days=10)
        mapped_payslips['payslip_tf30_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf30_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf31_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf31_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf33_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf33_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf34_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf34_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf35_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf35_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf36_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf36_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf38_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf38_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf39_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf39_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf40_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf40_01'], date(2022, 2, 1), date(2022, 2, 28))
        mapped_payslips['payslip_tf41_2022_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf41_01'], date(2022, 2, 1), date(2022, 2, 28))
        self._l10n_ch_compute_swissdec_demo_paylips(date(2022, 2, 1))

        # 2022-03
        mapped_employees['employee_tf01'].active = False
        mapped_employees['employee_tf01'].departure_date = date(2022, 3, 31)
        mapped_payslips['payslip_tf01_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf01_01'], date(2022, 3, 1), date(2022, 3, 31), thirteen_month=True)
        mapped_payslips['payslip_tf02_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf02_01'], date(2022, 3, 1), date(2022, 3, 31), thirteen_month=True)
        mapped_payslips['payslip_tf03_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf03_02'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf04_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf04_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf05_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf05_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf06_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf06_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf08_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf08_01'], date(2022, 3, 1), date(2022, 3, 31), thirteen_month=True)
        mapped_payslips['payslip_tf09_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf09_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf10_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf10_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf11_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf11_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf12_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf12_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf13_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf13_02'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf14_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf14_01'], date(2022, 3, 1), date(2022, 3, 31), thirteen_month=True)
        mapped_payslips['payslip_tf15_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf15_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf16_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf16_03'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf17_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf17_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf18_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf18_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf19_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf19_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf20_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf20_01'], date(2022, 3, 1), date(2022, 3, 31), thirteen_month=True)
        mapped_payslips['payslip_tf21_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf21_01'], date(2022, 3, 1), date(2022, 3, 31), thirteen_month=True)
        mapped_payslips['payslip_tf22_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf22_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf23_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf23_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf24_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf24_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf25_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf25_01'], date(2022, 3, 1), date(2022, 3, 31), ch_days=9)
        mapped_payslips['payslip_tf26_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf26_01'], date(2022, 3, 1), date(2022, 3, 31), ch_days=9)
        mapped_payslips['payslip_tf28_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf28_01'], date(2022, 3, 1), date(2022, 3, 31), ch_days=11)
        mapped_payslips['payslip_tf29_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf29_01'], date(2022, 3, 1), date(2022, 3, 31), ch_days=11)
        mapped_payslips['payslip_tf30_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf30_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf31_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf31_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf33_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf33_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf34_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf34_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf35_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf35_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf36_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf36_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf38_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf38_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf39_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf39_01'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf40_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf40_02'], date(2022, 3, 1), date(2022, 3, 31))
        mapped_payslips['payslip_tf41_2022_03'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf41_01'], date(2022, 3, 1), date(2022, 3, 31))
        self._l10n_ch_compute_swissdec_demo_paylips(date(2022, 3, 1))

        # 2022-04
        mapped_employees['employee_tf40'].write({'l10n_ch_canton': "VD"})
        mapped_payslips['payslip_tf02_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf02_01'], date(2022, 4, 1), date(2022, 4, 30), thirteen_month=True)
        mapped_payslips['payslip_tf03_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf03_02'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf04_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf04_01'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf05_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf05_01'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf06_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf06_01'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf08_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf08_01'], date(2022, 4, 1), date(2022, 4, 30), thirteen_month=True)
        mapped_payslips['payslip_tf09_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf09_01'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf10_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf10_01'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf11_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf11_01'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf12_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf12_01'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf13_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf13_02'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf14_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf14_01'], date(2022, 4, 1), date(2022, 4, 30), thirteen_month=True)
        mapped_payslips['payslip_tf17_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf17_01'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf18_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf18_01'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf19_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf19_02'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf22_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf22_01'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf23_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf23_01'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf24_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf24_01'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf25_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf25_01'], date(2022, 4, 1), date(2022, 4, 30), ch_days=18)
        mapped_payslips['payslip_tf26_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf26_01'], date(2022, 4, 1), date(2022, 4, 30), ch_days=18)
        mapped_payslips['payslip_tf28_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf28_01'], date(2022, 4, 1), date(2022, 4, 30), ch_days=14)
        mapped_payslips['payslip_tf29_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf29_01'], date(2022, 4, 1), date(2022, 4, 30), ch_days=14)
        mapped_payslips['payslip_tf30_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf30_01'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf31_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf31_01'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf33_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf33_01'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf34_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf34_01'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf35_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf35_01'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf36_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf36_01'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf38_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf38_01'], date(2022, 4, 1), date(2022, 4, 30))
        mapped_payslips['payslip_tf39_2022_04'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf39_01'], date(2022, 4, 1), date(2022, 4, 30))
        self._l10n_ch_compute_swissdec_demo_paylips(date(2022, 4, 1))

        # 2022-05
        mapped_employees['employee_tf30'].write({'private_street': 'Junkerngasse 42', 'private_zip': '3011', 'private_city': 'Bern', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': 351, 'l10n_ch_canton': 'BE', 'l10n_ch_residence_category': 'annual-B', 'lang': 'fr_FR'})
        mapped_payslips['payslip_tf01_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf01_01'], date(2022, 5, 1), date(2022, 5, 31), thirteen_month=True, after_payment="N")
        mapped_payslips['payslip_tf02_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf02_01'], date(2022, 5, 1), date(2022, 5, 31), thirteen_month=True)
        mapped_payslips['payslip_tf03_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf03_02'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf04_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf04_01'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf05_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf05_02'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf06_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf06_01'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf08_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf08_01'], date(2022, 5, 1), date(2022, 5, 31), thirteen_month=True)
        mapped_payslips['payslip_tf09_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf09_01'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf10_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf10_01'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf11_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf11_01'], date(2022, 5, 1), date(2022, 5, 31), thirteen_month=True)
        mapped_payslips['payslip_tf12_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf12_01'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf13_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf13_02'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf14_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf14_01'], date(2022, 5, 1), date(2022, 5, 31), thirteen_month=True)
        mapped_payslips['payslip_tf17_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf17_01'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf18_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf18_01'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf19_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf19_02'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf22_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf22_01'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf23_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf23_01'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf24_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf24_01'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf25_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf25_01'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf26_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf26_01'], date(2022, 5, 1), date(2022, 5, 31), ch_days=0)
        mapped_payslips['payslip_tf27_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf27_01'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf28_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf28_01'], date(2022, 5, 1), date(2022, 5, 31), ch_days=20)
        mapped_payslips['payslip_tf29_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf29_01'], date(2022, 5, 1), date(2022, 5, 31), ch_days=20)
        mapped_payslips['payslip_tf30_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf30_02'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf31_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf31_01'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf33_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf33_01'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf34_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf34_01'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf35_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf35_01'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf36_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf36_01'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf38_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf38_01'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf39_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf39_01'], date(2022, 5, 1), date(2022, 5, 31))
        mapped_payslips['payslip_tf41_2022_05'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf41_01'], date(2022, 5, 1), date(2022, 5, 31), after_payment='N')
        self._l10n_ch_compute_swissdec_demo_paylips(date(2022, 5, 1))

        # 2022-06
        mapped_employees['employee_tf23'].write({'marital': 'married', 'l10n_ch_marital_from': date(2022, 5, 8), 'l10n_ch_tax_scale': 'B'})
        mapped_employees['employee_tf31'].write({"l10n_ch_tax_scale": 'B'})
        self.env['hr.employee.is.line'].create({'employee_id': mapped_employees['employee_tf31'].id, 'valid_as_of': date(2022, 4, 1), 'correction_date': date(2022, 6, 1), 'payslips_to_correct': (mapped_payslips['payslip_tf31_2022_04'] + mapped_payslips['payslip_tf31_2022_05']).ids})
        mapped_employees['employee_tf33'].write({"l10n_ch_tax_scale": 'B'})
        self.env['hr.employee.is.line'].create({'employee_id': mapped_employees['employee_tf33'].id, 'valid_as_of': date(2022, 4, 1), 'correction_date': date(2022, 6, 1), 'payslips_to_correct': (mapped_payslips['payslip_tf33_2022_04'] + mapped_payslips['payslip_tf33_2022_05']).ids})
        mapped_employees['employee_tf34'].write({"l10n_ch_tax_scale": 'B'})
        self.env['hr.employee.is.line'].create({'employee_id': mapped_employees['employee_tf34'].id, 'valid_as_of': date(2022, 4, 1), 'correction_date': date(2022, 6, 1), 'payslips_to_correct': (mapped_payslips['payslip_tf34_2022_04'] + mapped_payslips['payslip_tf34_2022_05']).ids})
        mapped_employees['employee_tf35'].write({'l10n_ch_tax_scale': 'B'})
        mapped_employees['employee_tf36'].write({'l10n_ch_tax_scale': 'B'})
        mapped_payslips['payslip_tf02_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf02_01'], date(2022, 6, 1), date(2022, 6, 30), thirteen_month=True)
        mapped_payslips['payslip_tf03_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf03_02'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf04_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf04_01'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf05_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf05_02'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf06_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf06_01'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf08_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf08_01'], date(2022, 6, 1), date(2022, 6, 30), thirteen_month=True)
        mapped_payslips['payslip_tf09_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf09_01'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf10_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf10_01'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf11_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf11_02'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf12_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf12_01'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf13_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf13_02'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf14_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf14_01'], date(2022, 6, 1), date(2022, 6, 30), thirteen_month=True)
        mapped_payslips['payslip_tf17_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf17_01'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf18_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf18_01'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf19_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf19_02'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf22_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf22_01'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf23_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf23_01'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf24_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf24_01'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf25_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf25_01'], date(2022, 6, 1), date(2022, 6, 30), ch_days=10, thirteen_month=True, thirteen_force=4166.65)
        mapped_payslips['payslip_tf26_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf26_01'], date(2022, 6, 1), date(2022, 6, 30), ch_days=7, thirteen_month=True, thirteen_force=4166.65)
        mapped_payslips['payslip_tf27_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf27_01'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf28_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf28_01'], date(2022, 6, 1), date(2022, 6, 30), ch_days=11)
        mapped_payslips['payslip_tf29_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf29_01'], date(2022, 6, 1), date(2022, 6, 30), ch_days=11)
        mapped_payslips['payslip_tf30_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf30_02'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf31_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf31_01'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf33_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf33_01'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf34_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf34_01'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf35_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf35_01'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf36_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf36_01'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf38_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf38_01'], date(2022, 6, 1), date(2022, 6, 30))
        mapped_payslips['payslip_tf39_2022_06'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf39_01'], date(2022, 6, 1), date(2022, 6, 30))
        self._l10n_ch_compute_swissdec_demo_paylips(date(2022, 6, 1))

        # 2022-07
        mapped_employees['employee_tf22'].write({'marital': 'married', 'l10n_ch_marital_from': date(2022, 6, 26), 'l10n_ch_tax_scale': 'C'})
        mapped_contracts['contract_tf24_01'].write({'wage': 11000})
        mapped_employees['employee_tf33'].write({"children": 1})
        self.env['hr.employee.is.line'].create({'employee_id': mapped_employees['employee_tf33'].id, 'valid_as_of': date(2022, 5, 1), 'correction_date': date(2022, 7, 1), 'payslips_to_correct': (mapped_payslips['payslip_tf33_2022_05'] + mapped_payslips['payslip_tf33_2022_06']).ids})
        mapped_employees['employee_tf34'].write({"children": 1})
        self.env['hr.employee.is.line'].create({'employee_id': mapped_employees['employee_tf34'].id, 'valid_as_of': date(2022, 5, 1), 'correction_date': date(2022, 7, 1), 'payslips_to_correct': (mapped_payslips['payslip_tf34_2022_05'] + mapped_payslips['payslip_tf34_2022_06']).ids})
        mapped_payslips['payslip_tf02_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf02_01'], date(2022, 7, 1), date(2022, 7, 31), thirteen_month=True)
        mapped_payslips['payslip_tf03_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf03_02'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf04_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf04_01'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf05_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf05_02'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf06_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf06_01'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf08_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf08_01'], date(2022, 7, 1), date(2022, 7, 31), thirteen_month=True)
        mapped_payslips['payslip_tf09_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf09_01'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf10_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf10_01'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf11_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf11_02'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf12_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf12_01'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf13_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf13_02'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf14_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf14_01'], date(2022, 7, 1), date(2022, 7, 31), thirteen_month=True)
        mapped_payslips['payslip_tf17_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf17_01'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf18_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf18_01'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf19_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf19_02'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf22_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf22_01'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf23_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf23_01'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf24_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf24_01'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf27_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf27_01'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf28_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf28_01'], date(2022, 7, 1), date(2022, 7, 31), ch_days=8)
        mapped_payslips['payslip_tf29_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf29_01'], date(2022, 7, 1), date(2022, 7, 31), ch_days=8)
        mapped_payslips['payslip_tf30_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf30_02'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf31_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf31_01'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf33_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf33_01'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf34_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf34_01'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf35_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf35_01'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf36_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf36_01'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf38_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf38_01'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf39_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf39_01'], date(2022, 7, 1), date(2022, 7, 31))
        mapped_payslips['payslip_tf41_2022_07'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf41_02'], date(2022, 7, 1), date(2022, 7, 31))
        self._l10n_ch_compute_swissdec_demo_paylips(date(2022, 7, 1))

        # 2022-08
        mapped_employees['employee_tf36'].write({'l10n_ch_tax_scale': 'C'})
        mapped_payslips['payslip_tf02_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf02_01'], date(2022, 8, 1), date(2022, 8, 31), thirteen_month=True)
        mapped_payslips['payslip_tf03_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf03_02'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf04_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf04_01'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf05_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf05_02'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf06_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf06_01'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf08_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf08_01'], date(2022, 8, 1), date(2022, 8, 31), thirteen_month=True)
        mapped_payslips['payslip_tf09_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf09_01'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf10_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf10_01'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf11_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf11_02'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf12_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf12_01'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf13_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf13_02'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf14_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf14_01'], date(2022, 8, 1), date(2022, 8, 31), thirteen_month=True)
        mapped_payslips['payslip_tf17_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf17_01'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf18_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf18_01'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf19_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf19_02'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf22_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf22_01'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf23_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf23_01'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf24_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf24_01'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf27_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf27_01'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf28_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf28_01'], date(2022, 8, 1), date(2022, 8, 31), ch_days=13)
        mapped_payslips['payslip_tf29_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf29_01'], date(2022, 8, 1), date(2022, 8, 31), ch_days=13)
        mapped_payslips['payslip_tf30_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf30_02'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf31_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf31_01'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf33_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf33_01'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf34_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf34_01'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf35_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf35_01'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf36_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf36_01'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf38_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf38_01'], date(2022, 8, 1), date(2022, 8, 31))
        mapped_payslips['payslip_tf39_2022_08'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf39_01'], date(2022, 8, 1), date(2022, 8, 31))
        self._l10n_ch_compute_swissdec_demo_paylips(date(2022, 8, 1))

        # 2022-09
        mapped_contracts['contract_tf18_01'].write({'l10n_ch_current_occupation_rate': 41.21, 'hourly_wage': 35})
        mapped_contracts['contract_tf35_01'].write({'l10n_ch_lpp_insurance_id': lpp_3.id, 'l10n_ch_is_model': 'monthly'})
        mapped_employees['employee_tf35'].write({'private_street': "Blockweg 2", 'private_zip': '3007', 'private_city': 'Bern', 'private_country_id': self.env.ref('base.ch').id, 'l10n_ch_municipality': '351', 'l10n_ch_canton': 'BE'})
        mapped_employees['employee_tf36'].write({'private_street': 'Via Milano 26', 'private_zip': '22100', 'private_city': 'Como', 'private_country_id': self.env.ref('base.it').id, 'l10n_ch_municipality': False, 'l10n_ch_canton': 'EX', 'l10n_ch_residence_category': 'crossBorder-G', 'l10n_ch_tax_scale': "T"})
        mapped_payslips['payslip_tf02_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf02_01'], date(2022, 9, 1), date(2022, 9, 30), thirteen_month=True)
        mapped_payslips['payslip_tf03_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf03_02'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf04_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf04_01'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf05_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf05_02'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf06_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf06_01'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf08_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf08_01'], date(2022, 9, 1), date(2022, 9, 30), thirteen_month=True)
        mapped_payslips['payslip_tf09_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf09_01'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf10_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf10_01'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf11_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf11_02'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf12_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf12_01'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf13_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf13_02'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf14_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf14_02'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf17_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf17_01'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf18_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf18_01'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf19_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf19_02'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf22_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf22_01'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf23_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf23_01'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf24_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf24_01'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf27_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf27_01'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf28_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf28_01'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf29_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf29_01'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf30_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf30_02'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf31_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf31_01'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf32_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf32_01'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf33_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf33_01'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf34_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf34_01'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf35_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf35_01'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf36_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf36_02'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf38_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf38_01'], date(2022, 9, 1), date(2022, 9, 30))
        mapped_payslips['payslip_tf39_2022_09'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf39_01'], date(2022, 9, 1), date(2022, 9, 30))
        self._l10n_ch_compute_swissdec_demo_paylips(date(2022, 9, 1))

        # 2022-10
        mapped_contracts['contract_tf02_01'].l10n_ch_avs_status = "retired"
        mapped_contracts['contract_tf18_01'].write({'l10n_ch_current_occupation_rate': 34.07})
        mapped_employees['employee_tf24'].write({'l10n_ch_tax_scale': 'C'})
        self.env['hr.employee.is.line'].create({'employee_id': mapped_employees['employee_tf30'].id, 'valid_as_of': date(2022, 9, 1), 'correction_date': date(2023, 11, 1), 'payslips_to_correct': mapped_payslips['payslip_tf30_2022_09'].ids})
        mapped_employees['employee_tf36'].write({'l10n_ch_tax_scale': "F"})
        mapped_payslips['payslip_tf01_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf01_01'], date(2022, 10, 1), date(2022, 10, 31), thirteen_month=True, after_payment="N")
        mapped_payslips['payslip_tf02_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf02_01'], date(2022, 10, 1), date(2022, 10, 31), thirteen_month=True)
        mapped_payslips['payslip_tf03_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf03_02'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf04_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf04_01'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf05_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf05_02'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf06_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf06_01'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf08_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf08_01'], date(2022, 10, 1), date(2022, 10, 31), thirteen_month=True)
        mapped_payslips['payslip_tf09_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf09_02'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf10_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf10_01'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf11_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf11_02'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf12_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf12_02'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf13_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf13_02'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf14_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf14_02'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf17_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf17_01'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf18_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf18_01'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf19_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf19_02'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf22_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf22_01'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf23_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf23_01'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf24_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf24_01'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf27_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf27_01'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf28_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf28_01'], date(2022, 10, 1), date(2022, 10, 31), ch_days=7)
        mapped_payslips['payslip_tf29_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf29_01'], date(2022, 10, 1), date(2022, 10, 31), ch_days=7)
        mapped_payslips['payslip_tf31_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf31_01'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf32_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf32_01'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf33_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf33_01'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf34_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf34_01'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf35_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf35_01'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf36_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf36_02'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf38_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf38_01'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf39_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf39_01'], date(2022, 10, 1), date(2022, 10, 31))
        mapped_payslips['payslip_tf40_2022_10'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf40_03'], date(2022, 10, 1), date(2022, 10, 31))
        self._l10n_ch_compute_swissdec_demo_paylips(date(2022, 10, 1))

        # 2022-11
        mapped_contracts['contract_tf14_02'].write({'l10n_ch_accident_insurance_line_id': laa_A2.id})
        mapped_contracts['contract_tf18_01'].write({'l10n_ch_current_occupation_rate': 29.12})
        mapped_employees['employee_tf23'].write({'children': 1})
        mapped_employees['employee_tf35'].write({"children": 1})
        mapped_employees['employee_tf36'].write({"children": 1})
        mapped_contracts['contract_tf38_01'].write({'l10n_ch_is_predefined_category': "SF"})
        mapped_employees['employee_tf40'].write({'children': 2})
        mapped_payslips['payslip_tf02_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf02_01'], date(2022, 11, 1), date(2022, 11, 30), thirteen_month=True)
        mapped_payslips['payslip_tf03_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf03_02'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf04_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf04_01'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf05_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf05_02'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf08_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf08_01'], date(2022, 11, 1), date(2022, 11, 30), thirteen_month=True)
        mapped_payslips['payslip_tf09_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf09_02'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf10_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf10_01'], date(2022, 11, 1), date(2022, 11, 30), after_payment='N')
        mapped_payslips['payslip_tf11_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf11_02'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf12_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf12_02'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf13_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf13_02'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf14_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf14_02'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf17_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf17_01'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf18_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf18_01'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf19_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf19_02'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf22_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf22_01'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf23_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf23_01'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf24_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf24_01'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf27_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf27_01'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf28_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf28_01'], date(2022, 11, 1), date(2022, 11, 30), ch_days=16)
        mapped_payslips['payslip_tf29_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf29_01'], date(2022, 11, 1), date(2022, 11, 30), ch_days=16)
        mapped_payslips['payslip_tf30_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf30_02'], date(2022, 11, 1), date(2022, 11, 30), after_payment='NK')
        mapped_payslips['payslip_tf31_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf31_01'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf32_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf32_01'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf33_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf33_01'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf34_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf34_01'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf35_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf35_01'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf36_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf36_02'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf38_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf38_01'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf39_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf39_01'], date(2022, 11, 1), date(2022, 11, 30))
        mapped_payslips['payslip_tf42_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf42_01'], date(2022, 11, 1), date(2022, 11, 30), ch_days=12)
        mapped_payslips['payslip_tf43_2022_11'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf43_01'], date(2022, 11, 1), date(2022, 11, 30), ch_days=12)
        self._l10n_ch_compute_swissdec_demo_paylips(date(2022, 11, 1))

        # 2022-12
        mapped_contracts['contract_tf18_01'].write({'l10n_ch_current_occupation_rate': 39.01})
        mapped_employees['employee_tf24'].write({'l10n_ch_tax_scale': False, 'l10n_ch_has_withholding_tax': False})
        mapped_payslips['payslip_tf02_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf02_01'], date(2022, 12, 1), date(2022, 12, 31), thirteen_month=True)
        mapped_payslips['payslip_tf03_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf03_02'], date(2022, 12, 1), date(2022, 12, 31))
        mapped_payslips['payslip_tf04_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf04_01'], date(2022, 12, 1), date(2022, 12, 31), thirteen_month=True)
        mapped_payslips['payslip_tf05_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf05_02'], date(2022, 12, 1), date(2022, 12, 31), thirteen_month=True)
        mapped_payslips['payslip_tf08_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf08_01'], date(2022, 12, 1), date(2022, 12, 31), thirteen_month=True)
        mapped_payslips['payslip_tf09_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf09_02'], date(2022, 12, 1), date(2022, 12, 31))
        mapped_payslips['payslip_tf10_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf10_01'], date(2022, 12, 1), date(2022, 12, 31), after_payment='N')
        mapped_payslips['payslip_tf11_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf11_02'], date(2022, 12, 1), date(2022, 12, 31), thirteen_month=True)
        mapped_payslips['payslip_tf12_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf12_02'], date(2022, 12, 1), date(2022, 12, 31))
        mapped_payslips['payslip_tf13_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf13_02'], date(2022, 12, 1), date(2022, 12, 31))
        mapped_payslips['payslip_tf14_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf14_02'], date(2022, 12, 1), date(2022, 12, 31))
        mapped_payslips['payslip_tf17_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf17_01'], date(2022, 12, 1), date(2022, 12, 31))
        mapped_payslips['payslip_tf18_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf18_01'], date(2022, 12, 1), date(2022, 12, 31))
        mapped_payslips['payslip_tf19_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf19_02'], date(2022, 12, 1), date(2022, 12, 31), thirteen_month=True)
        mapped_payslips['payslip_tf22_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf22_01'], date(2022, 12, 1), date(2022, 12, 31))
        mapped_payslips['payslip_tf23_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf23_01'], date(2022, 12, 1), date(2022, 12, 31), thirteen_month=True)
        mapped_payslips['payslip_tf24_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf24_01'], date(2022, 12, 1), date(2022, 12, 31), thirteen_month=True, thirteen_force=9500)
        mapped_payslips['payslip_tf27_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf27_01'], date(2022, 12, 1), date(2022, 12, 31))
        mapped_payslips['payslip_tf28_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf28_01'], date(2022, 12, 1), date(2022, 12, 31), ch_days=9, thirteen_month=True)
        mapped_payslips['payslip_tf29_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf29_01'], date(2022, 12, 1), date(2022, 12, 31), ch_days=9, thirteen_month=True)
        mapped_payslips['payslip_tf31_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf31_01'], date(2022, 12, 1), date(2022, 12, 31), thirteen_month=True)
        mapped_payslips['payslip_tf32_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf32_01'], date(2022, 12, 1), date(2022, 12, 31))
        mapped_payslips['payslip_tf33_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf33_01'], date(2022, 12, 1), date(2022, 12, 31), thirteen_month=True)
        mapped_payslips['payslip_tf34_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf34_01'], date(2022, 12, 1), date(2022, 12, 31), thirteen_month=True)
        mapped_payslips['payslip_tf35_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf35_01'], date(2022, 12, 1), date(2022, 12, 31), thirteen_month=True)
        mapped_payslips['payslip_tf36_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf36_02'], date(2022, 12, 1), date(2022, 12, 31), thirteen_month=True)
        mapped_payslips['payslip_tf38_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf38_01'], date(2022, 12, 1), date(2022, 12, 31), thirteen_month=True)
        mapped_payslips['payslip_tf39_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf39_01'], date(2022, 12, 1), date(2022, 12, 31))
        mapped_payslips['payslip_tf40_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf40_04'], date(2022, 12, 1), date(2022, 12, 31), thirteen_month=True, thirteen_force=1333.35)
        mapped_payslips['payslip_tf42_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf42_01'], date(2022, 12, 1), date(2022, 12, 31), ch_days=8)
        mapped_payslips['payslip_tf43_2022_12'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf43_01'], date(2022, 12, 1), date(2022, 12, 31), ch_days=8)
        self._l10n_ch_compute_swissdec_demo_paylips(date(2022, 12, 1))

        # 2023-01
        mapped_contracts['contract_tf18_01'].write({'l10n_ch_current_occupation_rate': 19.23})
        self.env['hr.employee.is.line'].create({'employee_id': mapped_employees['employee_tf29'].id, 'valid_as_of': date(2022, 12, 1), 'correction_date': date(2023, 1, 1), 'payslips_to_correct': mapped_payslips['payslip_tf29_2022_12'].ids})
        mapped_employees['employee_tf32'].write({"l10n_ch_tax_scale": 'B'})
        self.env['hr.employee.is.line'].create({'employee_id': mapped_employees['employee_tf32'].id, 'valid_as_of': date(2022, 11, 1), 'correction_date': date(2023, 1, 1), 'payslips_to_correct': (mapped_payslips['payslip_tf32_2022_11'] + mapped_payslips['payslip_tf32_2022_12']).ids})
        mapped_payslips['payslip_tf02_2023_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf02_01'], date(2023, 1, 1), date(2023, 1, 31), thirteen_month=True)
        mapped_payslips['payslip_tf08_2023_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf08_01'], date(2023, 1, 1), date(2023, 1, 31), thirteen_month=True, after_payment='N')
        mapped_payslips['payslip_tf11_2023_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf11_02'], date(2023, 1, 1), date(2023, 1, 31))
        mapped_payslips['payslip_tf13_2023_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf13_03'], date(2023, 1, 1), date(2023, 1, 31))
        mapped_payslips['payslip_tf14_2023_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf14_02'], date(2023, 1, 1), date(2023, 1, 31))
        mapped_payslips['payslip_tf18_2023_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf18_01'], date(2023, 1, 1), date(2023, 1, 31))
        mapped_payslips['payslip_tf22_2023_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf22_01'], date(2023, 1, 1), date(2023, 1, 31))
        mapped_payslips['payslip_tf27_2023_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf27_01'], date(2023, 1, 1), date(2023, 1, 31))
        mapped_payslips['payslip_tf28_2023_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf28_01'], date(2023, 1, 1), date(2023, 1, 31), after_payment='NK')
        mapped_payslips['payslip_tf29_2023_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf29_01'], date(2023, 1, 1), date(2023, 1, 31), after_payment='NK')
        mapped_payslips['payslip_tf32_2023_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf32_01'], date(2023, 1, 1), date(2023, 1, 31))
        mapped_payslips['payslip_tf40_2023_01'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf40_04'], date(2023, 1, 1), date(2023, 1, 31))
        self._l10n_ch_compute_swissdec_demo_paylips(date(2023, 1, 1))

        # 2023-02
        mapped_employees['employee_tf29'].write({"l10n_ch_tax_scale": 'A', "l10n_ch_canton": 'BE'})
        mapped_contracts['contract_tf29_01'].write({'l10n_ch_is_model': "monthly"})
        mapped_payslips['payslip_tf02_2023_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf02_01'], date(2023, 2, 1), date(2023, 2, 28), thirteen_month=True)
        mapped_payslips['payslip_tf04_2023_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf04_01'], date(2023, 2, 1), date(2023, 2, 28), thirteen_month=True, after_payment="N")
        mapped_payslips['payslip_tf05_2023_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf05_02'], date(2023, 2, 1), date(2023, 2, 28), after_payment="N")
        mapped_payslips['payslip_tf06_2023_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf06_01'], date(2023, 2, 1), date(2023, 2, 28), after_payment="N")
        mapped_payslips['payslip_tf08_2023_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf08_01'], date(2023, 2, 1), date(2023, 2, 28), thirteen_month=True, after_payment="N")
        mapped_payslips['payslip_tf11_2023_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf11_02'], date(2023, 2, 1), date(2023, 2, 28))
        mapped_payslips['payslip_tf13_2023_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf13_03'], date(2023, 2, 1), date(2023, 2, 28))
        mapped_payslips['payslip_tf14_2023_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf14_02'], date(2023, 2, 1), date(2023, 2, 28))
        mapped_payslips['payslip_tf18_2023_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf18_01'], date(2023, 2, 1), date(2023, 2, 28))
        mapped_payslips['payslip_tf22_2023_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf22_01'], date(2023, 2, 1), date(2023, 2, 28))
        mapped_payslips['payslip_tf27_2023_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf27_01'], date(2023, 2, 1), date(2023, 2, 28))
        mapped_payslips['payslip_tf28_2023_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf28_01'], date(2023, 2, 1), date(2023, 2, 28), after_payment='N')
        mapped_payslips['payslip_tf29_2023_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf29_01'], date(2023, 2, 1), date(2023, 2, 28), after_payment='N')
        mapped_payslips['payslip_tf32_2023_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf32_01'], date(2023, 2, 1), date(2023, 2, 28))
        mapped_payslips['payslip_tf40_2023_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf40_04'], date(2023, 2, 1), date(2023, 2, 28))
        mapped_payslips['payslip_tf42_2023_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf42_01'], date(2023, 2, 1), date(2023, 2, 28), after_payment='N')
        mapped_payslips['payslip_tf43_2023_02'] = self._l10n_ch_generate_swissdec_demo_payslip(mapped_contracts['contract_tf43_01'], date(2023, 2, 1), date(2023, 2, 28), after_payment='N')
        self._l10n_ch_compute_swissdec_demo_paylips(date(2023, 2, 1))

        return mapped_payslips

    def _l10n_ch_generate_swissdec_demo_payslip(self, contract, date_from, date_to, thirteen_month=False, after_payment=False, ch_days=20, work_days=20, basic=False, as_days=False, thirteen_force=False, compute=False):
        self.ensure_one()
        batch = self.env['hr.payslip.run'].search([('date_start', '=', date_from), ('company_id', '=', self.env.company.id)])
        if not batch:
            batch = self.env['hr.payslip.run'].create({
                'name': f"Monthly Pay Batch - {date_from.year}-{date_from.month}",
                'date_start': date_from,
                'date_end': date_to,
                'company_id': self.env.company.id,
            })
        vals = {
            'name': f"Monthly Pay Batch - {date_from.year}-{date_from.month}",
            'employee_id': contract.employee_id.id,
            'contract_id': contract.id,
            'company_id': self.id,
            'struct_id': self.env.ref('l10n_ch_hr_payroll.hr_payroll_structure_ch_employee_salary').id,
            'date_from': date_from,
            'date_to': date_to,
            'l10n_ch_after_departure_payment': after_payment,
            'l10n_ch_pay_13th_month': thirteen_month,
            'payslip_run_id': batch.id,
        }
        # Ensure attachments are computed before writing new inputs by hand, that
        # would prevent field computation
        payslip = self.env['hr.payslip'].with_context(tracking_disable=True).create(vals)
        self.env.flush_all()
        payslip.l10n_ch_pay_13th_month = thirteen_month
        add_inputs = []
        if ch_days != 20:
            add_inputs.append((0, 0, {
                'input_type_id': self.env.ref('l10n_ch_hr_payroll_elm.input_is_worked_days_in_ch').id,
                'amount': ch_days,
            }))

        if work_days != 20:
            add_inputs.append((0, 0, {
                'input_type_id': self.env.ref('l10n_ch_hr_payroll_elm.input_is_worked_days').id,
                'amount': work_days,
            }))
        if basic:
            add_inputs.append((0, 0, {
                'input_type_id': self.env.ref('l10n_ch_hr_payroll_elm.input_force_monthly_basic').id,
                'amount': basic,
            }))
        if as_days:
            add_inputs.append((0, 0, {
                'input_type_id': self.env.ref('l10n_ch_hr_payroll_elm.input_force_as_days').id,
                'amount': as_days,
            }))
        if thirteen_force:
            add_inputs.append((0, 0, {
                'input_type_id': self.env.ref('l10n_ch_hr_payroll_elm.input_force_thirteen_month').id,
                'amount': thirteen_force,
            }))
        if add_inputs:
            payslip.write({
                'input_line_ids': add_inputs
            })
        if compute:
            payslip.compute_sheet()
            payslip.action_payslip_done()
            payslip.action_payslip_paid()
        return payslip

    def _l10n_ch_compute_swissdec_demo_paylips(self, date_from):
        self.ensure_one()
        _logger.info('Created payslips for period %s-%s', date_from.year, date_from.month)
        payslips = self.env['hr.payslip'].with_context(tracking_disable=True).search([
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_from + relativedelta(days=31)),
            ('state', '=', 'draft'),
            ('company_id', '=', self.id),
        ])
        payslips.compute_sheet()
        payslips.action_payslip_done()
        payslips.action_payslip_paid()
        _logger.info('Computed payslips for period %s-%s', date_from.year, date_from.month)
