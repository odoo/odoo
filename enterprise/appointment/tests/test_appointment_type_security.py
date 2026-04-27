# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from datetime import datetime, timedelta

from odoo.addons.appointment.tests.common import AppointmentSecurityCommon
from odoo.exceptions import AccessError
from odoo.tests import tagged, users
from odoo.tools import mute_logger, file_open


@tagged('security')
class TestAppointmentTypeSecurity(AppointmentSecurityCommon):

    @users('apt_manager')
    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_appointment_type_access_apt_manager(self):
        """  Test security access to appointment.type for the group_appointment_manager.
        Can read / write / create / unlink any appointment type.
        """
        self._prepare_types_with_user()
        # Can read, write, unlink any appointment type
        for appointment_type in self.all_apt_types:
            with self.subTest(appointment_type=appointment_type):
                appointment_type.read(['name'])
                appointment_type.write({'is_published': True})
                appointment_type.unlink()
        # Can create an appointment type
        self.env['appointment.type'].create({
            'name': 'Test Create'
        })

    @users('apt_user')
    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_appointment_type_access_apt_user(self):
        """  Test security access to appointment.type for the group_appointment_user.
        Can create an appointment type.
        Can read every published appointment type.
        Can read an appointment type that:
            - is created by the user.
            - has the user in its staff OR doesn't have any staff
            - is resource-based.
        Can write an appointment type that:
            - is created by the user.
        Can unlink an appointment type that:
            - is created by the user.
        """
        self._prepare_types_with_user()
        # Can't read appointment type for which he is not part of staff users
        with self.assertRaises(AccessError):
            self.apt_type_apt_manager.read(['name'])
        with self.assertRaises(AccessError):
            self.apt_type_internal_user.read(['name'])
        (self.apt_type_apt_user + self.apt_type_resource + self.apt_type_no_staff).read(['name'])
        # Can read now that's published
        for appointment_type in self.apt_type_apt_manager + self.apt_type_internal_user:
            with self.subTest(appointment_type=appointment_type):
                appointment_type.with_user(self.apt_manager).write({'is_published': True})
                appointment_type.read(['name'])

        # Can create an appointment type
        created_apt = self.env['appointment.type'].create({
            'name': 'Test Create',
        })

        # Can't write or unlink appointment type created by some one else
        for appointment_type in self.all_apt_types:
            with self.subTest(appointment_type=appointment_type), self.assertRaises(AccessError):
                appointment_type.write({'name': 'test'})
            with self.subTest(appointment_type=appointment_type), self.assertRaises(AccessError):
                appointment_type.unlink()

        # Can only write or unlink appointment types created by himself
        created_apt.write({'name': 'test'})
        created_apt.unlink()

    @users('internal_user')
    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_appointment_type_access_internal_user(self):
        """  Test security access to appointment.type for the base.group_user.
        Can read an appointment type that:
            - is published.
            - has the user in its staff OR doesn't have any staff
            - is resource-based.
        Can't write / create / unlink any appointment type.
        """
        self._prepare_types_with_user()
        # Can't read appointment type for which he is not part of staff users
        with self.assertRaises(AccessError):
            self.apt_type_apt_manager.read(['name'])
        with self.assertRaises(AccessError):
            self.apt_type_apt_user.read(['name'])
        (self.apt_type_internal_user + self.apt_type_resource + self.apt_type_no_staff).read(['name'])
        # Can read now that's published
        for appointment_type in self.apt_type_apt_manager + self.apt_type_apt_user:
            with self.subTest(appointment_type=appointment_type):
                appointment_type.with_user(self.apt_manager).write({'is_published': True})
                appointment_type.read(['name'])
        # Can't create an appointment type
        with self.assertRaises(AccessError):
            self.env['appointment.type'].create({
                'name': 'Test Create'
            })
        # Can't write or unlink any appointment type
        for appointment_type in self.all_apt_types:
            with self.subTest(appointment_type=appointment_type):
                with self.assertRaises(AccessError):
                    appointment_type.write({'is_published': True})
                with self.assertRaises(AccessError):
                    appointment_type.unlink()

    @users('public_user')
    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_appointment_type_access_public_user(self):
        """  Test security access to appointment.type for the base.group_public.
        Can't read / write / create / unlink any appointment type.
        """
        self._prepare_types_with_user()
        # Can't read / write / unlink any appointment type
        for appointment_type in self.all_apt_types:
            with self.subTest(appointment_type=appointment_type):
                with self.assertRaises(AccessError):
                    appointment_type.read(['name'])
                with self.assertRaises(AccessError):
                    appointment_type.write({'is_published': True})
                with self.assertRaises(AccessError):
                    appointment_type.unlink()
        # Can't create an appointment type
        with self.assertRaises(AccessError):
            self.env['appointment.type'].create({
                'name': 'Test Create'
            })

    @users('staff_user_aust')
    def test_appointment_type_customer_description_access(self):
        """
        Ensure a user who is only an attendee (i.e., not in staff_user_ids)
        does NOT receive an AccessError when calling _get_customer_description.
        """
        appointment_type = self.apt_type_bxls_2days
        appointment_type.sudo().staff_user_ids = [self.apt_manager.id]  # ensure staff is set
        appointment_type.sudo().message_confirmation = 'Test confirmation message'

        test_event = self.env['calendar.event'].create({
            'name': 'Test Event for Non-staff Attendee',
            'start': datetime.now(),
            'stop': datetime.now() + timedelta(hours=1),
            'appointment_type_id': appointment_type.id,
            'user_id': self.apt_manager.id,  # The staff/host user
            'partner_ids': [(6, 0, [self.env.user.partner_id.id, self.apt_manager.partner_id.id])],
        })

        test_event.appointment_type_id.invalidate_recordset(['message_confirmation'])
        self.assertIn("Test confirmation message", test_event._get_customer_description())

    @users('public_user')
    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_appointment_type_image_access_public_user(self):
        """  Test that base.group_public users can access every appointment type image
        even though they don't have read access on the appointment.type model.
        """
        self._prepare_types_with_user()

        placeholder_image = file_open(self.env['appointment.type']._get_placeholder_filename('image_1920'), 'rb').read()
        test_image_b64 = b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC'
        test_image = base64.b64decode(test_image_b64)

        (self.apt_type_apt_manager + self.apt_type_resource).with_user(self.apt_manager).write({'image_1920': test_image_b64})
        cases = [
            (self.apt_type_apt_manager, test_image),
            (self.apt_type_apt_user, placeholder_image),
            (self.apt_type_internal_user, placeholder_image),
            (self.apt_type_resource, test_image),
            (self.apt_type_no_staff, placeholder_image),
        ]
        for appointment_type, expected_image in cases:
            with self.subTest(appointment_type=appointment_type):
                res = self.url_open(f'/web/image/appointment.type/{appointment_type.id}/image_1920')
                self.assertEqual(res.status_code, 200)
                self.assertEqual(res.content, expected_image)

    def _prepare_types_with_user(self):
        """ Prepare the appointment types by applying the user to be the one from the environment. """
        self.apt_type_apt_manager = self.apt_type_apt_manager.with_user(self.env.user)
        self.apt_type_apt_user = self.apt_type_apt_user.with_user(self.env.user)
        self.apt_type_internal_user = self.apt_type_internal_user.with_user(self.env.user)
        self.apt_type_resource = self.apt_type_resource.with_user(self.env.user)
        self.apt_type_no_staff = self.apt_type_no_staff.with_user(self.env.user)
        self.all_apt_types = self.apt_type_apt_manager + self.apt_type_apt_user + self.apt_type_internal_user + self.apt_type_resource + self.apt_type_no_staff
