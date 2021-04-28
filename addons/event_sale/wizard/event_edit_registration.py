# -*- coding: utf-8 -*-

from odoo import models, fields, api


class RegistrationEditor(models.TransientModel):
    _name = "registration.editor"
    _description = 'Edit Attendee Details on Sales Confirmation'

    sale_order_id = fields.Many2one('sale.order', 'Sales Order', required=True)
    event_registration_ids = fields.One2many('registration.editor.line', 'editor_id', string='Registrations to Edit')
    show_event_column = fields.Boolean("Show Event Column",
                                       compute="_compute_show_event_column",
                                       help="Technical field used to determine if the event column must be shown or not")

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

        attendee_list = []
        for so_line in [l for l in sale_order.order_line if l.event_ticket_id]:
            existing_registrations = [r for r in registrations if r.sale_order_line_id.id == so_line.id]
            for reg in existing_registrations:
                attendee_list.append([0, 0, {
                    'event_id': reg.event_id.id,
                    'event_ticket_id': reg.event_ticket_id.id,
                    'registration_id': reg.id,
                    'name': reg.name,
                    'email': reg.email,
                    'phone': reg.phone,
                    'mobile': reg.mobile,
                    'sale_order_line_id': so_line.id,
                }])
            for count in range(int(so_line.product_uom_qty) - len(existing_registrations)):
                attendee_list.append([0, 0, {
                    'event_id': so_line.event_id.id,
                    'event_ticket_id': so_line.event_ticket_id.id,
                    'sale_order_line_id': so_line.id,
                    'name': so_line.order_partner_id.name,
                    'email': so_line.order_partner_id.email,
                    'phone': so_line.order_partner_id.phone,
                    'mobile': so_line.order_partner_id.mobile,
                }])
        res['event_registration_ids'] = attendee_list
        res = self._convert_to_write(res)
        return res

    @api.depends('event_registration_ids')
    def _compute_show_event_column(self):
        for event_edit_registration in self:
            #only show event column if there are multiple events
            event_edit_registration.show_event_column = len(event_edit_registration.event_registration_ids.event_id) > 1

    def action_make_registration(self):
        self.ensure_one()
        registrations_to_create = []
        for registration_line in self.event_registration_ids:
            values = registration_line.get_registration_data()
            if registration_line.registration_id:
                registration_line.registration_id.write(values)
            else:
                registrations_to_create.append(values)

        self.env['event.registration'].create(registrations_to_create)
        self.sale_order_id.order_line._update_registrations(confirm=self.sale_order_id.amount_total == 0)

        return {'type': 'ir.actions.act_window_close'}


class RegistrationEditorLine(models.TransientModel):
    """Event Registration"""
    _name = "registration.editor.line"
    _description = 'Edit Attendee Line on Sales Confirmation'
    _order = 'event_id, event_ticket_id'

    editor_id = fields.Many2one('registration.editor')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sales Order Line')
    event_id = fields.Many2one('event.event', string='Event')
    registration_id = fields.Many2one('event.registration', 'Original Registration')
    event_ticket_id = fields.Many2one('event.event.ticket', string='Ticket Type')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    name = fields.Char(string='Name', index=True)
    state = fields.Selection([('cancel', 'Cancelled'), ('open', 'Confirmed'), ('draft', 'Unconfirmed')],
                             string='Status', default='open')

    def get_registration_data(self):
        self.ensure_one()
        return {
            'event_id': self.event_id.id,
            'event_ticket_id': self.event_ticket_id.id,
            'partner_id': self.editor_id.sale_order_id.partner_id.id,
            'name': self.name or self.editor_id.sale_order_id.partner_id.name,
            'phone': self.phone or self.editor_id.sale_order_id.partner_id.phone,
            'mobile': self.mobile or self.editor_id.sale_order_id.partner_id.mobile,
            'email': self.email or self.editor_id.sale_order_id.partner_id.email,
            'state': self.state,
            'sale_order_id': self.editor_id.sale_order_id.id,
            'sale_order_line_id': self.sale_order_line_id.id,
        }
