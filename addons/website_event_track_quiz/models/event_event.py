# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class EventEvent(models.Model):
    _inherit = "event.event"

    # frontend menu management
    community_menu = fields.Boolean(
        "Community", compute="_compute_community_menu",
        readonly=False, store=True,
        help="Display the \"Rooms\" tab on website, redirecting to the leaderboard of the event.")
    community_menu_ids = fields.One2many(
        "website.event.menu", "event_id", string="Event Community Menus",
        domain=[("menu_type", "=", "community")])

    @api.depends("event_type_id", "website_menu", "community_menu")
    def _compute_community_menu(self):
        """At type onchange: synchronize. At website_menu update: synchronize."""
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.community_menu = event.event_type_id.community_menu
            elif event.website_menu and (event.website_menu != event._origin.website_menu or not event.community_menu):
                event.community_menu = True
            elif not event.website_menu:
                event.community_menu = False

    # ------------------------------------------------------------
    # WEBSITE MENU MANAGEMENT
    # ------------------------------------------------------------

    def _get_menu_type_field_matching(self):
        res = super()._get_menu_type_field_matching()
        res["community"] = "community_menu"
        return res

    def _get_menu_update_fields(self):
        return super()._get_menu_update_fields() + ["community_menu"]

    def _get_website_menu_entries(self):
        self.ensure_one()
        return super()._get_website_menu_entries() + [
            (_("Rooms"), "/event/%s/community" % self.env["ir.http"]._slug(self), False, 80, "community", False),
        ]

    def _update_website_menus(self, menus_update_by_field=None):
        super()._update_website_menus(menus_update_by_field=menus_update_by_field)
        for event in self:
            if event.menu_id and (not menus_update_by_field or event in menus_update_by_field.get('community_menu')):
                event._update_website_menu_entry("community_menu", "community_menu_ids", "community")

    def copy_event_menus(self, old_events):
        super().copy_event_menus(old_events)
        for new_event in self:
            new_event.community_menu_ids.menu_id.parent_id = new_event.menu_id
