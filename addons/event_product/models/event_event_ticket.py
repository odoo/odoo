# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, fields


class EventEventTicket(models.Model):
    _inherit = 'event.event.ticket'
    _order = "event_id, sequence, price, name, id"

    total_price_reduce_taxinc = fields.Float(
        string='Total Price Reduce Tax inc', compute='_compute_total_price_reduce_taxinc',
        digits='Product Price', compute_sudo=True)
    total_price_incl = fields.Float(
        string='Total Price include', compute='_compute_total_price_incl',
        digits='Product Price', compute_sudo=True)

    @api.depends('product_id.active')
    def _compute_sale_available(self):
        inactive_product_tickets = self.filtered(lambda ticket: not ticket.product_id.active)
        for ticket in inactive_product_tickets:
            ticket.sale_available = False
        super(EventEventTicket, self - inactive_product_tickets)._compute_sale_available()

    def _compute_total_price_reduce_taxinc(self):
        for ticket in self:
            ticket_tax_ids = ticket.product_id.taxes_id.filtered(lambda r: r.company_id == ticket.event_id.company_id)
            ticket_prices = ticket_tax_ids.compute_all(ticket.price_reduce, ticket.company_id.currency_id, 1.0, product=ticket.product_id)
            ticket_price_reduce_taxinc = ticket_prices['total_included']
            linked_products_price_taxinc = 0
            for product in ticket.additional_product_ids:
                tax_ids = product.taxes_id.filtered(lambda r: r.company_id == ticket.event_id.company_id)
                contextual_discount = product._get_contextual_discount()
                product_price_reduce = (1.0 - contextual_discount) * product.lst_price
                prices = tax_ids.compute_all(product_price_reduce, ticket.company_id.currency_id or product.currency_id, 1.0, product=product)
                linked_products_price_taxinc += prices['total_included']
            ticket.total_price_reduce_taxinc = ticket_price_reduce_taxinc + linked_products_price_taxinc

    @api.depends('additional_product_ids', 'price', 'product_id', 'product_id.taxes_id')
    def _compute_total_price_incl(self):
        for ticket in self:
            ticket_price_incl = 0
            if ticket.product_id and ticket.price:
                ticket_tax_ids = ticket.product_id.taxes_id.filtered(lambda r: r.company_id == ticket.event_id.company_id)
                ticket_prices = ticket_tax_ids.compute_all(ticket.price, ticket.company_id.currency_id, 1.0, product=ticket.product_id)
                ticket_price_incl = ticket_prices['total_included']
            linked_products_price_taxinc = 0
            for product in ticket.additional_product_ids:
                tax_ids = product.taxes_id.filtered(lambda r: r.company_id == ticket.event_id.company_id)
                prices = tax_ids.compute_all(product.lst_price, ticket.company_id.currency_id or product.currency_id, 1.0, product=product)
                linked_products_price_taxinc += prices['total_included']
            ticket.total_price_incl = ticket_price_incl + linked_products_price_taxinc
