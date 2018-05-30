# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def action_confirm(self):
        self.ensure_one()
        res = super(SaleOrder, self).action_confirm()
        self.order_line._update_registrations(confirm=True)
        if any(self.order_line.filtered(lambda line: line.event_id)):
            return self.env['ir.actions.act_window'].with_context(default_sale_order_id=self.id).for_xml_id('event_sale', 'action_sale_order_event_registration')
        return res


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    event_id = fields.Many2one('event.event', string='Event',
       help="Choose an event and it will automatically create a registration for this event.")
    event_ticket_id = fields.Many2one('event.event.ticket', string='Event Ticket', help="Choose "
        "an event ticket and it will automatically create a registration for this event ticket.")
    event_ok = fields.Boolean(related='product_id.event_ok', readonly=True)

    @api.multi
    def _prepare_invoice_line(self, qty):
        self.ensure_one()
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        if self.event_id:
            res['name'] = '%s: %s' % (res.get('name', ''), self.event_id.name)
        return res

    @api.multi
    def _update_registrations(self, confirm=True, registration_data=None):
        """ Create or update registrations linked to a sale order line. A sale
        order line has a product_uom_qty attribute that will be the number of
        registrations linked to this line. This method update existing registrations
        and create new one for missing one. """
        Registration = self.env['event.registration'].sudo()
        registrations = Registration.search([('sale_order_line_id', 'in', self.ids), ('state', '!=', 'cancel')])
        for so_line in self.filtered('event_id'):
            existing_registrations = registrations.filtered(lambda self: self.sale_order_line_id.id == so_line.id)
            if confirm:
                existing_registrations.filtered(lambda self: self.state != 'open').confirm_registration()
            else:
                existing_registrations.filtered(lambda self: self.state == 'cancel').do_draft()

            for count in range(int(so_line.product_uom_qty) - len(existing_registrations)):
                registration = {}
                if registration_data:
                    registration = registration_data.pop()
                # TDE CHECK: auto confirmation
                registration['sale_order_line_id'] = so_line
                Registration.with_context(registration_force_draft=True).create(
                    Registration._prepare_attendee_values(registration))
        return True

    @api.onchange('event_ticket_id')
    def _onchange_event_ticket_id(self):
        self.price_unit = (self.event_id.company_id or self.env.user.company_id).currency_id.compute(self.event_ticket_id.price, self.order_id.currency_id)
