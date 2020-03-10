# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventMenu(models.Model):
    _name = "website.event.menu"
    _description = "Website Event Menu"

    menu_id = fields.Many2one('website.menu', string='Menu', ondelete='cascade')
    event_id = fields.Many2one('event.event', string='Event', ondelete='cascade')
    menu_type = fields.Selection([('track', 'Event Tracks Menus'), ('track_proposal', 'Event Proposals Menus')])
