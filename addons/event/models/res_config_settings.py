# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_event_sale = fields.Boolean("Tickets")
    module_website_event_meet = fields.Boolean("Discussion Rooms")
    module_website_event_track = fields.Boolean("Tracks and Agenda")
    module_website_event_track_live = fields.Boolean("Live Mode")
    module_website_event_track_quiz = fields.Boolean("Quiz on Tracks")
    module_website_event_exhibitor = fields.Boolean("Advanced Sponsors")
    module_website_event_questions = fields.Boolean("Registration Survey")
    module_event_barcode = fields.Boolean("Barcode")
    module_website_event_sale = fields.Boolean("Online Ticketing")
    module_event_booth = fields.Boolean("Booth Management")

    @api.onchange('module_website_event_track')
    def _onchange_module_website_event_track(self):
        """ Reset sub-modules, otherwise you may have track to False but still
        have track_live or track_quiz to True, meaning track will come back due
        to dependencies of modules. """
        for config in self:
            if not config.module_website_event_track:
                config.module_website_event_track_live = False
                config.module_website_event_track_quiz = False
