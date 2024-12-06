# -*- coding: utf-8 -*-

from collections import Counter, defaultdict

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RegistrationEditor(models.TransientModel):
    _name = 'registration.editor'
    _description = 'Edit Attendee Details on Sales Confirmation'

    sale_order_id = fields.Many2one('sale.order', 'Sales Order', required=True, ondelete='cascade')
    event_registration_ids = fields.One2many('registration.editor.line', 'editor_id', string='Registrations to Edit')

    @api.model
    def default_get(self, fields):
        res = super(RegistrationEditor, self).default_get(fields)
        if not res.get('sale_order_id'):
            sale_order_id = res.get('sale_order_id', self._context.get('active_id'))
            res['sale_order_id'] = sale_order_id
        sale_order = self.env['sale.order'].browse(res.get('sale_order_id'))
        registrations = self.env['event.registration'].search([
            ('sale_order_id', '=', sale_order.id),
            ('event_ticket_id', 'in', sale_order.mapped('order_line.event_ticket_id').ids),
            ('state', '!=', 'cancel')])

        so_lines = sale_order.order_line.filtered('event_ticket_id')
        so_line_to_reg = registrations.grouped('sale_order_line_id')
        attendee_list = []
        for so_line in so_lines:
            registrations = so_line_to_reg.get(so_line, self.env['event.registration'])
            # Add existing registrations
            attendee_list += [[0, 0, {
                'event_id': reg.event_id.id,
                'event_ticket_id': reg.event_ticket_id.id,
                'registration_id': reg.id,
                'name': reg.name,
                'email': reg.email,
                'phone': reg.phone,
                'sale_order_line_id': so_line.id,
            }] for reg in registrations]
            # Add new registrations
            attendee_list += [[0, 0, {
                'event_id': so_line.event_id.id,
                'event_ticket_id': so_line.event_ticket_id.id,
                'sale_order_line_id': so_line.id,
                'name': so_line.order_partner_id.name,
                'email': so_line.order_partner_id.email,
                'phone': so_line.order_partner_id.phone,
            }] for _count in range(int(so_line.product_uom_qty) - len(registrations))]
        res['event_registration_ids'] = attendee_list
        res = self._convert_to_write(res)
        return res

    def action_make_registration(self):
        self.ensure_one()
        registrations_to_create = []
        for registration_line in self.event_registration_ids:
            if registration_line.registration_id:
                registration_line.registration_id.write(registration_line._prepare_registration_data())
            else:
                registrations_to_create.append(registration_line._prepare_registration_data(include_event_values=True))

        self.env['event.registration'].create(registrations_to_create)

        return {'type': 'ir.actions.act_window_close'}


class RegistrationEditorLine(models.TransientModel):
    """Event Registration"""
    _name = 'registration.editor.line'
    _description = 'Edit Attendee Line on Sales Confirmation'
    _order = "id desc"

    editor_id = fields.Many2one('registration.editor')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sales Order Line')
    event_id = fields.Many2one('event.event', string='Event', required=True)
    company_id = fields.Many2one(related="event_id.company_id")
    registration_id = fields.Many2one('event.registration', 'Original Registration')
    event_ticket_id = fields.Many2one('event.event.ticket', string='Event Ticket')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    name = fields.Char(string='Name')

    def _prepare_registration_data(self, include_event_values=False):
        self.ensure_one()
        registration_data = {
            'partner_id': self.editor_id.sale_order_id.partner_id.id,
            'name': self.name or self.editor_id.sale_order_id.partner_id.name,
            'phone': self.phone or self.editor_id.sale_order_id.partner_id.phone or self.editor_id.sale_order_id.partner_id.mobile,
            'email': self.email or self.editor_id.sale_order_id.partner_id.email,
        }
        if include_event_values:
            registration_data.update({
                'event_id': self.event_id.id,
                'event_ticket_id': self.event_ticket_id.id,
                'sale_order_id': self.editor_id.sale_order_id.id,
                'sale_order_line_id': self.sale_order_line_id.id,
            })
        return registration_data
