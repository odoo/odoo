# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields, models, api

class WebsiteTrack(models.Model):
    _inherit = 'website.track'

    product_id = fields.Many2one('product.product', ondelete='cascade', readonly=True, index='btree_not_null')


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    visitor_product_count = fields.Integer('Product Views', compute="_compute_product_statistics", help="Total number of views on products")
    product_ids = fields.Many2many('product.product', string="Visited Products", compute="_compute_product_statistics")
    product_count = fields.Integer('Products Views', compute="_compute_product_statistics", help="Total number of product viewed")

    @api.depends('website_track_ids')
    def _compute_product_statistics(self):
        results = self.env['website.track']._read_group(
            [('visitor_id', 'in', self.ids), ('product_id', '!=', False),
             '|', ('product_id.company_id', 'in', self.env.companies.ids), ('product_id.company_id', '=', False)],
            ['visitor_id', 'product_id'], ['visitor_id', 'product_id'],
            lazy=False)
        mapped_data = {}
        for result in results:
            visitor_info = mapped_data.get(result['visitor_id'][0], {'product_count': 0, 'product_ids': set()})
            visitor_info['product_count'] += result['__count']
            visitor_info['product_ids'].add(result['product_id'][0])
            mapped_data[result['visitor_id'][0]] = visitor_info

        for visitor in self:
            visitor_info = mapped_data.get(visitor.id, {'product_ids': [], 'product_count': 0})

            visitor.product_ids = [(6, 0, visitor_info['product_ids'])]
            visitor.visitor_product_count = visitor_info['product_count']
            visitor.product_count = len(visitor_info['product_ids'])

    def _add_viewed_product(self, product_id):
        """ add a website_track with a page marked as viewed"""
        self.ensure_one()
        if product_id and self.env['product.product'].browse(product_id)._is_variant_possible():
            domain = [('product_id', '=', product_id)]
            website_track_values = {'product_id': product_id}
            self._add_tracking(domain, website_track_values)
