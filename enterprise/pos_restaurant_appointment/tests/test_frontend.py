# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_restaurant.tests.test_frontend import TestFrontend
from odoo import fields
from dateutil.relativedelta import relativedelta



@odoo.tests.tagged('post_install', '-at_install')
class TestUi(TestFrontend):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.appointment_type = cls.env['appointment.type'].create({
            'appointment_manual_confirmation': True,
            'appointment_tz': 'US/Eastern',
            'assign_method': 'time_auto_assign',
            'event_videocall_source': False,
            'name': 'Table Booking Test',
            'resource_manage_capacity': True,
            'resource_manual_confirmation_percentage': 0.8,
            'schedule_based_on': 'resources',
        })

        cls.pos_config.write({
            'module_pos_restaurant_appointment': True,
            'appointment_type_id': cls.appointment_type.id,
        })

        cls.table_5_resource = cls.env['appointment.resource'].create({
            'name': 'Test Main Floor - Table 5',
            'capacity': 2,
            'appointment_type_ids': [(6, 0, [cls.appointment_type.id])],
            'pos_table_ids': [(6, 0, [cls.main_floor_table_5.id])]
        })
    def test_pos_restaurant_appointment_tour_basic(self):
        now = fields.Datetime.now()
        self.env['calendar.event'].create({
                    'name': "Test Lunch",
                    'start': now + relativedelta(minutes=30),
                    'stop': now + relativedelta(minutes=150),
                    'appointment_type_id': self.appointment_type.id,
                    'booking_line_ids': [(0, 0, {'appointment_resource_id': self.table_5_resource.id, 'capacity_reserved': 2})],
        })

        # open a session, the /pos/ui controller will redirect to it
        self.pos_config.with_user(self.pos_admin).open_ui()

        self.start_pos_tour('RestaurantAppointmentTour', login="pos_admin")
