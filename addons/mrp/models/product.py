# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from odoo import api, fields, models
from odoo.tools.float_utils import float_round


class ProductTemplate(models.Model):
    _inherit = "product.template"

    bom_line_ids = fields.One2many('mrp.bom.line', 'product_tmpl_id', 'BoM Components')
    bom_ids = fields.One2many('mrp.bom', 'product_tmpl_id', 'Bill of Materials')
    bom_count = fields.Integer('# Bill of Material', compute='_compute_bom_count')
    used_in_bom_count = fields.Integer('# of BoM Where is Used', compute='_compute_used_in_bom_count')
    mrp_product_qty = fields.Float('Manufactured', compute='_compute_mrp_product_qty')
    produce_delay = fields.Float(
        'Manufacturing Lead Time', default=0.0,
        help="Average lead time in days to manufacture this product. In the case of multi-level BOM, the manufacturing lead times of the components will be added.")

    def _compute_bom_count(self):
        for product in self:
            product.bom_count = self.env['mrp.bom'].search_count([('product_tmpl_id', '=', product.id)])

    def _compute_used_in_bom_count(self):
        for template in self:
            template.used_in_bom_count = self.env['mrp.bom'].search_count(
                [('bom_line_ids.product_id', 'in', template.product_variant_ids.ids)])

    def action_used_in_bom(self):
        self.ensure_one()
        action = self.env.ref('mrp.mrp_bom_form_action').read()[0]
        action['domain'] = [('bom_line_ids.product_id', 'in', self.product_variant_ids.ids)]
        return action

    def _compute_mrp_product_qty(self):
        for template in self:
            template.mrp_product_qty = float_round(sum(template.mapped('product_variant_ids').mapped('mrp_product_qty')), precision_rounding=template.uom_id.rounding)

    def action_view_mos(self):
        action = self.env.ref('mrp.mrp_production_report').read()[0]
        action['domain'] = [('state', '=', 'done'), ('product_tmpl_id', 'in', self.ids)]
        action['context'] = {
            'graph_measure': 'product_uom_qty',
            'time_ranges': {'field': 'date_planned_start', 'range': 'last_365_days'}
        }
        return action


class ProductProduct(models.Model):
    _inherit = "product.product"

    variant_bom_ids = fields.One2many('mrp.bom', 'product_id', 'BOM Product Variants')
    bom_line_ids = fields.One2many('mrp.bom.line', 'product_id', 'BoM Components')
    bom_count = fields.Integer('# Bill of Material', compute='_compute_bom_count')
    used_in_bom_count = fields.Integer('# BoM Where Used', compute='_compute_used_in_bom_count')
    mrp_product_qty = fields.Float('Manufactured', compute='_compute_mrp_product_qty')

    def _compute_bom_count(self):
        for product in self:
            product.bom_count = self.env['mrp.bom'].search_count(['|', ('product_id', '=', product.id), '&', ('product_id', '=', False), ('product_tmpl_id', '=', product.product_tmpl_id.id)])

    def _compute_used_in_bom_count(self):
        for product in self:
            product.used_in_bom_count = self.env['mrp.bom'].search_count([('bom_line_ids.product_id', '=', product.id)])

    def action_used_in_bom(self):
        self.ensure_one()
        action = self.env.ref('mrp.mrp_bom_form_action').read()[0]
        action['domain'] = [('bom_line_ids.product_id', '=', self.id)]
        return action

    def _compute_mrp_product_qty(self):
        date_from = fields.Datetime.to_string(fields.datetime.now() - timedelta(days=365))
        #TODO: state = done?
        domain = [('state', '=', 'done'), ('product_id', 'in', self.ids), ('date_planned_start', '>', date_from)]
        read_group_res = self.env['mrp.production'].read_group(domain, ['product_id', 'product_uom_qty'], ['product_id'])
        mapped_data = dict([(data['product_id'][0], data['product_uom_qty']) for data in read_group_res])
        for product in self:
            if not product.id:
                product.mrp_product_qty = 0.0
                continue
            product.mrp_product_qty = float_round(mapped_data.get(product.id, 0), precision_rounding=product.uom_id.rounding)

    def _compute_quantities(self):
        """ When the product is a kit, this override computes the fields :
         - 'virtual_available'
         - 'qty_available'
         - 'incoming_qty'
         - 'outgoing_qty'
         """
        for product in self:
            bom_kit = self.env['mrp.bom']._bom_find(product=product, bom_type='phantom')
            if bom_kit:
                boms, bom_sub_lines = bom_kit.explode(product, 1)
                ratios_virtual_available = []
                ratios_qty_available = []
                ratios_incoming_qty = []
                ratios_outgoing_qty = []
                for bom_line, bom_line_data in bom_sub_lines:
                    component = bom_line.product_id
                    uom_qty_per_kit = bom_line_data['qty'] / bom_line_data['original_qty']
                    qty_per_kit = bom_line.product_uom_id._compute_quantity(uom_qty_per_kit, bom_line.product_id.uom_id)
                    ratios_virtual_available.append(component.virtual_available / qty_per_kit)
                    ratios_qty_available.append(component.qty_available / qty_per_kit)
                    ratios_incoming_qty.append(component.incoming_qty / qty_per_kit)
                    ratios_outgoing_qty.append(component.outgoing_qty / qty_per_kit)
                if bom_sub_lines:
                    product.virtual_available = min(ratios_virtual_available) // 1
                    product.qty_available = min(ratios_qty_available) // 1
                    product.incoming_qty = min(ratios_incoming_qty) // 1
                    product.outgoing_qty = min(ratios_incoming_qty) // 1
            else:
                super(ProductProduct, self)._compute_quantities()

    def action_view_bom(self):
        action = self.env.ref('mrp.product_open_bom').read()[0]
        template_ids = self.mapped('product_tmpl_id').ids
        # bom specific to this variant or global to template
        action['context'] = {
            'default_product_tmpl_id': template_ids[0],
            'default_product_id': self.ids[0],
        }
        action['domain'] = ['|', ('product_id', 'in', self.ids), '&', ('product_id', '=', False), ('product_tmpl_id', 'in', template_ids)]
        return action

    def action_view_mos(self):
        action = self.env.ref('mrp.mrp_production_report').read()[0]
        action['domain'] = [('state', '=', 'done'), ('product_id', 'in', self.ids)]
        action['context'] = {
            'time_ranges': {'field': 'date_planned_start', 'range': 'last_365_days'},
            'graph_measure': 'product_uom_qty',
        }
        return action
