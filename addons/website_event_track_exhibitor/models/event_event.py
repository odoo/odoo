# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug


class EventType(models.Model):
    _inherit = "event.type"

    website_exhibitor = fields.Boolean(
        string='Exhibitors on Website', compute='_compute_website_menu_data',
        readonly=False, store=True)

    @api.depends('website_menu')
    def _compute_website_menu_data(self):
        super(EventType, self)._compute_website_menu_data()
        for event_type in self:
            if not event_type.website_menu:
                event_type.website_exhibitor = False

class EventEvent(models.Model):
    _inherit = "event.event"

    website_exhibitor = fields.Boolean(
        string='Exhibitors on Website', compute='_compute_website_exhibitor',
        readonly=False, store=True)
    exhibitor_menu_ids = fields.One2many(
        'website.event.menu', 'event_id', string='Exhibitors Menus',
        domain=[('menu_type', '=', 'exhibitor')])

    @api.depends('event_type_id', 'website_exhibitor')
    def _compute_website_exhibitor(self):
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.website_exhibitor = event.event_type_id.website_exhibitor
            elif not event.website_exhibitor:
                event.website_exhibitor = False

    def write(self, values):
        exhibitor_activated = self.filtered(lambda event: event.website_exhibitor)
        exhibitor_activated_deactivated = self.filtered(lambda event: not event.website_exhibitor)
        super(EventEvent, self).write(values)
        to_deactivate = exhibitor_activated.filtered(lambda event: not event.website_exhibitor)
        to_activate = exhibitor_activated_deactivated.filtered(lambda event: event.website_exhibitor)
        (to_activate | to_deactivate)._update_website_exhibitor_menus()

    def _update_website_exhibitor_menus(self):
        for event in self:
            if event.website_exhibitor and not event.exhibitor_menu_ids:
                for sequence, (name, url, xml_id, menu_type) in enumerate(event._get_exhibitor_menu_entries()):
                    menu = super(EventEvent, event)._create_menu(sequence, name, url, xml_id)
                    event.env['website.event.menu'].create({
                        'menu_id': menu.id,
                        'event_id': event.id,
                        'menu_type': menu_type,
                    })
            elif not event.website_exhibitor:
                event.exhibitor_menu_ids.mapped('menu_id').unlink()

    def _get_exhibitor_menu_entries(self):
        self.ensure_one()
        res = [(_('Exhibitors'), '/event/%s/exhibitors' % slug(self), False, 'exhibitor')]
        return res

    def toggle_website_exhibitor(self, val):
        self.website_exhibitor = val
