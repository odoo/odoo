# -*- coding: utf-8 -*-

from openerp import models, fields, api


class SaleOrderEventRegistration(models.TransientModel):
    _name = "registration.editor"

    sale_order_id = fields.Many2one('sale.order', 'Sale Order', required=True)
    event_registration_ids = fields.One2many('registration.editor.line', 'editor_id', string='Registrations to Edit')

    @api.model
    def default_get(self, fields):
        res = super(SaleOrderEventRegistration, self).default_get(fields)
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
            existing_registrations = [r for r in registrations if r.event_ticket_id == so_line.event_ticket_id]
            for reg in existing_registrations:
                attendee_list.append({
                    'event_id': reg.event_id.id,
                    'event_ticket_id': reg.event_ticket_id.id,
                    'registration_id': reg.id,
                    'name': reg.name,
                    'email': reg.email,
                    'phone': reg.phone,
                    'sale_order_line_id': so_line.id,
                })
            for count in range(int(so_line.product_uom_qty) - len(existing_registrations)):
                attendee_list.append([0, 0, {
                    'event_id': so_line.event_id.id,
                    'event_ticket_id': so_line.event_ticket_id.id,
                    'sale_order_line_id': so_line.id,
                }])
        res['event_registration_ids'] = attendee_list
        res = self._convert_to_cache(res, validate=False)
        res = self._convert_to_write(res)
        return res

    @api.multi
    def action_make_registration(self):
        Registration = self.env['event.registration']
        for wizard in self:
            for wiz_registration in wizard.event_registration_ids:
                if wiz_registration.registration_id:
                    wiz_registration.registration_id.write(wiz_registration.get_registration_data()[0])
                else:
                    Registration.create(wiz_registration.get_registration_data()[0])
        return {'type': 'ir.actions.act_window_close'}


class RegistrationEditorLine(models.TransientModel):
    """Event Registration"""
    _name = "registration.editor.line"

    editor_id = fields.Many2one('registration.editor')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line')
    event_id = fields.Many2one('event.event', string='Event', required=True)
    registration_id = fields.Many2one('event.registration', 'Original Registration')
    event_ticket_id = fields.Many2one('event.event.ticket', string='Event Ticket')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    name = fields.Char(string='Name', select=True)

    @api.one
    def get_registration_data(self):
        return {
            'event_id': self.event_id.id,
            'event_ticket_id': self.event_ticket_id.id,
            'partner_id': self.editor_id.sale_order_id.partner_id.id,
            'name': self.name or self.editor_id.sale_order_id.partner_id.name,
            'phone': self.phone or self.editor_id.sale_order_id.partner_id.phone,
            'email': self.email or self.editor_id.sale_order_id.partner_id.email,
            'origin': self.editor_id.sale_order_id.name,
            'sale_order_id': self.editor_id.sale_order_id.id,
            'sale_order_line_id': self.sale_order_line_id.id,
        }
