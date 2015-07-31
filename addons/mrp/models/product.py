# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.multi
    def _bom_orders_count(self):
        for product_tmpl_id in self:
            product_tmpl_id.bom_count = self.env['mrp.bom'].search_count([('product_tmpl_id', '=', product_tmpl_id.id)])

    @api.multi
    def _bom_orders_count_mo(self):
        for product_tmpl_id in self:
            product_tmpl_id.mo_count = sum([product.mo_count for product in product_tmpl_id.product_variant_ids])

    bom_ids = fields.One2many('mrp.bom', 'product_tmpl_id', string='Bill of Materials')
    bom_count = fields.Integer(compute='_bom_orders_count', string='# Bill of Material')
    mo_count = fields.Integer(compute='_bom_orders_count_mo', string='# Manufacturing Orders')
    produce_delay = fields.Float(string='Manufacturing Lead Time', default=1.0, help="Average delay in days to produce this product. In the case of multi-level BOM, the manufacturing lead times of the components will be added.")

    @api.multi
    def action_view_mos(self):
        products = self._get_products()
        result = self._get_act_window_dict('mrp.act_product_mrp_production')
        if len(self) == 1 and len(products) == 1:
            result['context'] = "{'default_product_id': " + str(products[0]) + ", 'search_default_product_id': " + str(products[0]) + "}"
        else:
            result['domain'] = "[('product_id','in',[" + ','.join(map(str, products)) + "])]"
            result['context'] = "{}"
        return result


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.multi
    def _bom_orders_count(self):
        for product_id in self:
            product_id.mo_count = self.env['mrp.production'].search_count([('product_id', '=', product_id.id)])

    mo_count = fields.Integer(compute='_bom_orders_count', string='# Manufacturing Orders')

    @api.multi
    def action_view_bom(self):
        products = set()
        for product in self:
            products.add(product.product_tmpl_id.id)
        result = self.env['product.template']._get_act_window_dict('mrp.product_open_bom')
        # bom specific to this variant or global to template
        domain = ['|', ('product_id', 'in', [self.id]), '&', ('product_id', '=', False), ('product_tmpl_id', 'in', list(products)), ]
        result['context'] = "{}"
        result['domain'] = str(domain)
        return result
