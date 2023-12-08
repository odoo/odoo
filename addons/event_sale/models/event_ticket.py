# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class EventTicket(models.Model):
    _inherit = 'event.event.ticket'
    _order = "event_id, sequence, price, name, id"

    # product
    price_reduce_taxinc = fields.Float(
        string='Price Reduce Tax inc', compute='_compute_price_reduce_taxinc',
        compute_sudo=True)
    price_incl = fields.Float(
        string='Price include', compute='_compute_price_incl',
        digits='Product Price', readonly=False)

    def _compute_price_reduce_taxinc(self):
        for event in self:
            # sudo necessary here since the field is most probably accessed through the website
            tax_ids = event.product_id.taxes_id.filtered(lambda r: r.company_id == event.event_id.company_id)
            taxes = tax_ids.compute_all(event.price_reduce, event.event_id.company_id.currency_id, 1.0, product=event.product_id)
            event.price_reduce_taxinc = taxes['total_included']

    @api.depends('product_id', 'product_id.taxes_id', 'price')
    def _compute_price_incl(self):
        for event in self:
            if event.product_id and event.price:
                tax_ids = event.product_id.taxes_id.filtered(lambda r: r.company_id == event.event_id.company_id)
                taxes = tax_ids.compute_all(event.price, event.currency_id, 1.0, product=event.product_id)
                event.price_incl = taxes['total_included']
            else:
                event.price_incl = 0

    def _get_ticket_multiline_description(self):
        """ If people set a description on their product it has more priority
        than the ticket name itself for the SO description. """
        self.ensure_one()
        if self.product_id.description_sale:
            return '%s\n%s' % (self.product_id.description_sale, self.event_id.display_name)
        return super(EventTicket, self)._get_ticket_multiline_description()
