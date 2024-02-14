# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from collections import defaultdict

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    purchase_order_count = fields.Integer(
        "Count of generated PO",
        compute='_compute_purchase_order_count',
        groups='purchase.group_purchase_user')

    @api.depends('procurement_group_id.stock_move_ids.created_purchase_line_id.order_id', 'procurement_group_id.stock_move_ids.move_orig_ids.purchase_line_id.order_id')
    def _compute_purchase_order_count(self):
        procurement_group_orders_count = defaultdict(int)
        domain = [
            '|',
            ('order_line.move_dest_ids.group_id', 'in', self.procurement_group_id.ids),
            ('order_line.move_ids.move_dest_ids.group_id', 'in', self.procurement_group_id.ids),
        ]
        for group in self.env['purchase.order']._read_group(domain, ['id'], ['group_id']):
            procurement_group_orders_count[group['group_id'][0]] = group['group_id_count']
        for production in self:
            production.purchase_order_count = procurement_group_orders_count[production.procurement_group_id.id]

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
