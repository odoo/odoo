# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import deque

from odoo import api, Command, fields, models, _
from odoo.tools.float_utils import float_round, float_is_zero, float_compare
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    purchase_line_id = fields.Many2one(
        'purchase.order.line', 'Purchase Order Line',
        ondelete='set null', index='btree_not_null', readonly=True)
    created_purchase_line_ids = fields.Many2many(
        'purchase.order.line', 'stock_move_created_purchase_line_rel',
        'move_id', 'created_purchase_line_id', 'Created Purchase Order Lines', copy=False)

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        distinct_fields = super(StockMove, self)._prepare_merge_moves_distinct_fields()
        distinct_fields += ['purchase_line_id', 'created_purchase_line_ids']
        return distinct_fields

    @api.model
    def _prepare_merge_negative_moves_excluded_distinct_fields(self):
        excluded_fields = super()._prepare_merge_negative_moves_excluded_distinct_fields() + ['created_purchase_line_ids']
        if self.env['ir.config_parameter'].sudo().get_param('purchase_stock.merge_different_procurement'):
            excluded_fields += ['procure_method']
        return excluded_fields

    @api.depends('purchase_line_id', 'purchase_line_id.product_uom_id')
    def _compute_packaging_uom_id(self):
        super()._compute_packaging_uom_id()
        for move in self:
            if move.purchase_line_id:
                move.packaging_uom_id = move.purchase_line_id.product_uom_id

    def _compute_partner_id(self):
        # dropshipped moves should have their partner_ids directly set
        not_dropshipped_moves = self.filtered(lambda m: not m._is_dropshipped())
        super(StockMove, not_dropshipped_moves)._compute_partner_id()

    @api.depends('purchase_line_id.name')
    def _compute_description_picking(self):
        super()._compute_description_picking()
        for move in self:
            if move.purchase_line_id:
                seller = move.purchase_line_id.selected_seller_id
                vendor_reference = f'[{seller.product_code}]' if seller.product_code else ''
                vendor_reference += f' {seller.product_name}' if seller.product_name else ''
                no_variant_attributes = '\n'.join(f'{attribute.attribute_id.name}: {attribute.name}' for attribute in move.purchase_line_id.product_no_variant_attribute_value_ids)
                move.description_picking = (no_variant_attributes + '\n' + vendor_reference + '\n' + move.description_picking).strip()

    def _get_description(self):
        return self.purchase_line_id.name if self.purchase_line_id else super()._get_description()

    def _action_synch_order(self):
        purchase_order_lines_vals = []
        for move in self:
            purchase_order = move.picking_id.purchase_id or move.picking_id.return_id.purchase_id
            # Creates new PO line only when pickings linked to a purchase order and
            # for moves with qty. done and not already linked to a PO line.
            if not purchase_order \
                or (move.location_id.usage not in ['supplier', 'transit'] and not (move.location_dest_id.usage == 'supplier' and move.to_refund)) \
                or move.purchase_line_id \
                or not move.picked:
                continue
            product = move.product_id
            if line := purchase_order.order_line.filtered(lambda l: l.product_id == product):
                move.purchase_line_id = line[:1]
                continue
            quantity = move.quantity
            if move.location_dest_id.usage in ['supplier', 'transit']:
                quantity *= -1
            po_line_vals = {
                'move_ids': [Command.link(move.id)],
                'order_id': purchase_order.id,
                'product_id': product.id,
                'product_qty': 0,
                'product_uom_id': move.product_uom.id,
                'qty_received': quantity
            }
            if product.purchase_method == 'purchase':
                # No unit price if the product is purchased on the ordered qty.
                po_line_vals['price_unit'] = 0
            purchase_order_lines_vals.append(po_line_vals)
        if purchase_order_lines_vals:
            self.env['purchase.order.line'].create(purchase_order_lines_vals)
        return super()._action_synch_order()

    def _should_ignore_pol_price(self):
        self.ensure_one()
        return self.origin_returned_move_id or not self.purchase_line_id or not self.product_id.id

    def _prepare_move_split_vals(self, uom_qty):
        vals = super(StockMove, self)._prepare_move_split_vals(uom_qty)
        vals['purchase_line_id'] = self.purchase_line_id.id
        # when backordering an mto move link the bakcorder to the purchase order
        if self.procure_method == 'make_to_order' and self.created_purchase_line_ids:
            vals['created_purchase_line_ids'] = [Command.set(self.created_purchase_line_ids.ids)]
        return vals

    def _clean_merged(self):
        super(StockMove, self)._clean_merged()
        self.write({'created_purchase_line_ids': [Command.clear()]})

    def _get_upstream_documents_and_responsibles(self, visited):
        created_pl = self.created_purchase_line_ids.filtered(lambda cpl: cpl.state != 'cancel' and (cpl.state != 'draft' or self.env.context.get('include_draft_documents')))
        if created_pl:
            return [(pl.order_id, pl.order_id.user_id, visited) for pl in created_pl]
        elif self.purchase_line_id and self.purchase_line_id.state != 'cancel':
            return[(self.purchase_line_id.order_id, self.purchase_line_id.order_id.user_id, visited)]
        else:
            return super(StockMove, self)._get_upstream_documents_and_responsibles(visited)

    def _get_source_document(self):
        res = super()._get_source_document()
        return self.purchase_line_id.order_id or res

    def _is_purchase_return(self):
        self.ensure_one()
        return self.location_dest_id.usage == "supplier" or (self.origin_returned_move_id and self.location_dest_id == self.env.ref('stock.stock_location_inter_company', raise_if_not_found=False))

    def _get_all_related_sm(self, product):
        return super()._get_all_related_sm(product) | self.filtered(lambda m: m.purchase_line_id.product_id == product)

    def _get_purchase_line_and_partner_from_chain(self):
        moves_to_check = deque(self)
        seen_moves = set()
        while moves_to_check:
            current_move = moves_to_check.popleft()
            if current_move.purchase_line_id:
                return current_move.purchase_line_id.id, current_move.picking_id.partner_id.id
            seen_moves.add(current_move)
            moves_to_check.extend(
                [move for move in current_move.move_orig_ids if move not in moves_to_check and move not in seen_moves]
            )
        return None, None

    # --------------------------------------------------------
    # Valuation
    # --------------------------------------------------------

    def _get_value_from_account_move(self, quantity, at_date=None):
        if not (self.purchase_line_id and self.purchase_line_id):
            return 0, 0

        quantity = 0
        value = 0
        for aml in self.purchase_line_id.invoice_lines:
            if at_date and aml.date > at_date:
                continue
            if aml.move_id.state != 'posted':
                continue
            if aml.move_type == 'in_invoice':
                quantity += aml.quantity
                value += aml.price_subtotal
            elif aml.move_type == 'in_refund':
                quantity -= aml.quantity
                value -= aml.price_subtotal

        return value, quantity

    def _get_value_from_quotation(self, quantity, at_date=None):
        # TODO: Start from global value
        if not self.purchase_line_id:
            return super()._get_value_from_quotation(quantity)
        if at_date and self.purchase_line_id.order_id.date_order > at_date:
            return super()._get_value_from_quotation(quantity)
        price_unit = self.purchase_line_id._get_stock_move_price_unit()
        quantity = min(quantity, self.quantity)
        return price_unit * quantity, quantity

    def _get_related_invoices(self):
        """ Overridden to return the vendor bills related to this stock move.
        """
        rslt = super()._get_related_invoices()
        purchase_ids = self.env['purchase.order'].search([('picking_ids', 'in', self.picking_id.ids)])
        rslt += purchase_ids.invoice_ids.filtered(lambda x: x.state == 'posted')
        return rslt
