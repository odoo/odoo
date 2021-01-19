# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventBoothSlotEditor(models.TransientModel):
    _name = 'event.slot.editor'
    _description = 'Edit Slot Details on Sales Confirmation'

    sale_order_id = fields.Many2one('sale.order', 'Sales Order', required=True)
    event_slot_ids = fields.One2many('event.slot.editor.line', 'editor_id', string='Slots to Edit')

    @api.model
    def default_get(self, fields):
        res = super(EventBoothSlotEditor, self).default_get(fields)
        if not res.get('sale_order_id'):
            res['sale_order_id'] = self._context.get('active_id')
        sale_order_id = self.env['sale.order'].browse(res.get('sale_order_id'))
        registrations = self.env['event.booth.registration'].search([
            ('sale_order_id', '=', sale_order_id.id),
        ])

        booth_list = []
        for so_line in filter(lambda sol: sol.is_event_booth, sale_order_id.order_line):
            existing_registration = registrations.filtered(lambda reg: reg.sale_order_line_id == so_line)
            booth_list.append([0, 0, {
                'sale_order_line_id': so_line.id,
                'slot_registration_id': existing_registration.id,
                'name': so_line.order_partner_id.name,
                'email': so_line.order_partner_id.email,
                'phone': so_line.order_partner_id.phone,
                'mobile': so_line.order_partner_id.mobile,
            }])
        res['event_slot_ids'] = booth_list
        res = self._convert_to_write(res)
        return res

    def action_confirm_registration(self):
        self.ensure_one()
        registration_to_create = []
        for line in self.event_slot_ids:
            values = line._get_details_data()
            if line.slot_registration_id:
                line.slot_registration_id.write(values)
            else:
                registration_to_create.append(values)

        if registration_to_create:
            self.env['event.booth.registration'].create(registration_to_create)

        return {'type': 'ir.actions.act_window_close'}


class SlotEditorLine(models.TransientModel):
    _name = 'event.slot.editor.line'
    _description = 'Edit Slot Line on Sales Confirmation'

    editor_id = fields.Many2one('event.slot.editor')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sales Order Line')
    slot_registration_id = fields.Many2one('event.booth.registration', string='Registration')
    event_id = fields.Many2one(related='sale_order_line_id.event_id')
    event_booth_id = fields.Many2one(related='sale_order_line_id.event_booth_id')
    event_booth_slot_ids = fields.Many2many(related='sale_order_line_id.event_booth_slot_ids')
    description = fields.Text(compute='_compute_description')
    topic = fields.Char(string='Topic')
    name = fields.Char(string='Name')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')

    @api.depends('event_booth_slot_ids')
    def _compute_description(self):
        for line in self:
            line.description = line.event_booth_slot_ids._get_booth_multiline_description()

    def _get_details_data(self):
        self.ensure_one()
        return {
            'partner_id': self.editor_id.sale_order_id.partner_id.id,
            'booth_slot_ids': self.event_booth_slot_ids,
            'name': self.topic,
            'contact_name': self.name,
            'contact_email': self.email,
            'contact_phone': self.phone,
            'contact_mobile': self.mobile,
            'sale_order_id': self.editor_id.sale_order_id.id,
            'sale_order_line_id': self.sale_order_line_id.id,
        }
