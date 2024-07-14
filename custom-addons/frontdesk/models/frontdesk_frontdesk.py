# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from werkzeug.urls import url_join
from datetime import datetime, timedelta

from odoo import models, fields, api, tools, _

ASK_FIELDS_SELECTION = [
    ("required", "Required"),
    ("optional", "Optional"),
    ("none", "None"),
]

PLANNED_VISITOR_TIME = 45

class Frontdesk(models.Model):
    _name = 'frontdesk.frontdesk'
    _description = 'Frontdesk'

    name = fields.Char('Frontdesk Name', required=True)
    responsible_ids = fields.Many2many('res.users', string='Responsibles', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    theme = fields.Selection(selection=[("light", "Light"), ("dark", "Dark")], default='light')
    image = fields.Image("Image")
    host_selection = fields.Boolean('Host Selection', groups='frontdesk.frontdesk_group_user')
    authenticate_guest = fields.Boolean('Authenticate Guest', default=True, groups='frontdesk.frontdesk_group_user')
    ask_phone = fields.Selection(string='Phone', selection=ASK_FIELDS_SELECTION, default='required', required=True)
    ask_company = fields.Selection(string='Organization', selection=ASK_FIELDS_SELECTION, default='optional', required=True)
    ask_email = fields.Selection(string='Email', selection=ASK_FIELDS_SELECTION, default='none', required=True)
    notify_email = fields.Boolean('Notify by email', groups='frontdesk.frontdesk_group_user')
    mail_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain="[('model', '=', 'frontdesk.frontdesk')]",
        default=lambda self: self.env.ref('frontdesk.frontdesk_mail_template', raise_if_not_found=False)
    )
    notify_sms = fields.Boolean('Notify by SMS', groups='frontdesk.frontdesk_group_user')
    sms_template_id = fields.Many2one(
        'sms.template',
        string='SMS Template',
        domain="[('model', '=', 'frontdesk.frontdesk')]",
        default=lambda self: self.env.ref('frontdesk.frontdesk_sms_template', raise_if_not_found=False)
    )
    self_check_in = fields.Boolean('Self Check-In', groups='frontdesk.frontdesk_group_user',
        help='Shows a QR code in the interface, for guests to check in from their mobile phone.'
    )
    drink_offer = fields.Boolean('Offer Drinks', groups='frontdesk.frontdesk_group_user')
    drink_ids = fields.Many2many('frontdesk.drink')
    notify_discuss = fields.Boolean('Notify by discuss', default=True, groups='frontdesk.frontdesk_group_user')
    description = fields.Html(groups='frontdesk.frontdesk_group_user')
    visitor_ids = fields.One2many('frontdesk.visitor', 'station_id', string='Visitors')
    guest_on_site = fields.Integer('Guests On Site', compute='_compute_dashboard_data')
    pending = fields.Integer('Pending', compute='_compute_dashboard_data')
    drink_to_serve = fields.Integer('Drinks to Serve', compute='_compute_dashboard_data')
    latest_check_in = fields.Char(compute='_compute_dashboard_data')
    visitor_properties_definition = fields.PropertiesDefinition('Visitor Properties')
    access_token = fields.Char("Security Token", default=lambda self: str(uuid.uuid4()), required=True, copy=False, readonly=True)
    kiosk_url = fields.Char('Kiosk URL', compute='_compute_kiosk_url', groups='frontdesk.frontdesk_group_user')
    is_favorite = fields.Boolean()
    active = fields.Boolean(default=True)

    def _compute_dashboard_data(self):
        """ This method computes the number of guests currently on site, the number of pending visitors, the number
        of drinks to serve, and the time of the latest check-in. """
        visitor_data = self.env['frontdesk.visitor']._read_group([
                ('state', 'in', ('checked_in', 'planned')),
                ('station_id', 'in', self.ids),
            ], ['station_id', 'state'], ['__count'])
        checked_in_mapped = {station.id: count for station, state, count in visitor_data if state == 'checked_in'}
        planned_mapped = {station.id: count for station, state, count in visitor_data if state == 'planned'}
        drinks_data = self.env['frontdesk.visitor']._read_group([
                ('drink_ids', '!=', False), ('served', '=', False),
                ('station_id', 'in', self.ids),
            ], ['station_id'], ['__count'])
        drinks_data_mapped = {station.id: count for station, count in drinks_data}
        for frontdesk in self:
            guest_on_site = pending = drink_to_serve = 0
            latest_check_in = False
            if frontdesk.visitor_ids:
                guest_on_site = checked_in_mapped.get(frontdesk.id, 0)
                pending = planned_mapped.get(frontdesk.id, 0)
                drink_to_serve = drinks_data_mapped.get(frontdesk.id, 0)
                last_visitors = frontdesk.visitor_ids.filtered(lambda v: v.state == 'checked_in')
                latest_check_in_time = last_visitors and last_visitors[-1].check_in
                if latest_check_in_time:
                    total_seconds = (datetime.now() - latest_check_in_time).total_seconds()
                    time_diff = int(total_seconds / 60) if total_seconds < 3600 else int(total_seconds / 3600)
                    latest_check_in = _("Last Check-In: %s minutes ago", time_diff) if total_seconds < 3600 \
                        else _("Last Check-In: %s hours ago", time_diff)
            frontdesk.update({
                'guest_on_site': guest_on_site,
                'pending': pending,
                'drink_to_serve': drink_to_serve,
                'latest_check_in': latest_check_in,
            })

    @api.depends('access_token')
    def _compute_kiosk_url(self):
        for frontdesk in self:
            frontdesk.kiosk_url = url_join(frontdesk.get_base_url(), '/kiosk/%s/%s' % (frontdesk.id, frontdesk.access_token))

    def action_open_kiosk(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.kiosk_url,
            'target': 'new',
        }

    def action_open_visitors(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Visitors"),
            'res_model': 'frontdesk.visitor',
            'view_mode': 'tree,form,kanban,graph,pivot,calendar,gantt',
            'context': {
                "search_default_state_is_planned": 1,
                "search_default_state_is_checked_in": 1,
                "search_default_today": 1
            },
            'domain': [('station_id.id', '=', self.id)],
        }

    def _get_frontdesk_field(self):
        return ['description', 'host_selection', 'drink_offer', 'self_check_in', 'theme',
          'drink_ids', 'ask_email', 'ask_phone', 'ask_company', 'authenticate_guest']

    def _get_frontdesk_data(self):
        """ Returns the data to the frontend. """
        self.ensure_one()
        data = {
            'company': {'name': self.company_id.name, 'id': self.company_id.id},
            'langs': [{'code': lang[0], 'name': lang[1]} for lang in self.env['res.lang'].get_installed()],
            'station': self.search_read([('id', '=', self.id)], self._get_frontdesk_field()),
        }
        if self.drink_offer:
            data['drinks'] = self.env['frontdesk.drink'].search_read([('id', 'in', self.drink_ids.ids)], ['name'])
        return data

    def _get_planned_visitors(self):
        """ Returns the planned visitors for quick sign in to the frontend. """
        time_min = datetime.now() - timedelta(minutes=PLANNED_VISITOR_TIME)
        time_max = datetime.now() + timedelta(minutes=PLANNED_VISITOR_TIME)
        visitors = self.env['frontdesk.visitor'].sudo().search_read(
                [('check_in', '>=', time_min), ('check_in', '<=', time_max), ('state', '=', 'planned'), ('station_id.id', '=', self.id)],
                ['name', 'company', 'message', 'host_ids'])
        if visitors:
            return [{
                **visitor,
                'host_ids': [{'id': host.id, 'name': host.name} for host in self.env['hr.employee'].browse(visitor['host_ids'])]
            } for visitor in visitors]
        return []

    def _get_tmp_code(self):
        self.ensure_one()
        return tools.hmac(self.env(su=True), 'kiosk-mobile', (self.id, fields.Date.to_string(fields.Datetime.now())))
