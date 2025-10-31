# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models
from odoo.addons.product.models.product_template import PRICE_CONTEXT_KEYS

_logger = logging.getLogger(__name__)


class EventTypeTicket(models.Model):
    _inherit = 'event.type.ticket'
    _order = "sequence, price, name, id"

    def _default_product_id(self):
        return self.env.ref('event_product.product_product_event', raise_if_not_found=False)

    description = fields.Text(compute='_compute_description', readonly=False, store=True)
    # product
    product_id = fields.Many2one(
        'product.product', string='Product', required=True, index=True,
        domain=[("service_tracking", "=", "event")], default=_default_product_id)
    currency_id = fields.Many2one(related="product_id.currency_id", string="Currency")
    price = fields.Float(
        string='Ticket Price', compute='_compute_price',
        digits='Product Price', readonly=False, store=True)
    price_reduce = fields.Float(
        string="Price Reduce", compute="_compute_price_reduce",
        compute_sudo=True, digits='Product Price')
    additional_product_ids = fields.Many2many('product.product', string='Additional Products',
            domain=[('service_tracking', '!=', 'event')],
            help="Select products to include with each registration. They will also show up separately on Sale Orders.")
    total_price = fields.Float(string='Total Price', compute='_compute_total_price', digits='Product Price',
        help="Price at which this ticket will be sold, which takes into account the Ticket Price and the price of every Additional Product")
    total_price_reduce = fields.Float(string='Total Price Reduce', compute='_compute_price_reduce',
        compute_sudo=True, digits='Product Price')

    @api.depends('product_id')
    def _compute_price(self):
        for ticket in self:
            if ticket.product_id and ticket.product_id.lst_price:
                ticket.price = ticket.product_id.lst_price or 0
            elif not ticket.price:
                ticket.price = 0

    @api.depends('additional_product_ids', 'additional_product_ids.lst_price', 'price')
    def _compute_total_price(self):
        for ticket in self:
            ticket.total_price = ticket.price + sum(ticket.additional_product_ids.mapped('lst_price'))

    @api.depends('product_id')
    def _compute_description(self):
        for ticket in self:
            if ticket.product_id and ticket.product_id.description_sale:
                ticket.description = ticket.product_id.description_sale
            # initialize, i.e for embedded tree views
            if not ticket.description:
                ticket.description = False

    # TODO clean this feature in master
    # Feature broken by design, depending on the hacky `_get_contextual_price` field on products
    # context_dependent, core part of the pricelist mess
    # This field usage should be restricted to the UX, and any use in effective
    # price computation should be replaced by clear calls to the pricelist API
    @api.depends_context(*PRICE_CONTEXT_KEYS)
    @api.depends('additional_product_ids', 'product_id', 'price', 'total_price')
    def _compute_price_reduce(self):
        for ticket in self:
            contextual_discount = ticket.product_id._get_contextual_discount()
            ticket.price_reduce = (1.0 - contextual_discount) * ticket.price
            total_additional_products_price_reduce = 0
            for product in ticket.additional_product_ids:
                contextual_discount = product._get_contextual_discount()
                total_additional_products_price_reduce += (1.0 - contextual_discount) * product.lst_price
            ticket.total_price_reduce = ticket.price_reduce + total_additional_products_price_reduce

    def _init_column(self, column_name):
        if column_name != "product_id":
            return super()._init_column(column_name)

        # fetch void columns
        self.env.cr.execute("SELECT id FROM %s WHERE product_id IS NULL" % self._table)
        ticket_type_ids = self.env.cr.fetchall()
        if not ticket_type_ids:
            return

        # update existing columns
        _logger.debug("Table '%s': setting default value of new column %s to unique values for each row",
                      self._table, column_name)
        default_event_product = self.env.ref('event_product.product_product_event', raise_if_not_found=False)
        if default_event_product:
            product_id = default_event_product.id
        else:
            product_id = self.env['product.product'].create({
                'name': 'Generic Registration Product',
                'list_price': 0,
                'standard_price': 0,
                'type': 'service',
            }).id
            self.env['ir.model.data'].create({
                'name': 'product_product_event',
                'module': 'event_product',
                'model': 'product.product',
                'res_id': product_id,
            })
        self.env.cr._obj.execute(
            f'UPDATE {self._table} SET product_id = %s WHERE id IN %s;',
            (product_id, tuple(ticket_type_ids))
        )

    @api.model
    def _get_event_ticket_fields_whitelist(self):
        """ Add sale specific fields to copy from template to ticket """
        return super()._get_event_ticket_fields_whitelist() + ['product_id', 'price']
