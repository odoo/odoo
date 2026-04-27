# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.appointment.tests.common import AppointmentCommon


class GoogleReserveCommon(AppointmentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_location = cls.env['res.partner'].create({
            'name': 'Test Google Reserve',
            'is_company': True,
            'street': 'Zboing Street 42',
            'city': 'Bloups',
            'zip': '6666',
            'country_id': cls.env.ref('base.be').id,
            'phone': '+32 11 22 33 44',
        })

        cls.google_reserve_merchant = cls.env['google.reserve.merchant'].create({
            'name': 'My Company',
            'business_category': 'Restaurant',
            'phone': '+32499123456',
            'website_url': 'https://www.example.com',
            'location_id': cls.test_location.id,
        })

        with patch(
            'odoo.addons.appointment_google_reserve.tools.google_reserve_iap.GoogleReserveIAP.register_appointment',
            lambda self, appointment: None
        ):
            cls.apt_type_resource_google = cls.env['appointment.type'].create({
                'appointment_tz': 'UTC',
                'assign_method': 'time_auto_assign',
                'location_id': cls.test_location.id,
                'min_schedule_hours': 1.0,
                'max_schedule_days': 5,
                'name': 'Test Google Reserve',
                'resource_manage_capacity': True,
                'schedule_based_on': 'resources',
                'google_reserve_enable': True,
                'google_reserve_merchant_id': cls.google_reserve_merchant.id,
                'slot_ids': [(0, 0, {
                    'weekday': str(cls.reference_monday.isoweekday()),
                    'start_hour': 15,
                    'end_hour': 18,
                })],
            })

            cls.apt_type_staff_google = cls.env['appointment.type'].create({
                'appointment_tz': 'UTC',
                'assign_method': 'time_auto_assign',
                'location_id': cls.test_location.id,
                'min_schedule_hours': 1.0,
                'max_schedule_days': 5,
                'name': 'Test Google Reserve Staff Users',
                'schedule_based_on': 'users',
                'google_reserve_enable': True,
                'google_reserve_merchant_id': cls.google_reserve_merchant.id,
                'slot_ids': [(0, 0, {
                    'weekday': str(cls.reference_monday.isoweekday()),
                    'start_hour': 15,
                    'end_hour': 18,
                })],
                'staff_user_ids': [
                    (4, cls.apt_manager.id),
                    (4, cls.staff_user_bxls.id),
                ],
            })

        [cls.apt_type_resources_table_1, cls.apt_type_resources_table_2] = cls.env['appointment.resource'].create([{
            'appointment_type_ids': cls.apt_type_resource_google.ids,
            'capacity': 4,
            'name': 'Table 1',
            'sequence': 2,
        }, {
            'appointment_type_ids': cls.apt_type_resource_google.ids,
            'capacity': 2,
            'name': 'Table 2',
            'sequence': 1,
        }])
        cls.apt_resources_google = (cls.apt_type_resources_table_1 + cls.apt_type_resources_table_2)

        # cleanup config
        cls.env['ir.config_parameter'].set_param(
            'appointment_google_reserve.google_reserve_iap_endpoint',
            'https://google-reserve.api.odoo.com'
        )
