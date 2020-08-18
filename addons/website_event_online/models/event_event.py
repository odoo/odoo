# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from pytz import timezone, utc

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.resource.models.resource import float_to_time
from odoo.osv import expression


class Event(models.Model):
    _name = 'event.event'
    _inherit = 'event.event'

    # frontend options
    menu_register_cta = fields.Boolean(
        'Add Register Button', compute='_compute_menu_register_cta',
        readonly=False, store=True)
    # live information
    is_ongoing = fields.Boolean(
        'Is Ongoing', compute='_compute_time_data', search='_search_is_ongoing',
        help="Whether event has begun")
    is_done = fields.Boolean(
        'Is Done', compute='_compute_time_data',
        help="Whether event is finished")
    start_today = fields.Boolean(
        'Start Today', compute='_compute_time_data',
        help="Whether event is going to start today if still not ongoing")
    start_remaining = fields.Integer(
        'Remaining before start', compute='_compute_time_data',
        help="Remaining time before event starts (minutes)")

    @api.depends('website_menu')
    def _compute_menu_register_cta(self):
        for event in self:
            event.menu_register_cta = event.website_menu

    @api.depends('date_begin', 'date_end')
    def _compute_time_data(self):
        """ Compute start and remaining time. Do everything in UTC as we compute only
        time deltas here. """
        now_utc = utc.localize(fields.Datetime.now().replace(microsecond=0))
        for event in self:
            date_begin_utc = utc.localize(event.date_begin, is_dst=False)
            date_end_utc = utc.localize(event.date_end, is_dst=False)
            event.is_ongoing = date_begin_utc <= now_utc <= date_end_utc
            event.is_done = now_utc > date_end_utc
            event.start_today = date_begin_utc.date() == now_utc.date()
            if date_begin_utc >= now_utc:
                td = date_begin_utc - now_utc
                event.start_remaining = int(td.total_seconds() / 60)
            else:
                event.start_remaining = 0

    def _compute_is_participating(self):
        """ Override is_participating to improve heuristic that is now

          * public, no visitor: not participating as we have no information;
          * public and visitor: check visitor is linked to a registration. As
            visitors are merged on the top parent, current visitor check is
            sufficient even for successive visits;
          * logged, no visitor: check partner is linked to a registration. Do
            not check the email as it is not really secure;
          * logged as visitor: check partner or visitor are linked to a
            registration;
        """
        current_visitor = self.env['website.visitor']._get_visitor_from_request(force_create=False)
        if self.env.user._is_public() and not current_visitor:
            events = self.env['event.event']
        elif self.env.user._is_public():
            events = self.env['event.registration'].sudo().search([
                ('event_id', 'in', self.ids),
                ('visitor_id', '=', current_visitor.id),
            ]).event_id
        else:
            if current_visitor:
                domain = [
                    '|',
                    ('partner_id', '=', self.env.user.partner_id.id),
                    ('visitor_id', '=', current_visitor.id)
                ]
            else:
                domain = [('partner_id', '=', self.env.user.partner_id.id)]
            events = self.env['event.registration'].sudo().search(
                expression.AND([
                    domain,
                    [('event_id', 'in', self.ids)]
                ])
            ).event_id


        for event in self:
            event.is_participating = event in events
