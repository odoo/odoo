# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug


class EventEvent(models.Model):
    _inherit = "event.event"

    social_menu = fields.Boolean(
        'Showcase Twitter Wall', compute='_compute_social_menu',
        readonly=False, store=True)
    twitter_wall_id = fields.Many2one('website.twitter.wall', string="Twitter Wall")
    social_menu_ids = fields.One2many(
        'website.event.menu', 'event_id', string='Social Menus',
        domain=[('menu_type', '=', 'social')])

    # ------------------------------------------------------------
    # WEBSITE MENU MANAGEMENT
    # ------------------------------------------------------------

    @api.depends('website_menu', 'twitter_wall_id', 'event_type_id')
    def _compute_social_menu(self):
        """ If the main menu is checked and we have a twitter wall configured: show 'Social' menu entry """
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.social_menu = event.event_type_id.social_menu
            elif not event.twitter_wall_id:
                event.social_menu = False
            elif event.website_menu and (event.website_menu != event._origin.website_menu or not event.social_menu):
                event.social_menu = True
            elif not event.social_menu:
                event.social_menu = False

    def _get_menu_update_fields(self):
        return super(EventEvent, self)._get_menu_update_fields() + ['social_menu']

    def _update_website_menus(self, menus_update_by_field=None):
        super(EventEvent, self)._update_website_menus(menus_update_by_field=menus_update_by_field)
        for event in self:
            if event.menu_id and (not menus_update_by_field or event in menus_update_by_field.get('social_menu')):
                event._update_website_menu_entry('social_menu', 'social_menu_ids', 'social')

    def _get_menu_type_field_matching(self):
        res = super(EventEvent, self)._get_menu_type_field_matching()
        res['social'] = 'social_menu'
        return res

    def _get_website_menu_entries(self):
        self.ensure_one()
        return super(EventEvent, self)._get_website_menu_entries() + [
            (_('Social'), '/event/%s/social' % slug(self), False, 85, 'social')
        ]
