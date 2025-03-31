# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestHrCalendarCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.tz = 'Europe/Brussels'
        cls.user_employee = mail_new_test_user(cls.env, login='david', groups='base.group_user')

        cls.company_A, cls.company_B = cls.env['res.company'].create([
            {
                'name': 'Test company A',
            },
            {
                'name': 'Test company B',
            },
        ])
        cls.env.user.company_id = cls.company_A
        cls.rd_dept = cls.env['hr.department'].create({
            'name': 'Research and development',
        })
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

        main_partner_id = cls.env.ref('base.main_partner')
        cls.work_office_1 = cls.env['hr.work.location'].create({
            'name': "Bureau 1",
            'location_type': "office",
            'address_id': main_partner_id.id,
        })

        cls.work_office_2 = cls.env['hr.work.location'].create({
            'name': "Bureau 2",
            'location_type': "office",
            'address_id': main_partner_id.id,
        })

        cls.work_home = cls.env['hr.work.location'].create({
            'name': "Maison",
            'location_type': "home",
            'address_id': main_partner_id.id,
        })

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
                'user_id': cls.user_employee.id,
                'department_id': cls.rd_dept.id,
                'monday_location_id': cls.work_home.id,
                'tuesday_location_id': cls.work_home.id,
                'wednesday_location_id': cls.work_office_1.id,
                'thursday_location_id': cls.work_office_1.id,
                'friday_location_id': cls.work_office_1.id,
                'saturday_location_id': cls.work_home.id,
                'sunday_location_id': cls.work_home.id,
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
