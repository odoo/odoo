# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.appointment.tests.common import AppointmentSecurityCommon
from odoo.exceptions import AccessError
from odoo.tests import tagged, users
from odoo.tools import mute_logger


@tagged('security')
class TestAppointmentSlotSecurity(AppointmentSecurityCommon):

    @users('apt_manager')
    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_appointment_slot_access_apt_manager(self):
        """  Test security access to appointment.slot for the group_appointment_manager.
        Can read / write / create / unlink any appointment slot.
        """
        self._prepare_slots_with_user()
        for appointment_slot in self.all_apt_slots:
            with self.subTest(appointment_slot=appointment_slot):
                appointment_slot.read(['weekday'])
                appointment_slot.write({'weekday': '2'})
                self.env['appointment.slot'].create({
                    'appointment_type_id': appointment_slot.appointment_type_id.id,
                    **self.common_slot_config
                })
                appointment_slot.unlink()

    @users('apt_user')
    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_appointment_slot_access_apt_user(self):
        """  Test security access to appointment.slot for the group_appointment_user.
        Can read the appointment slot if the related appointment type is published.
        Can read / write / create an appointment slot if the relation appointment type:
            - is created by the user.
            - has the user in its staff OR doesn't have any staff
            - is resource-based.
        Can unlink an appointment slot if:
            - the slot OR the related appointment type is created by the user.
        """
        self._prepare_slots_with_user()

        # Can't read the appointment slot if he is not part of the related appointment type staff users
        with self.assertRaises(AccessError):
            self.slot_apt_manager.read(['weekday'])
        with self.assertRaises(AccessError):
            self.slot_internal_user.read(['weekday'])
        (self.slot_apt_user + self.slot_resource + self.slot_no_staff).read(['weekday'])
        # Can read now that's published
        for appointment_slot in self.slot_apt_manager + self.slot_internal_user:
            with self.subTest(appointment_slot=appointment_slot):
                appointment_slot.with_user(self.apt_manager).appointment_type_id.write({'is_published': True})
                appointment_slot.read(['weekday'])

        # Can't create an appointment slot if he is not part of the related appointment type staff users
        with self.assertRaises(AccessError):
            self.env['appointment.slot'].create({
                'appointment_type_id': self.apt_type_apt_manager.id,
                **self.common_slot_config
            })
        with self.assertRaises(AccessError):
            self.env['appointment.slot'].create({
                'appointment_type_id': self.apt_type_internal_user.id,
                **self.common_slot_config
            })
        [created_slot_apt_user, created_slot_resource, created_slot_no_staff] = self.env['appointment.slot'].create([{
            'appointment_type_id': apt_type.id,
            **self.common_slot_config
        } for apt_type in (self.apt_type_apt_user + self.apt_type_resource + self.apt_type_no_staff)])

        # Can't write and unlink an appointment slot created by someone else.
        for appointment_slot in self.all_apt_slots:
            with self.subTest(appointment_slot=appointment_slot), self.assertRaises(AccessError):
                appointment_slot.write({'weekday': '2'})
            with self.subTest(appointment_slot=appointment_slot), self.assertRaises(AccessError):
                appointment_slot.unlink()
        # Can write and unlink an appointment slot if the slot is created by the user.
        (created_slot_apt_user + created_slot_resource + created_slot_no_staff).write({'weekday': '2'})
        (created_slot_apt_user + created_slot_resource + created_slot_no_staff).unlink()
        # Can unlink an appointment slot if the related appointment type is created by the user.
        created_apt = self.env['appointment.type'].create({
            'name': 'Test Create'
        })
        apt_manager_slots = self.env['appointment.slot'].with_user(self.apt_manager).create({
            'appointment_type_id': created_apt.id,
            **self.common_slot_config
        })
        apt_manager_slots.unlink()

    @users('internal_user')
    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_appointment_slot_access_internal_user(self):
        """  Test security access to appointment.slot for the base.group_user.
        Can read an appointment slot if the related appointment type:
            - is published.
            - has the user in its staff OR doesn't have any staff
            - is resource-based.
        Can't write / create / unlink any appointment slot.
        """
        self._prepare_slots_with_user()

        # Can't read the appointment slot if he is not part of the related appointment type staff users
        with self.assertRaises(AccessError):
            self.slot_apt_manager.read(['weekday'])
        with self.assertRaises(AccessError):
            self.slot_apt_user.read(['weekday'])
        (self.slot_internal_user + self.slot_resource + self.slot_no_staff).read(['weekday'])

        for appointment_slot in self.all_apt_slots:
            with self.subTest(appointment_slot=appointment_slot):
                # Can read now that's published
                appointment_slot.with_user(self.apt_manager).appointment_type_id.write({'is_published': True})
                appointment_slot.read(['weekday'])
                # Can't write / create / unlink appointment slots
                with self.assertRaises(AccessError):
                    appointment_slot.write({'weekday': '2'})
                with self.assertRaises(AccessError):
                    self.env['appointment.slot'].create({
                        'appointment_type_id': appointment_slot.with_user(self.apt_manager).appointment_type_id.id,
                        **self.common_slot_config
                    })
                with self.assertRaises(AccessError):
                    appointment_slot.unlink()

    @users('public_user')
    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_appointment_slot_access_public_user(self):
        """  Test security access to appointment.slot for the base.group_public.
        Can't access anything outside of specific invitations (as those are sudo'ed in the controllers).
        Can't read / write / create / unlink any appointment slot.
        (When website_appointment is installed public users get access to published appointments)
        """
        self._prepare_slots_with_user()
        for appointment_slot in self.all_apt_slots:
            with self.subTest(appointment_slot=appointment_slot):
                with self.assertRaises(AccessError):
                    appointment_slot.read(['weekday'])
                with self.assertRaises(AccessError):
                    appointment_slot.write({'is_published': True})
                with self.assertRaises(AccessError):
                    self.env['appointment.slot'].create({
                        'appointment_type_id': appointment_slot.with_user(self.apt_manager).appointment_type_id.id,
                        **self.common_slot_config
                    })
                with self.assertRaises(AccessError):
                    appointment_slot.unlink()

    def _prepare_slots_with_user(self):
        """ Prepare the slots by applying the user to be the one from the environment. """
        self.slot_apt_manager = self.apt_type_apt_manager.slot_ids[0].with_user(self.env.user)
        self.slot_apt_user = self.apt_type_apt_user.slot_ids[0].with_user(self.env.user)
        self.slot_internal_user = self.apt_type_internal_user.slot_ids[0].with_user(self.env.user)
        self.slot_resource = self.apt_type_resource.slot_ids[0].with_user(self.env.user)
        self.slot_no_staff = self.apt_type_no_staff.slot_ids[0].with_user(self.env.user)
        self.all_apt_slots = self.slot_apt_manager + self.slot_apt_user + self.slot_internal_user + self.slot_resource + self.slot_no_staff
