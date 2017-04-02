# -*- coding: utf-8 -*-

from odoo import api, fields, models

class event_config_settings(models.TransientModel):
    _name = 'event.config.settings'
    _inherit = 'res.config.settings'

    module_event_sale = fields.Selection([
        (0, "All events are free"),
        (1, 'Allow selling tickets')
        ], "Tickets",
        help='Install the event_sale module')
    module_website_event_track = fields.Selection([
        (0, "No mini website per event"),
        (1, 'Allow tracks, agenda and dedicated menus/website per event')
        ], "Tracks and Agenda",
        help='Install the module website_event_track')
    module_website_event_questions = fields.Selection([
        (0, "No extra questions on registrations"),
        (1, 'Allow adding extra questions on registrations')
        ], "Registration Survey",
        help='Install the website_event_questions module')
    auto_confirmation = fields.Selection([
        (1, 'No validation step on registration'),
        (0, "Manually confirm every registration")
        ], "Auto Confirmation",
        help='Unselect this option to manually manage draft event and draft registration')
    module_event_barcode = fields.Boolean("Scan badges to confirm attendances",
        help="Install the event_barcode module")

    @api.multi
    def set_default_auto_confirmation(self):
        if self.env.user._is_admin() or self.env['res.users'].has_group('event.group_event_manager'):
            IrValues = self.env['ir.values'].sudo()
        else:
            IrValues = self.env['ir.values']
        IrValues.set_default('event.config.settings', 'auto_confirmation', self.auto_confirmation)
