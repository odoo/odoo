# -*- coding: utf-8 -*-

from odoo import api, fields, models

class event_config_settings(models.TransientModel):
    _name = 'event.config.settings'
    _inherit = 'res.config.settings'

    event_config_type = fields.Selection([
        (1, 'All events are free'),
        (2, 'Allow selling tickets'),
        (3, 'Allow your customer to buy tickets from your eCommerce'),
        ], "Tickets",
        help='Install website_event_sale or event_sale module based on options')
    module_event_sale = fields.Boolean()
    module_website_event_sale = fields.Boolean()
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

    @api.model
    def default_get(self, fields):
        res = super(event_config_settings, self).default_get(fields)
        if 'event_config_type' in fields: res['event_config_type'] = 1
        if 'module_website_event_sale' in fields and res['module_website_event_sale']:
            res['event_config_type'] = 3
        elif 'module_event_sale' in fields and res['module_event_sale']:
            res['event_config_type'] = 2
        return res
         
    @api.onchange('event_config_type')
    def onchange_event_config_type(self):
        if self.event_config_type == 3:
            self.module_website_event_sale = True
        elif self.event_config_type == 2:
            self.write({'module_event_sale': True, 'module_website_event_sale': False})
        else:
            self.write({'module_event_sale': False, 'module_website_event_sale': False})
             
    @api.multi 
    def set_default_event_config_type(self):
        if self.env.user._is_admin() or self.env['res.users'].has_group('event.group_event_manager'):
            IrValues = self.env['ir.values'].sudo()
        else:
            IrValues = self.env['ir.values']
        IrValues.set_default('event.config.settings', 'event_config_type', self.event_config_type)
 
    @api.multi
    def set_default_auto_confirmation(self):
        if self.env.user._is_admin() or self.env['res.users'].has_group('event.group_event_manager'):
            IrValues = self.env['ir.values'].sudo()
        else:
            IrValues = self.env['ir.values']
        IrValues.set_default('event.config.settings', 'auto_confirmation', self.auto_confirmation)

