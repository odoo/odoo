# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ReplenishmentReport(models.AbstractModel):
    _inherit = 'report.stock.report_product_product_replenishment'

    @api.model
    def _get_report_data(self, product_template_ids=False, product_variant_ids=False):
        res = super()._get_report_data(product_template_ids, product_variant_ids)
        location_ids = False
        # Get warehouse locations.
        if self.env.context.get('wh_location_id'):
            wh_location_id = self.env.context.get('wh_location_id')
            location_ids = self.env['stock.location'].search_read(
                [('id', 'child_of', wh_location_id)],
                ['id'],
            )
            location_ids = [loc['id'] for loc in location_ids]
        domain = [('state', '=', 'draft')]
        domain += self._product_domain(product_template_ids, product_variant_ids)
        mo_domain = domain
        if location_ids:
            mo_domain += [('location_dest_id', 'in', location_ids)]

        qty_in, qty_out = 0, 0
        # Pending incoming quantity.
        grouped_mo = self.env['mrp.production'].read_group(mo_domain, ['product_qty'], 'product_id')
        if grouped_mo:
            qty_in = sum(mo['product_qty'] for mo in grouped_mo)
        # Pending outgoing quantity.
        move_domain = domain + [('raw_material_production_id', '!=', False)]
        if location_ids:
            move_domain += [('location_id', 'in', location_ids)]
        grouped_moves = self.env['stock.move'].read_group(move_domain, ['product_qty'], 'product_id')
        if grouped_moves:
            qty_out = sum(move['product_qty'] for move in grouped_moves)

        res['draft_production_qty'] = {
            'in': qty_in,
            'out': qty_out,
        }
        res['qty']['in'] += qty_in
        res['qty']['out'] += qty_out
        return res
