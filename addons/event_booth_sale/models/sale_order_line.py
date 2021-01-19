# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    event_booth_id = fields.Many2one('event.booth', string='Event Booth')
    event_booth_slot_ids = fields.Many2many('event.booth.slot', string='Event Booth Slots')
    is_event_booth = fields.Boolean(related='product_id.is_event_booth', readonly=True)

    @api.constrains('event_booth_slot_ids')
    def _check_if_contiguous_slots(self):
        for so_line in self:
            if so_line.event_booth_slot_ids:
                from_date = min(so_line.event_booth_slot_ids.mapped('booking_to'))
                to_date = max(so_line.event_booth_slot_ids.mapped('booking_from'))
                slot = self.env['event.booth.slot'].search([
                    ('event_booth_id', '=', so_line.event_booth_id.id),
                    ('id', 'not in', so_line.event_booth_slot_ids.ids),
                    ('booking_from', '>=', from_date),
                    ('booking_to', '<=', to_date)
                ])
                if slot.exists():
                    raise ValidationError(_('You must select contiguous Booth Slots.'))

    def _update_booth_slot(self, set_paid=False):
        RegistrationSudo = self.env['event.booth.registration'].sudo()
        registrations = RegistrationSudo.search([('sale_order_line_id', 'in', self.ids)])
        registrations_to_create = []
        for so_line in self.filtered('is_event_booth'):
            line_registration = registrations.filtered(lambda reg: reg.sale_order_line_id.id == so_line.id)
            if line_registration:
                if set_paid:
                    line_registration.filtered(lambda reg: reg.state == 'draft').action_set_paid()
            else:
                values = {
                    'sale_order_id': so_line.order_id.id,
                    'sale_order_line_id': so_line.id,
                    'partner_id': so_line.order_id.partner_id.id,
                    'booth_slot_ids': so_line.event_booth_slot_ids,
                }
                registrations_to_create.append(values)

        if registrations_to_create:
            RegistrationSudo.create(registrations_to_create)
        return True

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.event_id and (not self.product_id or self.product_id.id not in self.event_id.mapped('event_booth_ids.product_id.id')):
            self.event_id = None

    @api.onchange('event_id')
    def _onchange_event_id(self):
        if self.event_booth_id and (not self.event_id or self.event_id != self.event_booth_id.event_id):
            self.event_booth_id = None
        if self.event_booth_slot_ids and not self.event_id:
            self.event_booth_slot_ids = None

    @api.onchange('event_booth_id')
    def _onchange_event_booth_id(self):
        self.product_id_change()

    def get_sale_order_line_multiline_description_sale(self, product):
        if self.event_booth_id:
            # TODO: See how the translation works here (as it is done in event_sale)
            if self.event_booth_slot_ids:
                return self.event_booth_slot_ids._get_booth_multiline_description()
        else:
            return super(SaleOrderLine, self).get_sale_order_line_multiline_description_sale(product)

    def _get_display_price(self, product):
        if self.event_booth_id and self.event_id:
            company = self.event_id.company_id or self.env.company
            currency = company.currency_id
            extra_price = self.event_booth_id.extra_price * (len(self.event_booth_slot_ids) - 1)
            total_price = self.event_booth_id.price + extra_price
            return currency._convert(
                total_price, self.order_id.currency_id,
                self.order_id.company_id or self.env.company.id,
                self.order_id.date_order or fields.Date.today())
        else:
            return super(SaleOrderLine, self)._get_display_price(product)

    # TODO: Look if this method is used when displaying on the portal cart
    # @api.depends('product_id.display_name')
    # def _compute_name_short(self):
    #     super(SaleOrderLine, self)._compute_name_short()
    #     for record in self:
    #         if record.event_booth_slot_ids:
    #             record.name_short = record.event_booth_slot_ids._get_booth_multiline_description()
