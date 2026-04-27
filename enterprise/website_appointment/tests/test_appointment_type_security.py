# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.appointment.tests.test_appointment_type_security import TestAppointmentTypeSecurity
from odoo.exceptions import AccessError
from odoo.tests import tagged, users
from odoo.tools import mute_logger


@tagged('security')
class WebsiteAppointmentTypeSecurityTest(TestAppointmentTypeSecurity):

    @users('public_user')
    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_website_appointment_type_website_published_access(self):
        """  Public users should have read access on every 'website_published' appointment types. """
        self._prepare_types_with_user()
        for appointment_type in self.all_apt_types:
            with self.subTest(appointment_type=appointment_type), self.assertRaises(AccessError):
                appointment_type.read(['name'])

        self.all_apt_types.with_user(self.apt_manager).write({'website_published': True})
        # Should now be able to read every appointment type
        for appointment_type in self.all_apt_types:
            with self.subTest(appointment_type=appointment_type):
                appointment_type.read(['name'])
