# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    attendee_count = fields.Integer('Attendee Count', compute='_compute_attendee_count')

    def write(self, vals):
        """ Synchronize partner from SO to registrations. This is done notably
        in website_sale controller shop/address that updates customer, but not
        only. """
        result = super(SaleOrder, self).write(vals)
        if vals.get('partner_id'):
            registrations_toupdate = self.sudo().env['event.registration'].search([('sale_order_id', 'in', self.ids)])
            registrations_toupdate.write({'partner_id': vals['partner_id']})
        return result

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for so in self:
            if not any(line.product_type == 'event' for line in so.order_line):
                continue
            # confirm registration if it was free (otherwise it will be confirmed once invoice fully paid)
            so.order_line._update_registrations(confirm=so.amount_total == 0, cancel_to_draft=False)
            if len(self) == 1:
                return self.env['ir.actions.act_window'].with_context(
                    default_sale_order_id=so.id
                )._for_xml_id('event_sale.action_sale_order_event_registration')
        return res

    def _action_cancel(self):
        self.order_line._cancel_associated_registrations()
        return super()._action_cancel()

    def action_view_attendee_list(self):
        action = self.env["ir.actions.actions"]._for_xml_id("event.event_registration_action_tree")
        action['domain'] = [('sale_order_id', 'in', self.ids)]
        return action

    def _compute_attendee_count(self):
        sale_orders_data = self.env['event.registration']._read_group(
            [('sale_order_id', 'in', self.ids),
             ('state', '!=', 'cancel')],
            ['sale_order_id'], ['sale_order_id']
        )
        attendee_count_data = {
            sale_order_data['sale_order_id'][0]:
            sale_order_data['sale_order_id_count']
            for sale_order_data in sale_orders_data
        }
        for sale_order in self:
            sale_order.attendee_count = attendee_count_data.get(sale_order.id, 0)

    def unlink(self):
        self.order_line._unlink_associated_registrations()
        return super(SaleOrder, self).unlink()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    event_id = fields.Many2one(
        'event.event', string='Event',
        compute="_compute_event_id", store=True, readonly=False, precompute=True,
        help="Choose an event and it will automatically create a registration for this event.")
    event_ticket_id = fields.Many2one(
        'event.event.ticket', string='Event Ticket',
        compute="_compute_event_ticket_id", store=True, readonly=False, precompute=True,
        help="Choose an event ticket and it will automatically create a registration for this event ticket.")
    # TODO in master: remove this field, unused anymore
    event_ok = fields.Boolean(compute='_compute_event_ok')

    @api.depends('product_id.detailed_type')
    def _compute_event_ok(self):
        for record in self:
            record.event_ok = record.product_id.detailed_type == 'event'

    @api.depends('state', 'event_id')
    def _compute_product_uom_readonly(self):
        event_lines = self.filtered(lambda line: line.event_id)
        event_lines.update({'product_uom_readonly': True})
        super(SaleOrderLine, self - event_lines)._compute_product_uom_readonly()

    def _update_registrations(self, confirm=True, cancel_to_draft=False, registration_data=None, mark_as_paid=False):
        """ Create or update registrations linked to a sales order line. A sale
        order line has a product_uom_qty attribute that will be the number of
        registrations linked to this line. This method update existing registrations
        and create new one for missing one. """
        RegistrationSudo = self.env['event.registration'].sudo()
        registrations = RegistrationSudo.search([('sale_order_line_id', 'in', self.ids)])
        registrations_vals = []
        for so_line in self:
            if not so_line.product_type == 'event':
                continue
            existing_registrations = registrations.filtered(lambda self: self.sale_order_line_id.id == so_line.id)
            if confirm:
                existing_registrations.filtered(lambda self: self.state not in ['open', 'cancel']).action_confirm()
            if mark_as_paid:
                existing_registrations.filtered(lambda self: not self.is_paid)._action_set_paid()
            if cancel_to_draft:
                existing_registrations.filtered(lambda self: self.state == 'cancel').action_set_draft()

            for count in range(int(so_line.product_uom_qty) - len(existing_registrations)):
                values = {
                    'sale_order_line_id': so_line.id,
                    'sale_order_id': so_line.order_id.id
                }
                # TDE CHECK: auto confirmation
                if registration_data:
                    values.update(registration_data.pop())
                registrations_vals.append(values)

        if registrations_vals:
            RegistrationSudo.create(registrations_vals)
        return True

    @api.depends('product_id')
    def _compute_event_id(self):
        event_lines = self.filtered(lambda line: line.product_id and line.product_id.detailed_type == 'event')
        (self - event_lines).event_id = False
        for line in event_lines:
            if line.product_id not in line.event_id.event_ticket_ids.product_id:
                line.event_id = False

    @api.depends('event_id')
    def _compute_event_ticket_id(self):
        event_lines = self.filtered('event_id')
        (self - event_lines).event_ticket_id = False
        for line in event_lines:
            if line.event_id != line.event_ticket_id.event_id:
                line.event_ticket_id = False

    @api.depends('event_ticket_id')
    def _compute_price_unit(self):
        super()._compute_price_unit()

    @api.depends('event_ticket_id')
    def _compute_name(self):
        """Override to add the compute dependency.

        The custom name logic can be found below in _get_sale_order_line_multiline_description_sale.
        """
        super()._compute_name()

    def unlink(self):
        self._unlink_associated_registrations()
        return super(SaleOrderLine, self).unlink()

    def _cancel_associated_registrations(self):
        self.env['event.registration'].search([('sale_order_line_id', 'in', self.ids)]).action_cancel()

    def _unlink_associated_registrations(self):
        self.env['event.registration'].search([('sale_order_line_id', 'in', self.ids)]).unlink()

    def _get_sale_order_line_multiline_description_sale(self):
        """ We override this method because we decided that:
                The default description of a sales order line containing a ticket must be different than the default description when no ticket is present.
                So in that case we use the description computed from the ticket, instead of the description computed from the product.
                We need this override to be defined here in sales order line (and not in product) because here is the only place where the event_ticket_id is referenced.
        """
        if self.event_ticket_id:
            return self.event_ticket_id._get_ticket_multiline_description() + self._get_sale_order_line_multiline_description_variants()
        else:
            return super()._get_sale_order_line_multiline_description_sale()

    def _get_display_price(self):
        if self.event_ticket_id and self.event_id:
            event_ticket = self.event_ticket_id.with_context(
                pricelist=self.order_id.pricelist_id.id,
                uom=self.product_uom.id
            )
            company = event_ticket.company_id or self.env.company
            currency = company.currency_id
            pricelist = self.order_id.pricelist_id
            if pricelist.discount_policy == "with_discount":
                price = event_ticket.price_reduce
            else:
                price = event_ticket.price
            return currency._convert(
                price, self.order_id.currency_id,
                self.order_id.company_id or self.env.company.id,
                self.order_id.date_order or fields.Date.today())
        return super()._get_display_price()
