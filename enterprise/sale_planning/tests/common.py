# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo.addons.planning.tests.common import TestCommonPlanning

class TestCommonSalePlanning(TestCommonPlanning):

    @classmethod
    def setUpEmployees(cls):
        super().setUpEmployees()
        cls.employee_wout = cls.env['hr.employee'].create({
            'name': 'Wout',
            'work_email': 'wout@a.be',
            'tz': 'Europe/Brussels',
            'employee_type': 'freelance',
        })
        cls.env.cr.execute("UPDATE hr_employee SET create_date=%s WHERE id=%s",
                           ('2021-01-01 00:00:00', cls.employee_wout.id))

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.setUpEmployees()
        calendar_joseph = cls.env['resource.calendar'].create({
            'name': 'Calendar 1',
            'tz': 'UTC',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 9, 'hour_to': 13, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 14, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 14, 'hour_to': 18, 'day_period': 'afternoon'}),
            ]
        })
        calendar_bert = cls.env['resource.calendar'].create({
            'name': 'Calendar 2',
            'tz': 'UTC',
            'hours_per_day': 4,
            'attendance_ids': [
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'morning'}),
            ],
        })
        calendar = cls.env['resource.calendar'].create({
            'name': 'Classic 40h/week',
            'tz': 'UTC',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'})
            ]
        })
        cls.env.user.company_id.resource_calendar_id = calendar
        cls.employee_joseph.resource_calendar_id = calendar_joseph
        cls.employee_bert.resource_calendar_id = calendar_bert
        cls.planning_role_junior = cls.env['planning.role'].create({
            'name': 'Junior Developer'
        })

        cls.planning_partner = cls.env['res.partner'].create({
            'name': 'Customer Credee'
        })
        cls.plannable_product = cls.env['product.product'].create({
            'name': 'Home Help',
            'type': 'service',
            'planning_enabled': True,
            'planning_role_id': cls.planning_role_junior.id
        })
        cls.plannable_so = cls.env['sale.order'].create({
            'partner_id': cls.planning_partner.id,
        })
        cls.plannable_sol = cls.env['sale.order.line'].create({
            'order_id': cls.plannable_so.id,
            'product_id': cls.plannable_product.id,
            'product_uom_qty': 10,
        })
