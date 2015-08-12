# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.multi
    def _bom_orders_count(self):
        bom_data = self.env['mrp.bom'].read_group([('product_tmpl_id', 'in', self.ids)], ['product_tmpl_id'], ['product_tmpl_id'])
        product_data = dict([(m['product_tmpl_id'][0], m['product_tmpl_id_count']) for m in bom_data])
        for product_tmpl_id in self:
            product_tmpl_id.bom_count = product_data.get(product_tmpl_id.id, 0)

    @api.multi
    def _bom_orders_count_mo(self):
        mo_data = self.env['mrp.production'].read_group([('product_id', 'in', self.ids)], ['product_id'], ['product_id'])
        product_data = dict([(m['product_id'][0], m['product_id_count']) for m in mo_data])
        for product_tmpl_id in self:
            product_tmpl_id.mo_count = product_data.get(product_tmpl_id.id, 0)

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
        mo_data = self.env['mrp.production'].read_group([('product_id', 'in', self.ids)], ['product_id'], ['product_id'])
        product_data = dict([(m['product_id'][0], m['product_id_count']) for m in mo_data])
        for product_tmpl_id in self:
            product_tmpl_id.mo_count = product_data.get(product_tmpl_id.id, 0)

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
