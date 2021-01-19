# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    event_booth_ids = fields.One2many('event.booth', 'sale_order_line_id', string='Event Booths')
    is_event_booth = fields.Boolean(related='product_id.is_event_booth', readonly=True)

    @api.depends('event_booth_ids')
    def _compute_name_short(self):
        wbooth = self.filtered(lambda line: line.event_booth_ids)
        for record in wbooth:
            record.name_short = record.event_booth_ids._get_booth_multiline_description()
        super(SaleOrderLine, self - wbooth)._compute_name_short()

    @api.onchange('product_id')
    def _onchange_booth_product_id(self):
        if self.event_id and (not self.product_id or self.product_id.id not in self.event_id.mapped('event_booth_ids.product_id.id')):
            self.event_id = None

    @api.onchange('event_id')
    def _onchange_booth_event_id(self):
        if self.event_booth_ids and (not self.event_id or self.event_id != self.event_booth_ids.event_id):
            self.event_booth_ids = None

    @api.onchange('event_booth_ids')
    def _onchange_event_booth_ids(self):
        self.product_id_change()

    def _update_event_booths(self, set_paid=False):
        for so_line in self.filtered('is_event_booth'):
            if set_paid:
                so_line.event_booth_ids.write({'is_paid': True})
            else:
                unavailable = so_line.event_booth_ids.filtered(lambda booth: not booth.is_available)
                if unavailable:
                    raise ValidationError(
                        _('The following booths are unavailable, please remove them to continue : %(booth_names)s',
                          booth_names=''.join('\n\t- %s' % booth.display_name for booth in unavailable)
                         ))
                booth_vals = {
                    'partner_id': so_line.order_id.partner_id.id,
                    'sale_order_id': so_line.order_id.id,
                }
                so_line.event_booth_ids.action_confirm(booth_vals)
        return True

    def get_sale_order_line_multiline_description_sale(self, product):
        if self.event_booth_ids:
            # TODO: See how the translation works here (as it is done in event_sale)
            return self.event_booth_ids._get_booth_multiline_description()
        else:
            return super(SaleOrderLine, self).get_sale_order_line_multiline_description_sale(product)

    def _get_display_price(self, product):
        if self.event_booth_ids and self.event_id:
            company = self.event_id.company_id or self.env.company
            currency = company.currency_id
            total_price = sum([booth.price for booth in self.event_booth_ids])
            return currency._convert(
                total_price, self.order_id.currency_id,
                self.order_id.company_id or self.env.company.id,
                self.order_id.date_order or fields.Date.today())
        else:
            return super(SaleOrderLine, self)._get_display_price(product)
