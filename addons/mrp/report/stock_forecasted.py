# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class StockForecasted(models.AbstractModel):
    _inherit = 'stock.forecasted_product_product'

    def _prepare_report_line(self, quantity, move_out=None, move_in=None, replenishment_filled=True, product=False, reserved_move=False, in_transit=False, read=True):
        line = super()._prepare_report_line(quantity, move_out, move_in, replenishment_filled, product, reserved_move, in_transit, read)

        if not move_out or not move_out.raw_material_production_id or not read:
            return line

        line['move_out']['raw_material_production_id'] = move_out.raw_material_production_id.read(fields=['id', 'unreserve_visible', 'reserve_visible', 'priority'])[0]
        return line

    def _move_draft_domain(self, product_template_ids, product_ids, wh_view_location_id):
        in_domain, out_domain = super()._move_draft_domain(product_template_ids, product_ids, wh_view_location_id)
        in_domain += [('production_id', '=', False)]
        out_domain += [('raw_material_production_id', '=', False)]
        return in_domain, out_domain

    def _get_report_header(self, product_template_ids, product_ids, wh_view_location_id):
        res = super()._get_report_header(product_template_ids, product_ids, wh_view_location_id)
        res['draft_production_qty'] = {}
        domain = self._product_domain(product_template_ids, product_ids)
        domain += [('state', '=', 'draft')]

        view_loc = self.env['stock.location'].browse(wh_view_location_id)
        wh_parent_path_pattern = view_loc.parent_path + '%'

        # Pending incoming quantity.
        mo_domain = domain + [('location_dest_id.parent_path', 'like', wh_parent_path_pattern)]
        [product_qty] = self.env['mrp.production']._read_group(mo_domain, aggregates=['product_qty:sum'])[0]
        res['draft_production_qty']['in'] = product_qty or 0.0

        # Pending outgoing quantity.
        move_domain = domain + [
            ('raw_material_production_id', '!=', False),
            ('location_id.parent_path', 'like', wh_parent_path_pattern),
        ]
        [product_qty] = self.env['stock.move']._read_group(move_domain, aggregates=['product_qty:sum'])[0]
        res['draft_production_qty']['out'] = product_qty or 0.0
        res['qty']['in'] += res['draft_production_qty']['in']
        res['qty']['out'] += res['draft_production_qty']['out']

        return res

    def _get_reservation_data(self, move):
        if move.production_id:
            m2o = 'production_id'
        elif move.raw_material_production_id:
            m2o = 'raw_material_production_id'
        else:
            return super()._get_reservation_data(move)
        return {
            '_name': move[m2o]._name,
            'name': move[m2o].name,
            'id': move[m2o].id
        }
