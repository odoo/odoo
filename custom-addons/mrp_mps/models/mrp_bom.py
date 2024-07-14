# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    schedule_count = fields.Integer('Schedules', compute='_compute_schedule_count')

    def _compute_schedule_count(self):
        domain = [
            '|',
                ('product_id.bom_line_ids.bom_id', 'in', self.ids),
                '|',
                    ('product_id', 'in', self.product_id.ids),
                    ('product_id.product_tmpl_id', 'in', self.product_tmpl_id.ids),
        ]
        grouped_data = self.env['mrp.production.schedule']._read_group(
            domain, ['product_id'], ['__count'])
        product_schedule_counts = {product.id: count for product, count in grouped_data}
        for bom in self:
            schedule_count = 0
            if bom.product_id:
                ids = bom.product_id.ids
            else:
                ids = bom.product_tmpl_id.product_variant_ids.ids
            for product_id in bom.bom_line_ids.product_id.ids + ids:
                schedule_count += product_schedule_counts.get(product_id, 0)
            bom.schedule_count = schedule_count

    def action_open_mps_view(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("mrp_mps.action_mrp_mps")
        action['domain'] = ["|", ('product_id.bom_line_ids.bom_id', '=', self.id),
                            "|", ('product_id.variant_bom_ids', '=', self.id),
                            "&", ('product_tmpl_id.bom_ids.product_id', '=', False),
                            ('product_tmpl_id.bom_ids', '=', self.id)]
        return action
