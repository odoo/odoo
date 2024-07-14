# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.appointment.tests.common import AppointmentCommon
from odoo.tests import HttpCase


class AppointmentAccountPaymentCommon(AppointmentCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        paid_apt_common_values = {
            'appointment_tz': 'UTC',
            'has_payment_step': True,
            'min_schedule_hours': 1.0,
            'max_schedule_days': 2,
            'product_id': cls.env.ref('appointment_account_payment.default_booking_product').id,
            'slot_ids': [(0, 0, {
                'weekday': str(cls.reference_monday.isoweekday()),
                'start_hour': 14,
                'end_hour': 15,
            })],
        }
        cls.appointment_users_payment, cls.appointment_resources_payment = cls.env['appointment.type'].create([{
            'name': 'Paid Appointment Type - Users',
            'schedule_based_on': 'users',
            'staff_user_ids': [(4, cls.staff_user_bxls.id)],
            **paid_apt_common_values,
        }, {
            'name': 'Paid Appointment Type - Resource',
            'resource_manage_capacity': True,
            'resource_manual_confirmation': False,
            'schedule_based_on': 'resources',
            **paid_apt_common_values,
        }])

        cls.resource_1, cls.resource_2 = cls.env['appointment.resource'].create([{
            'appointment_type_ids': cls.appointment_resources_payment.ids,
            'capacity': 3,
            'name': 'Resource 1',
        }, {
            'appointment_type_ids': cls.appointment_resources_payment.ids,
            'capacity': 2,
            'name': 'Resource 2',
            'shareable': True,
        }])

        cls.start_slot = cls.reference_monday.replace(hour=14, microsecond=0)
        cls.stop_slot = cls.reference_monday.replace(hour=15, microsecond=0)
