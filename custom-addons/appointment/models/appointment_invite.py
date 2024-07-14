# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import uuid
from markupsafe import Markup
from werkzeug.urls import url_encode, url_join

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

SHORT_CODE_PATTERN = re.compile(r"^[\w-]+$")


class AppointmentShare(models.Model):
    _name = 'appointment.invite'
    _description = 'Appointment Invite'
    _order = 'create_date DESC, id DESC'
    _rec_name = 'short_code'

    access_token = fields.Char('Token', default=lambda s: uuid.uuid4(), required=True, copy=False, readonly=True)
    short_code = fields.Char('Short Code', default=lambda s: s._get_unique_short_code(), required=True)
    short_code_format_warning = fields.Boolean('Short Code Format Warning', compute="_compute_short_code_warning")
    short_code_unique_warning = fields.Boolean('Short Code Unique Warning', compute="_compute_short_code_warning")
    disable_save_button = fields.Boolean('Computes if alert is present', compute='_compute_disable_save_button')

    base_book_url = fields.Char('Base Link URL', compute="_compute_base_book_url")
    book_url = fields.Char('Link URL', compute='_compute_book_url')
    redirect_url = fields.Char('Redirect URL', compute='_compute_redirect_url')

    # Put active_test to False because we always want to be able to check all appointment types from an invitation.
    # In case the appointment type is archived, we still want old links to work and display with a message telling
    # that it's no longer available.
    appointment_type_ids = fields.Many2many('appointment.type', string='Appointment Types',
        domain="[('category', 'in', ['punctual', 'recurring'])]", context={"active_test": False})
    appointment_type_info_msg = fields.Html('No User Assigned Message', compute='_compute_appointment_type_info_msg')
    appointment_type_count = fields.Integer('Selected Appointments Count', compute='_compute_appointment_type_count', store=True)
    schedule_based_on = fields.Char('Schedule Based On', compute="_compute_schedule_based_on")
    suggested_resource_ids = fields.Many2many('appointment.resource', related="appointment_type_ids.resource_ids", string="Possible resources")
    suggested_resource_count = fields.Integer('# Resources', compute='_compute_suggested_resource_count')
    suggested_staff_user_ids = fields.Many2many(
        'res.users', related='appointment_type_ids.staff_user_ids', string='Possible users',
        help="Get the users linked to the appointment type selected to apply a domain on the users that can be selected")
    suggested_staff_user_count = fields.Integer('# Staff Users', compute='_compute_suggested_staff_user_count')
    resources_choice = fields.Selection(
        selection=[
            ('current_user', 'Me (only with Users)'),
            ('all_assigned_resources', 'Any User/Resource'),
            ('specific_resources', 'Specific Users/Resources')],
        string='Assign to', compute='_compute_resources_choice', store=True, readonly=False)
    resource_ids = fields.Many2many('appointment.resource', string='Resources', domain="[('id', 'in', suggested_resource_ids)]",
        compute='_compute_resource_ids', store=True, readonly=False)
    staff_user_ids = fields.Many2many('res.users', string='Users', domain="[('id', 'in', suggested_staff_user_ids)]",
        compute='_compute_staff_user_ids', store=True, readonly=False)

    calendar_event_ids = fields.One2many('calendar.event', 'appointment_invite_id', string="Booked Appointments", readonly=True)
    calendar_event_count = fields.Integer('# Bookings', compute="_compute_calendar_event_count")

    _sql_constraints = [
        ('short_code_uniq', 'UNIQUE (short_code)', 'The URL is already taken, please pick another code.')
    ]

    @api.depends('short_code_format_warning',
            'short_code_unique_warning',
            'appointment_type_count',
            'suggested_resource_count',
            'suggested_staff_user_ids',
            'resources_choice')
    def _compute_disable_save_button(self):
        for invite in self:
            conditions = [
                invite.short_code_format_warning,
                invite.short_code_unique_warning,
                invite.appointment_type_count == 1 and invite.resources_choice == 'current_user' and self.env.user.id not in invite.suggested_staff_user_ids.ids,
                not invite.suggested_staff_user_ids and invite.appointment_type_count == 1 and invite.suggested_resource_count < 1,
            ]
            invite.disable_save_button = any(conditions)

    @api.constrains('short_code')
    def _check_short_code_format(self):
        invalid_invite = next((invite for invite in self if invite.short_code_format_warning), False)
        if invalid_invite:
            raise ValidationError(_(
                "Only letters, numbers, underscores and dashes are allowed in your links. You need to adapt %s.", invalid_invite.short_code
            ))

    @api.depends('appointment_type_ids')
    def _compute_schedule_based_on(self):
        """ Get the schedule_based_on value when selecting one appointment type.
        This allows to personalize the warning or info message based on this value. """
        for invite in self:
            invite.schedule_based_on = invite.appointment_type_ids.schedule_based_on if len(invite.appointment_type_ids) == 1 else False

    @api.depends('appointment_type_ids', 'appointment_type_count')
    def _compute_appointment_type_info_msg(self):
        '''
            When there is more than one appointment type selected to be shared and at least one doesn't have any staff user or resource assigned,
            display an alert info to tell the current user that, without staff users or resources, an appointment type won't be published.
        '''
        for invite in self:
            appt_without_staff_user = invite.appointment_type_ids.filtered_domain([('schedule_based_on', '=', 'users'), ('staff_user_ids', '=', False)])
            appt_without_resource = invite.appointment_type_ids.filtered_domain([('schedule_based_on', '=', 'resources'), ('resource_ids', '=', False)])
            appointment_type_info_msg = Markup()
            if appt_without_staff_user and invite.appointment_type_count > 1:
                appointment_type_info_msg += _(
                    'The following appointment type(s) have no staff assigned: %s.',
                    ', '.join(appt_without_staff_user.mapped('name'))
                ) + Markup('<br/>')
            if appt_without_resource and invite.appointment_type_count > 1:
                appointment_type_info_msg += _(
                    'The following appointment type(s) have no resource assigned: %s.',
                    ', '.join(appt_without_resource.mapped('name'))
                )
            invite.appointment_type_info_msg = appointment_type_info_msg if appointment_type_info_msg else False

    @api.depends('appointment_type_ids')
    def _compute_appointment_type_count(self):
        appointment_data = self.env['appointment.type']._read_group(
            [('appointment_invite_ids', 'in', self.ids)],
            ['appointment_invite_ids'],
            ['__count'],
        )
        mapped_data = {appointment_invite.id: count for appointment_invite, count in appointment_data}
        for invite in self:
            if isinstance(invite.id, models.NewId):
                invite.appointment_type_count = len(invite.appointment_type_ids)
            else:
                invite.appointment_type_count = mapped_data.get(invite.id, 0)

    @api.depends('short_code')
    def _compute_base_book_url(self):
        for invite in self:
            invite.base_book_url = url_join(invite.get_base_url(), '/book/')

    @api.depends('calendar_event_ids')
    def _compute_calendar_event_count(self):
        appointment_invite_data = self.env['calendar.event']._read_group(
            [('appointment_invite_id', 'in', self.ids)],
            ['appointment_invite_id'],
            ['__count'],
        )
        mapped_data = {invite.id: count for invite, count in appointment_invite_data}
        for invite in self:
            invite.calendar_event_count = mapped_data.get(invite.id, 0)

    @api.depends('short_code')
    def _compute_short_code_warning(self):
        for invite in self:
            invite.short_code_format_warning = not bool(re.match(SHORT_CODE_PATTERN, invite.short_code)) if invite.short_code else False
            invite.short_code_unique_warning = bool(self.env['appointment.invite'].search_count([
                ('id', '!=', invite._origin.id), ('short_code', '=', invite.short_code)]))

    @api.depends('appointment_type_ids')
    def _compute_resources_choice(self):
        for invite in self:
            if len(invite.appointment_type_ids) != 1:
                invite.resources_choice = False
            elif invite.appointment_type_ids.schedule_based_on == 'users' and self.env.user in invite.appointment_type_ids._origin.staff_user_ids:
                invite.resources_choice = 'current_user'
            else:
                invite.resources_choice = 'all_assigned_resources'

    @api.depends('appointment_type_ids')
    def _compute_resource_ids(self):
        for invite in self:
            if len(invite.appointment_type_ids) > 1 or invite.appointment_type_ids.schedule_based_on != 'resources':
                invite.resource_ids = False

    @api.depends('appointment_type_ids', 'resources_choice')
    def _compute_staff_user_ids(self):
        for invite in self:
            if invite.resources_choice == "current_user" and \
                    self.env.user.id in invite.appointment_type_ids.staff_user_ids.ids:
                invite.staff_user_ids = self.env.user
            else:
                invite.staff_user_ids = False

    @api.depends('suggested_resource_ids')
    def _compute_suggested_resource_count(self):
        for invite in self:
            invite.suggested_resource_count = len(invite.suggested_resource_ids)

    @api.depends('suggested_staff_user_ids')
    def _compute_suggested_staff_user_count(self):
        for invite in self:
            invite.suggested_staff_user_count = len(invite.suggested_staff_user_ids)

    @api.depends('base_book_url', 'short_code')
    def _compute_book_url(self):
        """
        Compute a short link linked to an appointment invitation.
        """
        for invite in self:
            invite.book_url = url_join(invite.base_book_url, invite.short_code) if invite.short_code else False

    @api.depends('appointment_type_ids', 'staff_user_ids', 'resource_ids')
    def _compute_redirect_url(self):
        """
        Compute a link that will be share for the user depending on the appointment types and users
        selected. We allow to preselect a group of them if there is only one appointment type selected.
        Indeed, it would be too complex to manage ones with multiple appointment types.
        Three possible params can be generated with the link:
            - filter_resource_ids: which allows the user to select a resource between the ones selected
            - filter_staff_user_ids: which allows the user to select an user between the ones selected
            - filter_appointment_type_ids: which display a selection of appointment types to user from which
            they can choose
        """
        for invite in self:
            if len(invite.appointment_type_ids) == 1:
                base_redirect_url = url_join("/appointment/", str(invite.appointment_type_ids.id))
            else:
                base_redirect_url = '/appointment'

            invite.redirect_url = '%s?%s' % (
                base_redirect_url,
                url_encode(invite._get_redirect_url_parameters()),
            )

    @api.model
    def _get_invitation_url_parameters(self):
        """ Returns invitation-related url parameters we want to keep between the different steps of booking """
        return {'filter_appointment_type_ids', 'filter_resource_ids', 'filter_staff_user_ids', 'invite_token'}

    def _get_meeting_categories_for_appointment(self):
        """ Get the categories that will be linked to the meetings created from the invite
            :return <calendar.event.type> recordset:
        """
        return self.env.ref('appointment.calendar_event_type_data_online_appointment', raise_if_not_found=False)

    def _get_redirect_url_parameters(self):
        self.ensure_one()
        url_param = {
            'invite_token': self.access_token,
        }
        if self.appointment_type_ids:
            url_param.update({
                'filter_appointment_type_ids': str(self.appointment_type_ids.ids),
            })
        if self.staff_user_ids:
            url_param.update({
                'filter_staff_user_ids': str(self.staff_user_ids.ids)
            })
        elif self.resource_ids:
            url_param.update({
                'filter_resource_ids': str(self.resource_ids.ids)
            })
        return url_param

    def _check_appointments_params(self, appointment_types, users, resources):
        """
        Check if the param receive through the URL match with the appointment invite info
        :param recordset appointment_types: the appointment types representing the filter_appointment_type_ids
        :param recordset users: the staff users representing the filter_staff_user_ids
        :param recordset resources: the resources representing the filter_resource_ids
        """
        self.ensure_one()
        if (self.appointment_type_ids and self.appointment_type_ids != appointment_types) or self.staff_user_ids != users or self.resource_ids != resources:
            return False
        return True

    def _get_unique_short_code(self, short_code=False):
        short_access_token = self.access_token[:8] if self.access_token else uuid.uuid4().hex[:8]
        short_code = short_code or self.short_code or short_access_token
        nb_short_code = self.env['appointment.invite'].search_count([('id', '!=', self._origin.id), ('short_code', '=', short_code)])
        if bool(nb_short_code):
            short_code = "%s_%s" % (short_code, nb_short_code)
        return short_code

    @api.autovacuum
    def _gc_appointment_invite(self):
        limit_dt = fields.Datetime.subtract(fields.Datetime.now(), months=6)

        invites = self.env['appointment.invite'].search([('create_date', '<=', limit_dt)])

        to_remove = invites.filtered(lambda invite: not invite.calendar_event_ids or max([event.stop for event in invite.calendar_event_ids]) < limit_dt)
        to_remove.unlink()
