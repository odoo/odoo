# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    pos_order_ids = fields.One2many('pos.order', 'account_move')

    def _stock_account_get_last_step_stock_moves(self):
        stock_moves = super(AccountMove, self)._stock_account_get_last_step_stock_moves()
        for invoice in self.filtered(lambda x: x.move_type == 'out_invoice'):
            stock_moves += invoice.sudo().mapped('pos_order_ids.picking_ids.move_lines').filtered(lambda x: x.state == 'done' and x.location_dest_id.usage == 'customer')
        for invoice in self.filtered(lambda x: x.move_type == 'out_refund'):
            stock_moves += invoice.sudo().mapped('pos_order_ids.picking_ids.move_lines').filtered(lambda x: x.state == 'done' and x.location_id.usage == 'customer')
        return stock_moves


    def _tax_tags_need_inversion(self, move, is_refund, tax_type):
        # POS order operations are handled by the tax report just like invoices ;
        # we should never invert their tags.
        if move.move_type == 'entry':
            orders_count = self.env['pos.order'].search_count([('account_move', '=', move._origin.id)])
            sessions_count = self.env['pos.session'].search_count([('move_id', '=', move._origin.id)])
            if orders_count + sessions_count:
                return False
        return super()._tax_tags_need_inversion(move, is_refund, tax_type)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _stock_account_get_anglo_saxon_price_unit(self):
        self.ensure_one()
        if not self.product_id:
            return self.price_unit
        price_unit = super(AccountMoveLine, self)._stock_account_get_anglo_saxon_price_unit()
        order = self.move_id.pos_order_ids
        if order:
            price_unit = order._get_pos_anglo_saxon_price_unit(self.product_id, self.move_id.partner_id.id, self.quantity)
        return price_unit

    def _get_not_entry_condition(self, aml):
        # Overridden so that sale entry moves created par POS still have their amount inverted
        # in _compute_tax_audit()
        rslt = super()._get_not_entry_condition(aml)

        sessions_count = self.env['pos.session'].search_count([('move_id', '=', aml.move_id.id)])
        pos_orders_count = self.env['pos.order'].search_count([('account_move', '=', aml.move_id.id)])

        return rslt or (sessions_count + pos_orders_count)

    def _get_refund_tax_audit_condition(self, aml):
        # Overridden so that the returns can be detected as credit notes by the tax audit computation
        rslt = super()._get_refund_tax_audit_condition(aml)

        if aml.move_id.is_invoice():
            # We don't need to check the pos orders for this move line if an invoice
            # is linked to it ; we know that the invoice type tells us whether it's a refund
            return rslt

        sessions_count = self.env['pos.session'].search_count([('move_id', '=', aml.move_id.id)])
        pos_orders_count = self.env['pos.order'].search_count([('account_move', '=', aml.move_id.id)])

        return rslt or (sessions_count + pos_orders_count and aml.debit > 0)
