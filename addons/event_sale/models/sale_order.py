# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _action_confirm(self):
        res = super(SaleOrder, self)._action_confirm()
        for so in self:
            # confirm registration if it was free (otherwise it will be confirmed once invoice fully paid)
            so.order_line._update_registrations(confirm=so.amount_total == 0, cancel_to_draft=False)
        return res

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for so in self:
            if any(so.order_line.filtered(lambda line: line.event_id)):
                return self.env['ir.actions.act_window'] \
                    .with_context(default_sale_order_id=so.id) \
                    .for_xml_id('event_sale', 'action_sale_order_event_registration')
        return res


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    event_id = fields.Many2one('event.event', string='Event',
       help="Choose an event and it will automatically create a registration for this event.")
    event_ticket_id = fields.Many2one('event.event.ticket', string='Event Ticket', help="Choose "
        "an event ticket and it will automatically create a registration for this event ticket.")
    event_ok = fields.Boolean(related='product_id.event_ok', readonly=True)

    def _update_registrations(self, confirm=True, cancel_to_draft=False, registration_data=None):
        """ Create or update registrations linked to a sales order line. A sale
        order line has a product_uom_qty attribute that will be the number of
        registrations linked to this line. This method update existing registrations
        and create new one for missing one. """
        Registration = self.env['event.registration'].sudo()
        registrations = Registration.search([('sale_order_line_id', 'in', self.ids)])
        for so_line in self.filtered('event_id'):
            existing_registrations = registrations.filtered(lambda self: self.sale_order_line_id.id == so_line.id)
            if confirm:
                existing_registrations.filtered(lambda self: self.state not in ['open', 'cancel']).confirm_registration()
            if cancel_to_draft:
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

    @api.onchange('product_id')
    def _onchange_product_id(self):
        # We reset the event when keeping it would lead to an inconstitent state.
        # We need to do it this way because the only relation between the product and the event is through the corresponding tickets.
        if self.event_id and (not self.product_id or self.product_id.id not in self.event_id.mapped('event_ticket_ids.product_id.id')):
            self.event_id = None

    @api.onchange('event_id')
    def _onchange_event_id(self):
        # We reset the ticket when keeping it would lead to an inconstitent state.
        if self.event_ticket_id and (not self.event_id or self.event_id != self.event_ticket_id.event_id):
            self.event_ticket_id = None

    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        if not self.event_ticket_id:
            super(SaleOrderLine, self).product_uom_change()

    @api.onchange('event_ticket_id')
    def _onchange_event_ticket_id(self):
        # we call this to force update the default name
        self.product_id_change()

    def get_sale_order_line_multiline_description_sale(self, product):
        """ We override this method because we decided that:
                The default description of a sales order line containing a ticket must be different than the default description when no ticket is present.
                So in that case we use the description computed from the ticket, instead of the description computed from the product.
                We need this override to be defined here in sales order line (and not in product) because here is the only place where the event_ticket_id is referenced.
        """
        if self.event_ticket_id:
            ticket = self.event_ticket_id.with_context(
                lang=self.order_id.partner_id.lang,
            )

            return ticket.get_ticket_multiline_description_sale() + self._get_sale_order_line_multiline_description_variants()
        else:
            return super(SaleOrderLine, self).get_sale_order_line_multiline_description_sale(product)

    def _get_display_price(self, product):
        if self.event_ticket_id and self.event_id:
            company = self.event_id.company_id or self.env.company
            currency = company.currency_id
            return currency._convert(
                self.event_ticket_id.price, self.order_id.currency_id,
                self.order_id.company_id or self.env.company.id,
                self.order_id.date_order or fields.Date.today())
        else:
            return super()._get_display_price(product)
