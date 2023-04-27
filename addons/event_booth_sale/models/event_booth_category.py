# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class EventBoothCategory(models.Model):
    _inherit = 'event.booth.category'

    def _default_product_id(self):
        return self.env.ref('event_booth_sale.product_product_event_booth', raise_if_not_found=False)

    product_id = fields.Many2one(
        'product.product', string='Product', required=True,
        domain=[('detailed_type', '=', 'event_booth')], default=_default_product_id,
        groups="event.group_event_registration_desk")
    price = fields.Float(
        string='Price', compute='_compute_price', digits='Product Price', readonly=False,
        store=True, groups="event.group_event_registration_desk")
    price_incl = fields.Float(
        string='Price incl', compute='_compute_price_incl', digits='Product Price', readonly=False,
        groups="event.group_event_registration_desk")
    currency_id = fields.Many2one(related='product_id.currency_id', groups="event.group_event_registration_desk")
    price_reduce = fields.Float(
        string='Price Reduce', compute='_compute_price_reduce',
        compute_sudo=True, digits='Product Price', groups="event.group_event_registration_desk")
    price_reduce_taxinc = fields.Float(
        string='Price Reduce Tax inc', compute='_compute_price_reduce_taxinc',
        compute_sudo=True
    )
    image_1920 = fields.Image(compute='_compute_image_1920', readonly=False, store=True)

    @api.depends('product_id')
    def _compute_image_1920(self):
        for category in self:
            category.image_1920 = category.image_1920 if category.image_1920 else category.product_id.image_1920

    @api.depends('product_id')
    def _compute_price(self):
        """ By default price comes from category but can be changed by event
        people as product may be shared across various categories. """
        for category in self:
            if category.product_id and category.product_id.list_price:
                category.price = category.product_id.list_price + category.product_id.price_extra

    @api.depends('product_id', 'product_id.taxes_id', 'price')
    def _compute_price_incl(self):
        for category in self:
            if category.product_id and category.price:
                category.price_incl = category._tax_compute(category.price, category.currency_id)
            else:
                category.price_incl = 0

    @api.depends_context('uom', 'pricelist', 'quantity')
    @api.depends('product_id', 'price')
    def _compute_price_reduce(self):
        for category in self:
            currency = category.product_id._get_contextual_pricelist().currency_id or self.env.company.currency_id
            category.price_reduce = currency._convert(
                category.product_id.with_context({
                    **self._context,
                    'record_being_sold': category.id,
                })._get_contextual_price(),
                category.currency_id, category.product_id.company_id or self.env.company, fields.Date.today(),
                round=False)

    @api.depends_context('pricelist', 'quantity')
    @api.depends('product_id', 'price_reduce')
    def _compute_price_reduce_taxinc(self):
        for category in self:
            category.price_reduce_taxinc = category._tax_compute(category.price_reduce, category.currency_id)

    def _init_column(self, column_name):
        """ Initialize product_id for existing columns when installing sale
        bridge, to ensure required attribute is fulfilled. """
        if column_name != "product_id":
            return super(EventBoothCategory, self)._init_column(column_name)

        # fetch void columns
        self.env.cr.execute("SELECT id FROM %s WHERE product_id IS NULL" % self._table)
        booth_category_ids = self.env.cr.fetchall()
        if not booth_category_ids:
            return

        # update existing columns
        _logger.debug("Table '%s': setting default value of new column %s to unique values for each row",
                      self._table, column_name)
        default_booth_product = self._default_product_id()
        if default_booth_product:
            product_id = default_booth_product.id
        else:
            product_id = self.env['product.product'].create({
                'name': 'Generic Event Booth Product',
                'categ_id': self.env.ref('event_sale.product_category_events').id,
                'list_price': 100,
                'standard_price': 0,
                'detailed_type': 'event_booth',
                'invoice_policy': 'order',
            }).id
            self.env['ir.model.data'].create({
                'name': 'product_product_event_booth',
                'module': 'event_booth_sale',
                'model': 'product.product',
                'res_id': product_id,
            })
        self.env.cr._obj.execute(
            f'UPDATE {self._table} SET product_id = %s WHERE id IN %s;',
            (product_id, tuple(booth_category_ids))
        )

    def _tax_compute(self, price, currency):
        """ Helper function to compute the price tax included for the booth (self). """
        self.ensure_one()
        tax_ids = self.product_id.taxes_id
        taxes = tax_ids.compute_all(price, currency, 1.0, product=self.product_id)
        return taxes['total_included'] or 0
