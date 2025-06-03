# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class StockForecasted_Product_Product(models.AbstractModel):
    _inherit = 'stock.forecasted_product_product'

    def _prepare_report_line(self, quantity, move_out=None, move_in=None, replenishment_filled=True, product=False, reserved_move=False, in_transit=False, read=True):
        line = super()._prepare_report_line(quantity, move_out, move_in, replenishment_filled, product, reserved_move, in_transit, read)

        if not move_out or not move_out.raw_material_production_id or not read:
            return line

        line['move_out']['raw_material_production_id'] = move_out.raw_material_production_id.read(fields=['id', 'unreserve_visible', 'reserve_visible', 'priority'])[0]
        return line

    def _move_draft_domain(self, product_template_ids, product_ids, wh_location_ids):
        in_domain, out_domain = super()._move_draft_domain(product_template_ids, product_ids, wh_location_ids)
        in_domain += [('production_id', '=', False)]
        out_domain += [('raw_material_production_id', '=', False)]
        return in_domain, out_domain

    def _get_report_header(self, product_template_ids, product_ids, wh_location_ids):
        res = super()._get_report_header(product_template_ids, product_ids, wh_location_ids)
        domain = self._product_domain(product_template_ids, product_ids)
        domain += [('state', '=', 'draft')]

        in_domain = domain + [('location_dest_id', 'in', wh_location_ids)]  # Pending incoming quantity.
        out_domain = domain + [  # Pending outgoing quantity.
            ('raw_material_production_id', '!=', False),
            ('location_id', 'in', wh_location_ids),
        ]
        in_product_qty = {k.id: v for k, v in self.env['mrp.production']._read_group(in_domain, aggregates=['product_qty:sum'], groupby=['product_id'])}
        out_product_qty = {k.id: v for k, v in self.env['stock.move']._read_group(out_domain, aggregates=['product_qty:sum'], groupby=['product_id'])}

        self._add_product_quantities(res, product_template_ids, product_ids, 'draft_production_qty', in_product_qty, out_product_qty)

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
