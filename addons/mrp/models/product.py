# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.multi
    def _bom_orders_count(self):
        read_group_res = self.env['mrp.bom'].read_group([('product_tmpl_id', 'in', self.ids)], ['product_tmpl_id'], ['product_tmpl_id'])
        mapped_data = dict([(data['product_tmpl_id'][0], data['product_tmpl_id_count']) for data in read_group_res])
        for product in self:
            product.mo_count = mapped_data.get(product.id, 0)

    @api.one
    def _bom_orders_count_mo(self):
        self.mo_count = sum(self.mapped('product_variant_ids').mapped('mo_count'))

    bom_ids = fields.One2many('mrp.bom', 'product_tmpl_id','Bill of Materials')
    bom_count = fields.Integer(compute='_bom_orders_count', string='# Bill of Material')
    mo_count = fields.Integer(compute='_bom_orders_count_mo', string='# Manufacturing Orders')
    produce_delay = fields.Float(
        'Manufacturing Lead Time', default=0.0,
        help="Average delay in days to produce this product. In the case of multi-level BOM, the manufacturing lead times of the components will be added.")

    @api.multi
    def action_view_mos(self):
        # TDE FIXME: get_products does not exists
        product_ids = self.mapped('product_variant_ids').ids
        action = self.env.ref('mrp.act_product_mrp_production').read()[0]
        if len(self) == 1 and len(product_ids) == 1:
            action['context'] = {'default_product_id': product_ids[0], 'search_default_product_id': product_ids[0]}
        else:
            action['domain'] = [('product_id', 'in', product_ids)]
            action['context'] = {}
        return action


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.multi
    def _bom_orders_count(self):
        read_group_res = self.env['mrp.production'].read_group([('product_id', 'in', self.ids)], ['product_id'], ['product_id'])
        mapped_data = dict([(data['product_id'][0], data['product_id_count']) for data in read_group_res])
        for product in self:
            product.mo_count = mapped_data.get(product.id, 0)

    mo_count = fields.Integer(compute='_bom_orders_count', string='# Manufacturing Orders')

    @api.multi
    def action_view_bom(self):
        action = self.env.ref('mrp.product_open_bom').read()[0]
        template_ids = self.mapped('producdt_tmpl_id').ids
        # bom specific to this variant or global to template
        action['context'] = {
            'default_product_tmpl_id': template_ids[0],
            'default_product_id': self.ids[0],
        }
        action['domain'] = ['|', ('product_id', 'in', [self.ids]), '&', ('product_id', '=', False), ('product_tmpl_id', 'in', template_ids)]
        return action


# in procurement module  # TDE CLEANME ? what ?
class ProductCategory(models.Model):
    _inherit = "product.category"

    procurement_time_frame = fields.Integer("Procurement Grouping Period (days)", help="Time Frame in which the procurements will be grouped together when triggering a new document (PO, MO)")

