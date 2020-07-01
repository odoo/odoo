# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventType(models.Model):
    _inherit = "event.type"

    menu_agenda = fields.Boolean(
        string='Agenda Menu on Website', compute='_compute_menu_agenda',
        readonly=False, store=True)

    @api.depends('website_menu')
    def _compute_menu_agenda(self):
        """ Default: website_menu triggers agenda """
        for event_type in self:
            if not event_type.website_menu:
                event_type.menu_agenda = False
            elif not event_type.menu_agenda:
                event_type.menu_agenda = True
