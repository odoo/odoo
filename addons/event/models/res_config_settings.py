# -*- coding: utf-8 -*-

from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_event_sale = fields.Boolean("Tickets")
    module_website_event_meet = fields.Boolean("Discussion Rooms")
    module_website_event_track = fields.Boolean("Tracks and Agenda")
    module_website_event_track_live = fields.Boolean("Live Mode")
    module_website_event_track_quiz = fields.Boolean("Quiz on Tracks")
    module_website_event_track_exhibitor = fields.Boolean("Advanced Sponsors")
    module_website_event_questions = fields.Boolean("Registration Survey")
    module_event_barcode = fields.Boolean("Barcode")
    module_website_event_sale = fields.Boolean("Online Ticketing")
