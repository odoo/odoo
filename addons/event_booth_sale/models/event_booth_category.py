# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class EventTypeBoothCategory(models.Model):
    _inherit = 'event.type.booth.category'

    def _default_product_id(self):
        return self.env.ref('event_booth_sale.product_product_event_booth', raise_if_not_found=False)

    product_id = fields.Many2one('product.product', string='Product', required=True,
                                 domain=[('is_event_booth', '=', True)], default=_default_product_id)
    price = fields.Float(string='Price', compute='_compute_price', readonly=False, store=True)
    extra_price = fields.Float(string='Extra Slot Price', digits='Product Price')
    image_1920 = fields.Image(compute='_compute_image_1920', readonly=False, store=True)

    @api.model
    def _get_event_booth_category_fields_whitelist(self):
        return super(EventTypeBoothCategory, self)._get_event_booth_category_fields_whitelist() + ['product_id', 'price', 'extra_price']

    @api.depends('product_id')
    def _compute_image_1920(self):
        for category in self:
            if not category.image_1920:
                category.image_1920 = category.product_id.image_1920

    @api.depends('product_id')
    def _compute_price(self):
        for category in self:
            if category.product_id and category.product_id.lst_price:
                category.price = category.product_id.lst_price

    def _init_column(self, column_name):
        if column_name != 'product_id':
            return super(EventTypeBoothCategory, self)._init_column(column_name)

        self.env.cr.execute("SELECT id FROM %s WHERE product_id IS NULL" % self._table)
        booth_category_ids = self.env.cr.fetchall()
        if not booth_category_ids:
            return

        _logger.debug("Table '%s': setting default value of new column %s to unique values for each row",
                      self._table, column_name)
        default_event_booth_product = self.env.ref('event_booth_sale.product_product_event_booth', raise_if_not_found=False)
        if default_event_booth_product:
            product_id = default_event_booth_product.id
        else:
            product_id = self.env['product.product'].create({
                'name': 'Generic Event Booth',
                'list_price': 0,
                'standard_price': 0,
                'type': 'service',
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
