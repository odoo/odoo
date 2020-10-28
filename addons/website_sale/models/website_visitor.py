# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields, models, api
from odoo.http import request

class WebsiteTrack(models.Model):
    _inherit = 'website.track'

    product_id = fields.Many2one('product.product', index=True, ondelete='cascade', readonly=True)


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    visitor_product_count = fields.Integer('Product Views', compute="_compute_product_statistics", help="Total number of views on products")
    product_ids = fields.Many2many('product.product', string="Visited Products", compute="_compute_product_statistics")
    product_count = fields.Integer('Products Views', compute="_compute_product_statistics", help="Total number of product viewed")

    @api.depends('website_track_ids')
    def _compute_product_statistics(self):
        results = self.env['website.track'].read_group(
            [('visitor_id', 'in', self.ids), ('product_id', '!=', False)], ['visitor_id', 'product_id'], ['visitor_id', 'product_id'], lazy=False)
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

    def _handle_website_page_visit(self, website_page, visitor_sudo):
        # avoid duplicate entry in page views, when he/she visit the product details
        if not self._context.get('product_view'):
            super(WebsiteVisitor, self)._handle_website_page_visit(website_page, visitor_sudo)
        else:
            if visitor_sudo.lang_id.id != request.lang.id:
                visitor_sudo.write({'lang_id': request.lang.id})

    def _add_viewed_product(self, product_id):
        """ add a website_track with a page marked as viewed"""
        self.ensure_one()
        if product_id and self.env['product.product'].browse(product_id)._is_variant_possible():
            domain = [('product_id', '=', product_id)]
            website_track_values = {'product_id': product_id, 'visit_datetime': datetime.now()}
            self._add_tracking(domain, website_track_values)
