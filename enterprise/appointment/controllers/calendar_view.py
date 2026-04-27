# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import Forbidden

from odoo import http, fields, _
from odoo.exceptions import ValidationError
from odoo.http import request, route


class AppointmentCalendarView(http.Controller):

    # ------------------------------------------------------------
    # APPOINTMENT JSON ROUTES FOR BACKEND
    # ------------------------------------------------------------

    @route('/appointment/appointment_type/create_custom', type='json', auth='user')
    def appointment_type_create_custom(self, slots, context=None):
        """
        Return the info (id and url) of the custom appointment type
        that is created with the time slots in the calendar.

        Users would typically use this feature to create a custom
        appointment type for a specific customer and suggest a few
        hand-picked slots from the calendar view that work best for that
        appointment.

        Contrary to regular appointment types that are meant to be re-used
        several times week after week (e.g.: "Schedule Demo"), this category
        of appointment type will be unlink after some time has passed.

        - slots format:
            [{
                'start': '2021-06-25 13:30:00',
                'end': '2021-06-25 15:30:00',
                'allday': False,
            }, {
                'start': '2021-06-25 22:00:00',
                'end': '2021-06-26 22:00:00',
                'allday': True,
            },...]
        The timezone used for the slots is UTC
        """
        if not slots:
            raise ValidationError(_("A list of slots information is needed to create a custom appointment type"))
        # Check if the user is a member of group_user to avoid portal user and the like to create appointment types
        if not request.env.user._is_internal():
            raise Forbidden()
        if context:
            request.update_context(**context)
        AppointmentType = request.env['appointment.type']
        appointment_type = AppointmentType.with_context(
            AppointmentType._get_clean_appointment_context()
        ).create({
            'name': _('%(name)s - My availabilities', name=request.env.user.name),
            'category': 'custom',
            'slot_ids': [(0, 0, {
                'start_datetime': fields.Datetime.from_string(slot.get('start')),
                'end_datetime': fields.Datetime.from_string(slot.get('end')),
                'allday': slot.get('allday'),
                'slot_type': 'unique',
            }) for slot in slots],
            'staff_user_ids': request.env.user.ids,
        })

        return self._get_staff_user_appointment_invite_info(appointment_type)

    @route('/appointment/appointment_type/update_custom', type='json', auth='user')
    def appointment_type_update_custom(self, appointment_type_id, slots):
        """
            Updates the slots of a custom appointment when a user changes them on
            the calendar view, on sharing link / opening the configuration form.
        """
        if not appointment_type_id or not request.env.user._is_internal():
            raise Forbidden()
        if not slots:
            raise ValidationError(_("A list of slots information is needed to update this custom appointment type"))

        appointment_type = request.env['appointment.type'].browse(int(appointment_type_id))
        if appointment_type.category != 'custom' or appointment_type.create_uid != request.env.user:
            raise Forbidden()

        appointment_type.write({
            'slot_ids': [(5, 0, 0)] + [(0, 0, {
                'allday': slot.get('allday'),
                'end_datetime': fields.Datetime.from_string(slot.get('end')),
                'slot_type': 'unique',
                'start_datetime': fields.Datetime.from_string(slot.get('start')),
            }) for slot in slots],
        })
        return True

    @route('/appointment/appointment_type/get_book_url', type='json', auth='user')
    def appointment_get_book_url(self, appointment_type_id, context=None):
        """
        Get the information of the appointment invitation used to share the link
        of the appointment type selected.
        """
        if context:
            request.update_context(**context)
        appointment_type = request.env['appointment.type'].browse(int(appointment_type_id)).exists()
        if not appointment_type:
            raise ValidationError(_("An appointment type is needed to get the link."))
        return self._get_staff_user_appointment_invite_info(appointment_type)

    @route('/appointment/appointment_type/get_staff_user_appointment_types', type='json', auth='user')
    def appointment_get_user_appointment_types(self):
        appointment_types_info = []
        domain = [('schedule_based_on', '=', 'users'), ('staff_user_ids', 'in', [request.env.user.id]), ('category', 'in', ['punctual', 'recurring'])]
        appointment_types_info = request.env['appointment.type'].search_read(domain, ['name', 'category'])
        return {
            'appointment_types_info': appointment_types_info,
        }

    @route('/appointment/appointment_type/search_create_anytime', type='json', auth='user')
    def appointment_type_search_create_anytime(self, context=None):
        """
        Return the info (id and url) of the anytime appointment type of the actual user.

        Search and return the anytime appointment type for the user.
        In case it doesn't exist yet, it creates an anytime appointment type.
        """
        # Check if the user is a member of group_user to avoid portal user and the like to create appointment types
        if not request.env.user._is_internal():
            raise Forbidden()
        AppointmentType = request.env['appointment.type']
        appointment_type = AppointmentType.search([
            ('category', '=', 'anytime'),
            ('staff_user_ids', 'in', request.env.user.ids)])
        if not appointment_type:
            if context:
                request.update_context(**context)
            appt_type_vals = self._prepare_appointment_type_anytime_values()
            appointment_type = AppointmentType.with_context(
                AppointmentType._get_clean_appointment_context()
            ).create(appt_type_vals)
        return self._get_staff_user_appointment_invite_info(appointment_type)

    # Utility Methods
    # ----------------------------------------------------------

    def _prepare_appointment_type_anytime_values(self):
        return {
            'name': _("%(name)s - Let's meet anytime", name=request.env.user.name),
            'max_schedule_days': 15,
            'category': 'anytime',
        }

    def _get_staff_user_appointment_invite_info(self, appointment_type):
        appointment_invitation_domain = self._get_staff_user_appointment_invite_domain(appointment_type)
        appointment_invitation = request.env['appointment.invite'].search(appointment_invitation_domain, limit=1)
        if not appointment_invitation:
            invitation_values = {
                'appointment_type_ids': appointment_type.ids,
                'resources_choice': 'current_user',
                'staff_user_ids': request.env.user.ids,
            }
            if appointment_type.category == 'custom':
                # Custom appointment users may be edited on the spot. 'all_assigned_resources'
                # allows the link copied to be correctly configured with latest users.
                invitation_values.update({
                    'resources_choice': 'all_assigned_resources',
                    'staff_user_ids': False,
                })
            appointment_invitation = request.env['appointment.invite'].with_context(
                request.env['appointment.type']._get_clean_appointment_context()
            ).create(invitation_values)

        dialog_form_view = request.env.ref(
            'appointment.appointment_type_view_form_custom_share',
            raise_if_not_found=False
        )
        return {
            'appointment_type_id': appointment_type.id,
            'invite_url': appointment_invitation.book_url,
            'view_id': dialog_form_view.id if dialog_form_view else False,
        }

    def _get_staff_user_appointment_invite_domain(self, appointment_type):
        """ Returns the domain used to search for an existing invitation when copying a link
        to any 'punctual' or 'recurring' appointment type in the calendar view. When sharing an
        'anytime' appointment, we search for existing invitations (as the appointment may already
        exist). This prevents duplicating appointment.invite.
        The user can modify 'custom' appointments and share their link more than once. Indeed, the
        'configure' button allows them to change staff users. They can even remove themselves from
        the staff users. As a new 'custom' appointment is created on using the 'select dates' feature
        on the fly, we want to search for the invitation that has been created by the current user. """
        if appointment_type.category == 'custom':
            return [
                ('appointment_type_ids', '=', appointment_type.id),
                ('create_uid', '=', request.env.user.id),
            ]
        return [
            ('appointment_type_ids', '=', appointment_type.id),
            ('staff_user_ids', '=', request.env.user.id),
        ]
