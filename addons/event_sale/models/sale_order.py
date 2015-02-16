# -*- coding: utf-8 -*-

from openerp import api, fields, models

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def action_button_confirm(self):
        self.ensure_one()
        res = super(SaleOrder, self).action_button_confirm()
        if self.mapped('order_line.event_id'):
            return self.env['ir.actions.act_window'].with_context(default_sale_order_id=self.id).for_xml_id('event_sale', 'action_sale_order_event_registration')


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    event_id = fields.Many2one(
        'event.event', string='Event',
        help="Choose an event and it will automatically create a registration for this event.")
    event_ticket_id = fields.Many2one(
        'event.event.ticket', string='Event Ticket',
        help="Choose an event ticket and it will automatically create a registration for this event ticket.")
    # those 2 fields are used for dynamic domains and filled by onchange
    # TDE: really necessary ? ...
    event_type_id = fields.Many2one(related='product_id.event_type_id', string="Event Type")
    event_ok = fields.Boolean(related='product_id.event_ok')

    @api.multi
    def product_id_change(self, pricelist, product, qty=0, uom=False,
                          qty_uos=0, uos=False, name='', partner_id=False, lang=False,
                          update_tax=True, date_order=False, packaging=False,
                          fiscal_position=False, flag=False):
        """ check product if event type """
        res = super(SaleOrderLine, self).product_id_change(pricelist, product, qty=qty, uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id, lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag)
        if product:
            product_res = self.env['product.product'].browse(product)
            if product_res.event_ok:
                res['value'].update(event_type_id=product_res.event_type_id.id,
                                    event_ok=product_res.event_ok)
            else:
                res['value'].update(event_type_id=False,
                                    event_ok=False)
        return res

    @api.onchange('event_ticket_id')
    def onchange_event_ticket_id(self):
        self.price_unit = self.event_ticket_id.price

    @api.multi
    def _update_registrations(self, confirm=True, registration_data=None):
        """ Create or update registrations linked to a sale order line. A sale
        order line has a product_uom_qty attribute that will be the number of
        registrations linked to this line. This method update existing registrations
        and create new one for missing one. """
        Registration = self.env['event.registration']
        registrations = Registration.search([('sale_order_line_id', 'in', self.ids)])
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

    @api.multi
    def button_confirm(self):
        """ Override confirmation of the sale order line in order to create
        or update the possible event registrations linked to the sale. """
        '''
        create registration with sales order
        '''
        res = super(SaleOrderLine, self).button_confirm()
        self._update_registrations(confirm=True)
        return res

    @api.model
    def _prepare_order_line_invoice_line(self, line, account_id=False):
        res = super(SaleOrderLine, self)._prepare_order_line_invoice_line(line, account_id=account_id)
        if line.event_id:
            res['name'] = '%s: %s' % (res.get('name', ''), line.event_id.name)
        return res
