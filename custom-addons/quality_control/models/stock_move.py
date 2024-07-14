# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_confirm(self, merge=True, merge_into=False):
        moves = super(StockMove, self)._action_confirm(merge=merge, merge_into=merge_into)
        moves._create_quality_checks()
        return moves

    def _create_quality_checks(self):
        # Groupby move by picking. Use it in order to generate missing quality checks.
        pick_moves = defaultdict(lambda: self.env['stock.move'])
        for move in self:
            if move.picking_id:
                pick_moves[move.picking_id] |= move
        check_vals_list = self._create_operation_quality_checks(pick_moves)
        for picking, moves in pick_moves.items():
            # Quality checks by product
            quality_points_domain = self.env['quality.point']._get_domain(moves.product_id, picking.picking_type_id, measure_on='product')
            quality_points = self.env['quality.point'].sudo().search(quality_points_domain)

            if not quality_points:
                continue
            picking_check_vals_list = quality_points._get_checks_values(moves.product_id, picking.company_id.id, existing_checks=picking.sudo().check_ids)
            for check_value in picking_check_vals_list:
                check_value.update({
                    'picking_id': picking.id,
                })
            check_vals_list += picking_check_vals_list
        self.env['quality.check'].sudo().create(check_vals_list)

    def _create_operation_quality_checks(self, pick_moves):
        check_vals_list = []
        for picking, moves in pick_moves.items():
            quality_points_domain = self.env['quality.point']._get_domain(moves.product_id, picking.picking_type_id, measure_on='operation')
            quality_points = self.env['quality.point'].sudo().search(quality_points_domain)
            for point in quality_points:
                if point.check_execute_now():
                    check_vals_list.append({
                        'point_id': point.id,
                        'team_id': point.team_id.id,
                        'measure_on': 'operation',
                        'picking_id': picking.id,
                    })
        return check_vals_list

    def _action_cancel(self):
        res = super()._action_cancel()

        to_unlink = self.env['quality.check'].sudo()
        is_product_canceled = defaultdict(lambda: True)
        for qc in self.picking_id.sudo().check_ids:
            if qc.quality_state != 'none':
                continue
            if (qc.picking_id, qc.product_id) not in is_product_canceled:
                for move in qc.picking_id.move_ids:
                    is_product_canceled[(move.picking_id, move.product_id)] &= move.state == 'cancel'
            if is_product_canceled[(qc.picking_id, qc.product_id)]:
                to_unlink |= qc
        to_unlink.unlink()

        return res
