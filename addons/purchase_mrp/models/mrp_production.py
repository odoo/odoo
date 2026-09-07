# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    purchase_order_count = fields.Integer(
        "Count of generated PO",
        compute='_compute_purchase_order_count',
        groups='purchase.group_purchase_user')

    @api.depends('procurement_group_id.stock_move_ids.created_purchase_line_id.order_id', 'procurement_group_id.stock_move_ids.move_orig_ids.purchase_line_id.order_id')
    def _compute_purchase_order_count(self):
        if not self.procurement_group_id:
            self.purchase_order_count = 0
            return

        self.flush_model(['procurement_group_id'])

        self.env.cr.execute("""
            SELECT group_id, COUNT(DISTINCT order_id)
            FROM (
                SELECT sm.group_id, pol.order_id
                FROM stock_move sm
                JOIN purchase_order_line pol ON pol.id = sm.created_purchase_line_id
                WHERE sm.group_id IN %(groups)s

                UNION

                SELECT sm.group_id, pol.order_id
                FROM purchase_order_line pol
                JOIN stock_move sm_orig ON sm_orig.purchase_line_id = pol.id
                JOIN stock_move_move_rel rel ON rel.move_orig_id = sm_orig.id
                JOIN stock_move sm ON sm.id = rel.move_dest_id
                WHERE sm.group_id IN %(groups)s
            ) AS combined
            GROUP BY group_id
        """, {
            'groups': tuple(self.procurement_group_id.ids)
        })
        res = {d[0]: d[1] for d in self.env.cr.fetchall()}
        for production in self:
            production.purchase_order_count = res.get(production.procurement_group_id.id, 0)

    def action_view_purchase_orders(self):
        self.ensure_one()
        purchase_order_ids = (self.procurement_group_id.stock_move_ids.created_purchase_line_id.order_id | self.procurement_group_id.stock_move_ids.move_orig_ids.purchase_line_id.order_id).ids
        action = {
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
        }
        if len(purchase_order_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': purchase_order_ids[0],
            })
        else:
            action.update({
                'name': _("Purchase Order generated from %s", self.name),
                'domain': [('id', 'in', purchase_order_ids)],
                'view_mode': 'tree,form',
            })
        return action

    def _get_document_iterate_key(self, move_raw_id):
        iterate_key = super(MrpProduction, self)._get_document_iterate_key(move_raw_id)
        if not iterate_key and move_raw_id.created_purchase_line_id:
            iterate_key = 'created_purchase_line_id'
        return iterate_key

    def _prepare_merge_orig_links(self):
        origs = super()._prepare_merge_orig_links()
        for move in self.move_raw_ids:
            if move.created_purchase_line_id:
                origs[move.bom_line_id.id]['created_purchase_line_id'] = move.created_purchase_line_id
        return origs
