# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    pos_order_ids = fields.One2many('pos.order', 'account_move')

    def _stock_account_get_last_step_stock_moves(self):
        stock_moves = super(AccountMove, self)._stock_account_get_last_step_stock_moves()
        for invoice in self.filtered(lambda x: x.type == 'out_invoice'):
            stock_moves += invoice.sudo().mapped('pos_order_ids.picking_id.move_lines').filtered(lambda x: x.state == 'done' and x.location_dest_id.usage == 'customer')
        for invoice in self.filtered(lambda x: x.type == 'out_refund'):
            stock_moves += invoice.sudo().mapped('pos_order_ids.picking_id.move_lines').filtered(lambda x: x.state == 'done' and x.location_id.usage == 'customer')
        return stock_moves

    def _compute_amount(self):
        super(AccountMove, self)._compute_amount()
        pos_invoices = self.filtered(lambda i: i.type in ['out_invoice', 'out_refund'] and i.pos_order_ids)
        for invoice in pos_invoices:
            invoice.invoice_payment_state = 'paid'

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _stock_account_get_anglo_saxon_price_unit(self):
        self.ensure_one()
        if not self.product_id:
            return self.price_unit
        price_unit = super(AccountMoveLine, self)._stock_account_get_anglo_saxon_price_unit()
        order = self.move_id.pos_order_ids
        if order:
            price_unit = - order._get_pos_anglo_saxon_price_unit(self.product_id, self.move_id.partner_id.id, self.quantity)
        return price_unit
