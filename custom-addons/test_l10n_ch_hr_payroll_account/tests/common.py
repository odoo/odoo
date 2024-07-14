# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestL10NChHrPayrollAccountCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='ch'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.ch').id,
            'street': 'Rue du Paradis',
            'zip': '6870',
            'city': 'Eghezee',
            'vat': 'BE0897223670',
            'phone': '061928374',
        })

        cls.company = cls.env.company

        admin = cls.env['res.users'].search([('login', '=', 'admin')])
        admin.company_ids |= cls.company

        cls.env.user.tz = 'Europe/Zurich'

        cls.resource_calendar_40_hours_per_week = cls.env['resource.calendar'].create([{
            'name': "Test Calendar : 40 Hours/Week",
            'company_id': cls.env.company.id,
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

        cls.social_insurance = cls.env['l10n.ch.social.insurance'].create({
            'name': 'Social Insurance AK Bern',
            'member_number': '2948',
            'member_subnumber': '2292490',
            'insurance_company': 'AK Bern',
            'insurance_code': '002.000',
            'avs_line_ids': [(0, 0, {
                'date_from': date(2022, 1, 1),
                'date_to': False,
                'employer_rate': 5.3,
                'employee_rate': 5.3,
            })],
            'ac_line_ids': [(0, 0, {
                'date_from': date(2022, 1, 1),
                'date_to': False,
                'employer_rate': 1.1,
                'employee_rate': 1.1,
                'employee_additional_rate': 0.5,
                'employer_additional_rate': 0,
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

        cls.groupe_mutuel = cls.env['res.partner'].create({
            'name': "Groupe Mutuel",
            'street': "Im Sandbüel 23",
            'city': "Frinvillier",
            'zip': "5000",
            'country_id': cls.env.ref("base.ch").id,
            'company_id': cls.env.company.id,
        })

        cls.accident_insurance = cls.env['l10n.ch.accident.insurance'].create({
            'name': "Accident Insurance Groupe Mutuel",
            'customer_number': '10403',
            'contract_number': '10390',
            'insurance_code': 'S270',
            'insurance_company': 'Groupe Mutuel',
            'insurance_company_address_id': cls.groupe_mutuel.id,
            'line_ids': [(0, 0, {
                "solution_name": "UVG solution A1",
                "solution_type": "A",
                "solution_number": "1",
                "rate_ids": [(0, 0, {
                    "date_from": date(2022, 1, 1),
                    "date_to": False,
                    "threshold": 148200,
                    "occupational_male_rate": 2,
                    "occupational_female_rate": 2,
                    "non_occupational_male_rate": 1.168,
                    "non_occupational_female_rate": 1.168,
                    "employer_occupational_part": "50",
                    "employer_non_occupational_part": "50",
                })],
            })],
        })

        cls.additional_accident_insurance = cls.env['l10n.ch.additional.accident.insurance'].create({
            'name': 'Additional Accident Insurance Groupe Mutuel',
            'customer_number': '10405',
            'contract_number': '10393',
            'insurance_company': 'Groupe Mutule',
            'insurance_code': 'S270',
            'insurance_company_address_id': cls.groupe_mutuel.id,
            'line_ids': [(0, 0, {
                'solution_name': 'UVG solution A1',
                'solution_type': 'A',
                'solution_number': '1',
                'rate_ids': [(0, 0, {
                    'date_from': date(2020, 1, 1),
                    'date_to': False,
                    'wage_from': 0,
                    'wage_to': 148200,
                    'male_rate': 2,
                    'female_rate': 2,
                    'employer_part': '50',
                })],
            })]
        })

        cls.sickness_insurance = cls.env['l10n.ch.sickness.insurance'].create({
            "name": 'Sickness Insurance Groupe Mutuel',
            "customer_number": '10405',
            "contract_number": '10393',
            "insurance_company": 'Groupe Mutuel',
            "insurance_code": 'S270',
            "insurance_company_address_id": cls.groupe_mutuel.id,
            "line_ids": [(0, 0, {
                "solution_name": "IJM solution A1",
                "solution_type": "A",
                "solution_number": "1",
                "rate_ids": [(0, 0, {
                    "date_from": date(2020, 1, 1),
                    "date_to": False,
                    "wage_from": 0,
                    "wage_to": 148200,
                    "male_rate": 1,
                    "female_rate": 1,
                    "employer_part": '50',
                })]
            })]
        })

        cls.lpp_insurance = cls.env['l10n.ch.lpp.insurance'].create({
            "name": 'LPP Insurance Groupe Mutuel',
            "customer_number": '30405',
            "contract_number": '40393',
            "insurance_company": 'Groupe Mutuel',
            "insurance_code": "S270",
            "insurance_company_address_id": cls.groupe_mutuel.id,
            "fund_number": '209230',
        })

        cls.compensation_fund = cls.env['l10n.ch.compensation.fund'].create({
            "name": 'Family Allowance AK Bern',
            "member_number": '2948',
            "member_subnumber": '2292490',
            "insurance_company": 'AK Bern',
            "insurance_code": '002.000',
            "caf_line_ids": [(0, 0, {
                'date_from': date(2022, 1, 1),
                'date_to': False,
                'employee_rate': 0.421,
            })],
        })

        cls.sick_time_off_type = cls.env['hr.leave.type'].create({
            'name': 'Sick Time Off',
            'requires_allocation': 'no',
            'work_entry_type_id': cls.env.ref('hr_work_entry_contract.work_entry_type_sick_leave').id,
        })
