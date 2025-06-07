# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, fields, models, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    purchase_order_count = fields.Integer(
        "Count of generated PO",
        compute='_compute_purchase_order_count',
        groups='purchase.group_purchase_user')

    @api.depends('procurement_group_id.stock_move_ids.created_purchase_line_ids.order_id', 'procurement_group_id.stock_move_ids.move_orig_ids.purchase_line_id.order_id')
    def _compute_purchase_order_count(self):
        for production in self:
            production.purchase_order_count = len(production._get_purchase_orders())

    def action_view_purchase_orders(self):
        self.ensure_one()
        purchase_order_ids = self._get_purchase_orders().ids
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
                'view_mode': 'list,form',
            })
        return action

    def _get_document_iterate_key(self, move_raw_id):
        iterate_key = super(MrpProduction, self)._get_document_iterate_key(move_raw_id)
        if not iterate_key and move_raw_id.created_purchase_line_ids:
            iterate_key = 'created_purchase_line_ids'
        return iterate_key

    def _get_purchase_orders(self):
        self.ensure_one()
        linked_po = self.procurement_group_id.stock_move_ids.created_purchase_line_ids.order_id \
                  | self.env['stock.move'].browse(self.procurement_group_id.stock_move_ids._rollup_move_origs()).purchase_line_id.order_id
        group_po = self.procurement_group_id.purchase_line_ids.order_id

        return linked_po | group_po

    def _prepare_merge_orig_links(self):
        origs = super()._prepare_merge_orig_links()
        for move in self.move_raw_ids:
            if not move.move_orig_ids or not move.created_purchase_line_ids:
                continue
            origs[move.bom_line_id.id].setdefault('created_purchase_line_ids', set()).update(move.created_purchase_line_ids.ids)
        for vals in origs.values():
            if vals.get('created_purchase_line_ids'):
                vals['created_purchase_line_ids'] = [Command.set(vals['created_purchase_line_ids'])]
            else:
                vals['created_purchase_line_ids'] = []
        return origs
