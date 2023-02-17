# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class StockForecasted(models.AbstractModel):
    _inherit = 'stock.forecasted_product_product'

    @api.model
    def action_reserve_linked_picks(self, move_id):
        """ In case of move connected to MOs instead of picking we want to reserve the MO
        """
        linked_move_ids = super().action_reserve_linked_picks(move_id)
        production_ids = linked_move_ids.raw_material_production_id | linked_move_ids.production_id
        production_ids.filtered(lambda m: m.state not in ['draft', 'cancel', 'done']).action_assign()

    @api.model
    def action_unreserve_linked_picks(self, move_id):
        linked_move_ids = super().action_unreserve_linked_picks(move_id)
        production_ids = linked_move_ids.raw_material_production_id | linked_move_ids.production_id
        production_ids.filtered(lambda m: m.state not in ['draft', 'cancel', 'done']).do_unreserve()

    def _prepare_report_line(self, quantity, move_out=None, move_in=None, replenishment_filled=True, product=False, reserved_move=False, in_transit=False):
        line = super()._prepare_report_line(quantity, move_out, move_in, replenishment_filled, product, reserved_move, in_transit)

        if not move_out or not move_out.raw_material_production_id:
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
        res['draft_production_qty'] = {}
        domain = self._product_domain(product_template_ids, product_ids)
        domain += [('state', '=', 'draft')]

        # Pending incoming quantity.
        mo_domain = domain + [('location_dest_id', 'in', wh_location_ids)]
        grouped_mo = self.env['mrp.production'].read_group(mo_domain, ['product_qty:sum'], 'product_id')
        res['draft_production_qty']['in'] = sum(mo['product_qty'] for mo in grouped_mo)

        # Pending outgoing quantity.
        move_domain = domain + [
            ('raw_material_production_id', '!=', False),
            ('location_id', 'in', wh_location_ids),
        ]
        grouped_moves = self.env['stock.move'].read_group(move_domain, ['product_qty:sum'], 'product_id')
        res['draft_production_qty']['out'] = sum(move['product_qty'] for move in grouped_moves)
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
