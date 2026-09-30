# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo.tests import common


class TestHrCalendarCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.tz = 'Europe/Brussels'

        cls.company_A, cls.company_B = cls.env['res.company'].create([
            {
                'name': 'Test company A',
            },
            {
                'name': 'Test company B',
            },
        ])
        cls.env.user.company_id = cls.company_A

        cls.calendar_35h, cls.calendar_28h, cls.calendar_35h_night = cls.env['resource.calendar'].create([
            {
                'tz': "Europe/Brussels",
                'name': '35h calendar',
                'hours_per_day': 7.0,
                'attendance_ids': [
                    (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Monday Evening', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Tuesday Evening', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Wednesday Evening', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Thursday Evening', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Friday Evening', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                ],
            },
            {
                'tz': "Europe/Brussels",
                'name': '28h calendar',
                'attendance_ids': [
                    (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Tuesday Evening', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Wednesday Evening', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Thursday Evening', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Friday Evening', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                ],
            },
            {
                'tz': "Europe/Brussels",
                'name': 'night calendar',
                'attendance_ids': [
                    (0, 0, {'name': 'Monday Evening', 'dayofweek': '0', 'hour_from': 15, 'hour_to': 22, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Tuesday Evening', 'dayofweek': '1', 'hour_from': 15, 'hour_to': 22, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Wednesday Evening', 'dayofweek': '2', 'hour_from': 15, 'hour_to': 22, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Thursday Evening', 'dayofweek': '3', 'hour_from': 15, 'hour_to': 22, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Friday Evening', 'dayofweek': '4', 'hour_from': 15, 'hour_to': 21, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Sunday Evening', 'dayofweek': '6', 'hour_from': 15, 'hour_to': 16, 'day_period': 'afternoon'}),
                ],
            },
        ])

        cls.partnerA, cls.partnerB, cls.partnerC, cls.partnerD = cls.env['res.partner'].create([
            {
                'name': "Partner A",
            },
            {
                'name': "Partner B",
            },
            {
                'name': "Partner C",
            },
            {
                'name': "Partner D",
            },
        ])

        cls.employeeA, cls.employeeA_company_B, cls.employeeB, cls.employeeC, cls.employeeD = cls.env['hr.employee'].create([
            {
                'name': "Partner A - Company A - Calendar 35h",
                'tz': "Europe/Brussels",
                'resource_calendar_id': cls.calendar_35h.id,
                'work_contact_id': cls.partnerA.id,
                'company_id': cls.company_A.id,
            },
            {
                'name': "Partner A - Company B - Calendar 28h",
                'tz': "Europe/Brussels",
                'resource_calendar_id': cls.calendar_28h.id,
                'work_contact_id': cls.partnerA.id,
                'company_id': cls.company_B.id,
            },
            {
                'name': "Partner B - Calendar 28h",
                'tz': "Europe/Brussels",
                'resource_calendar_id': cls.calendar_28h.id,
                'work_contact_id': cls.partnerB.id,
                'company_id': cls.company_A.id,
            },
            {
                'name': "Partner C - Calendar 35h night",
                'tz': "Europe/Brussels",
                'resource_calendar_id': cls.calendar_35h_night.id,
                'work_contact_id': cls.partnerC.id,
                'company_id': cls.company_A.id,
            },
            {
                'name': "Partner D - Calendar 35h No contract",
                'tz': "Europe/Brussels",
                'resource_calendar_id': cls.calendar_35h.id,
                'work_contact_id': cls.partnerD.id,
                'company_id': cls.company_A.id,
            },
        ])


class TestHrContractCalendarCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.tz = 'Europe/Brussels'

        cls.company_A, cls.company_B = cls.env['res.company'].create([
            {
                'name': 'Test company A',
            },
            {
                'name': 'Test company B',
            },
        ])
        cls.env.user.company_id = cls.company_A
        cls.calendar_35h, cls.calendar_28h, cls.calendar_35h_night = cls.env['resource.calendar'].create([
            {
                'tz': "Europe/Brussels",
                'name': '35h calendar',
                'hours_per_day': 7.0,
                'attendance_ids': [
                    (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Monday Evening', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Tuesday Evening', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Wednesday Evening', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Thursday Evening', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Friday Evening', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                ],
            },
            {
                'tz': "Europe/Brussels",
                'name': '28h calendar',
                'attendance_ids': [
                    (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Tuesday Evening', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Wednesday Evening', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Thursday Evening', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Friday Evening', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                ],
            },
            {
                'tz': "Europe/Brussels",
                'name': 'night calendar',
                'attendance_ids': [
                    (0, 0, {'name': 'Monday Evening', 'dayofweek': '0', 'hour_from': 15, 'hour_to': 22, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Tuesday Evening', 'dayofweek': '1', 'hour_from': 15, 'hour_to': 22, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Wednesday Evening', 'dayofweek': '2', 'hour_from': 15, 'hour_to': 22, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Thursday Evening', 'dayofweek': '3', 'hour_from': 15, 'hour_to': 22, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Friday Evening', 'dayofweek': '4', 'hour_from': 15, 'hour_to': 22, 'day_period': 'afternoon'}),
                ],
            },
        ])
        cls.partnerA, cls.partnerB, cls.partnerC, cls.partnerD, cls.partnerE,\
        cls.partnerF, cls.partnerG = cls.env['res.partner'].create([
            {
                'name': "Partner A",
            },
            {
                'name': "Partner B",
            },
            {
                'name': "Partner C",
            },
            {
                'name': "Partner D",
            },
            {
                'name': "Partner E",
            },
            {
                'name': 'Partner F',
            },
            {
                'name': 'Partner G',
            },
        ])

        cls.employeeA, cls.employeeB, cls.employeeB_company_B,\
        cls.employeeC, cls.employeeD, cls.employeeE,\
        cls.employeeF, cls.employeeG = cls.env['hr.employee'].create([
            {
                'name': "Partner A - Calendar 35h",
                'tz': "Europe/Brussels",
                'work_contact_id': cls.partnerA.id,
                'company_id': cls.company_A.id,
                'date_version': datetime(2023, 12, 1),
                'contract_date_start': datetime(2023, 12, 1),
                'resource_calendar_id': cls.calendar_35h.id,
                'wage': 5000.0,
            },
            {
                'name': "Partner B - Company A - Calendar 28h",
                'tz': "Europe/Brussels",
                'work_contact_id': cls.partnerB.id,
                'company_id': cls.company_A.id,
                'date_version': datetime(2023, 12, 1),
                'contract_date_start': datetime(2023, 12, 1),
                'contract_date_end': datetime(2024, 3, 5),
                'resource_calendar_id': cls.calendar_28h.id,
                'wage': 5000.0,
            },
            {
                'name': "Partner B - Company B - Calendar 35h night",
                'tz': "Europe/Brussels",
                'work_contact_id': cls.partnerB.id,
                'company_id': cls.company_B.id,
                'date_version': datetime(2023, 12, 1),
                'contract_date_start': datetime(2023, 12, 1),
                'resource_calendar_id': cls.calendar_35h_night.id,
                'wage': 5000.0,
            },
            {
                'name': "Partner C - Calendar 35h night",
                'tz': "Europe/Brussels",
                'work_contact_id': cls.partnerC.id,
                'company_id': cls.company_A.id,
                'date_version': datetime(2023, 12, 28),
                'contract_date_start': datetime(2023, 12, 28),
                'resource_calendar_id': cls.calendar_35h_night.id,
                'wage': 5000.0,
            },
            {
                'name': "Partner D - Calendar 35h",
                'tz': "Europe/Brussels",
                'work_contact_id': cls.partnerD.id,
                'company_id': cls.company_A.id,
                'date_version': datetime(2023, 12, 1),
                'contract_date_start': datetime(2023, 12, 1),
                'resource_calendar_id': cls.calendar_35h.id,
                'wage': 5000.0,
            },
            {
                'name': "Partner E - No calendar",
                'tz': "Europe/Brussels",
                'work_contact_id': cls.partnerE.id,
                'company_id': cls.company_A.id,
            },
            {
                'name': 'Partner F - Fully Flexible',
                'tz': "Europe/Brussels",
                'resource_calendar_id': False,
                'work_contact_id': cls.partnerF.id,
                'company_id': cls.company_A.id,
                'date_version': datetime(2023, 12, 1),
                'contract_date_start': datetime(2023, 12, 1),
                'wage': 5000.0,
            },
            {
                'name': 'Partner G - Default Calendar',
                'tz': "Europe/Brussels",
                'resource_calendar_id': cls.company_A.resource_calendar_id.id,
                'work_contact_id': cls.partnerG.id,
                'company_id': cls.company_A.id,
                'date_version': datetime(2023, 12, 1),
                'contract_date_start': datetime(2023, 12, 1),
                'wage': 5000.0,
            },
        ])
        cls.contractA = cls.employeeA.version_id
        cls.contractB = cls.employeeB.version_id
        cls.contractB_company_B = cls.employeeB_company_B.version_id
        cls.contractC = cls.employeeC.version_id
        cls.contractD = cls.employeeD.version_id
        cls.contractE = cls.employeeE.version_id
        cls.contractF = cls.employeeF.version_id
        cls.contractG = cls.employeeG.version_id
