# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, fields, models, _


class AppointmentType(models.Model):
    _inherit = "appointment.type"

    event_videocall_source = fields.Selection(selection_add=[('google_meet', 'Google Meet')], ondelete={'google_meet': 'set default'})
    users_wo_google_calendar_msg = fields.Html('Users Without Google Calendar Synchronization',
        compute='_compute_users_wo_google_calendar_msg')

    @api.depends('staff_user_ids', 'event_videocall_source')
    def _compute_users_wo_google_calendar_msg(self):
        self.users_wo_google_calendar_msg = False
        for appointment_type in self.filtered(lambda apt: apt.event_videocall_source == 'google_meet'):
            users_not_synchronized = appointment_type.staff_user_ids.filtered(
                lambda user: not user.is_google_calendar_synced())
            if users_not_synchronized:
                appointment_type.users_wo_google_calendar_msg = _(
                    '%(user_names)s did not synchronize their Google Calendar account yet, Google Meeting links won\'t be added to their meetings.',
                    user_names=Markup(', ').join(Markup('<b>%s</b>') % user.name for user in users_not_synchronized))
