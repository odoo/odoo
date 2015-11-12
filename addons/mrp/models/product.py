# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.multi
    def _bom_orders_count(self):
        for product_tmpl in self:
            product_tmpl.bom_count = self.env['mrp.bom'].search_count([('product_tmpl_id', '=', product_tmpl.id)])

    @api.multi
    def _bom_orders_count_mo(self):
        for product_tmpl in self:
            product_tmpl.mo_count = sum([p.mo_count for p in product_tmpl.product_variant_ids])

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
        for product in self:
            product.mo_count = self.env['mrp.production'].search_count([('product_id', '=', product.id)])

    mo_count = fields.Integer(compute='_bom_orders_count', string='# Manufacturing Orders')

    @api.multi
    def action_view_bom(self):
        result = self.env['product.template']._get_act_window_dict('mrp.product_open_bom')
        templates = self.product_tmpl_id
        # bom specific to this variant or global to template
        domain = ['|', ('product_id', 'in', [self.id]), '&', ('product_id', '=', False), ('product_tmpl_id', 'in', templates.ids)]
        result['context'] = "{}"
        result['domain'] = str(domain)
        return result


#in procurement module
class ProductCategory(models.Model):
    _inherit = "product.category"

    procurement_time_frame = fields.Integer("Procurement Grouping Period (days)", help="Time Frame in which the procurements will be grouped together when triggering a new document (PO, MO)")

