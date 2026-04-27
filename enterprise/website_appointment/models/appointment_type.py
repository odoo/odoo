# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons.website_appointment.controllers.appointment import WebsiteAppointment


class AppointmentType(models.Model):
    _name = "appointment.type"
    _inherit = [
        'appointment.type',
        'website.seo.metadata',
        'website.published.multi.mixin',
        'website.searchable.mixin',
    ]

    def _compute_website_url(self):
        super()._compute_website_url()
        for appointment_type in self:
            if appointment_type.id:
                appointment_type.website_url = '/appointment/%s' % appointment_type.id
            else:
                appointment_type.website_url = False

    def create_and_get_website_url(self, **kwargs):
        if 'appointment_tz' not in kwargs:
            # appointment_tz is a mandatory field defaulting to the environment user's timezone
            # however, sometimes the current user timezone is not defined, let's use a fallback
            website_visitor = self.env['website.visitor']._get_visitor_from_request(force_create=False)
            kwargs['appointment_tz'] = self.env.user.tz or website_visitor.timezone or 'UTC'

        return super().create_and_get_website_url(**kwargs)

    def copy_data(self, default=None):
        """ Force False manually for all categories of appointment type when duplicating
        even for categories that should be auto-publish. """
        default = dict(default or {})
        default['is_published'] = False
        return super().copy_data(default=default)

    def get_backend_menu_id(self):
        return self.env.ref('calendar.mail_menu_calendar').id

    @api.model
    def _search_get_detail(self, website, order, options):
        invite_token = options.get('invite_token')
        allowed_appointment_type_ids = WebsiteAppointment._fetch_and_check_private_appointment_types(
            options.get('filter_appointment_type_ids'),
            options.get('filter_staff_user_ids'),
            options.get('filter_resource_ids'),
            invite_token,
            domain=WebsiteAppointment._appointments_base_domain(
                filter_appointment_type_ids=options.get('filter_appointment_type_ids'),
                search=options.get('search'),
                invite_token=invite_token,
                additional_domain=WebsiteAppointment._appointment_website_domain(self),
                filter_countries=True,
            )
        ).ids

        domain = [[('id', 'in', allowed_appointment_type_ids)]]

        search_fields = ['name']
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
            'website_url': {'name': 'website_url', 'type': 'url', 'truncate': False, 'html': False},
        }

        mapping['detail'] = {'name': 'appointment_duration_formatted', 'type': 'text', 'html': True}
        if options['displayDescription']:
            mapping['description'] = {'name': 'message_intro', 'type': 'text', 'html': True, 'truncate': True}

        return {
            'base_domain': domain,
            'fetch_fields': [value['name'] for _, value in mapping.items()],
            'icon': 'fa-calendar',
            'mapping': mapping,
            'model': 'appointment.type',
            'requires_sudo': bool(invite_token),
            'search_fields': search_fields,
        }

    def action_share_invite(self):
        action = super().action_share_invite()
        if self.env.user.has_group('website.group_multi_website'):
            website_id = self.website_id
        else:
            website_id = self.env['website']
        action['context'].update({'default_website_id': website_id.id})
        return action
