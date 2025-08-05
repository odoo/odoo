# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'pos.load.mixin']

    pos_order_ids = fields.One2many('pos.order', 'account_move')
    pos_payment_ids = fields.One2many('pos.payment', 'account_move_id')
    pos_refunded_invoice_ids = fields.Many2many('account.move', 'refunded_invoices', 'refund_account_move', 'original_account_move')
    reversed_pos_order_id = fields.Many2one('pos.order', string="Reversed POS Order",
        index='btree_not_null',
        help="The pos order that was reverted after closing the session to create an invoice for it.")
    pos_session_ids = fields.One2many("pos.session", "move_id", "POS Sessions")
    pos_order_count = fields.Integer(compute="_compute_origin_pos_count", string='POS Order Count')

    @api.depends('pos_order_ids')
    def _compute_origin_pos_count(self):
        for move in self:
            move.pos_order_count = len(move.sudo().pos_order_ids)

    @api.depends('tax_cash_basis_created_move_ids', 'pos_session_ids')
    def _compute_always_tax_exigible(self):
        super()._compute_always_tax_exigible()
        # The pos closing move does not create caba entries (anymore); we set the tax values directly on the closing move.
        # (But there may still be old closing moves that used caba entries from previous versions.)
        for move in self:
            if move.always_tax_exigible or move.tax_cash_basis_created_move_ids:
                continue
            if move.pos_session_ids:
                move.always_tax_exigible = True

    def _stock_account_get_last_step_stock_moves(self):
        stock_moves = super(AccountMove, self)._stock_account_get_last_step_stock_moves()
        for invoice in self.filtered(lambda x: x.move_type == 'out_invoice'):
            stock_moves += invoice.sudo().mapped('pos_order_ids.picking_ids.move_ids').filtered(lambda x: x.state == 'done' and x.location_dest_id.usage == 'customer')
        for invoice in self.filtered(lambda x: x.move_type == 'out_refund'):
            stock_moves += invoice.sudo().mapped('pos_order_ids.picking_ids.move_ids').filtered(lambda x: x.state == 'done' and x.location_id.usage == 'customer')
        return stock_moves


    def _get_invoiced_lot_values(self):
        self.ensure_one()

        lot_values = super(AccountMove, self)._get_invoiced_lot_values()

        if self.state == 'draft':
            return lot_values

        # user may not have access to POS orders, but it's ok if they have
        # access to the invoice
        for order in self.sudo().pos_order_ids:
            for line in order.lines:
                lots = line.pack_lot_ids or False
                if lots:
                    for lot in lots:
                        lot_values.append({
                            'product_name': lot.product_id.name,
                            'quantity': line.qty if lot.product_id.tracking == 'lot' else 1.0,
                            'uom_name': line.product_uom_id.name,
                            'lot_name': lot.lot_name,
                            'pos_lot_id': lot.id,
                        })

        return lot_values

    def _compute_payments_widget_reconciled_info(self):
        """Add pos_payment_name field in the reconciled vals to be able to show the payment method in the invoice."""
        super()._compute_payments_widget_reconciled_info()
        for move in self:
            if move.invoice_payments_widget:
                if move.state == 'posted' and move.is_invoice(include_receipts=True):
                    reconciled_partials = move._get_all_reconciled_invoice_partials()
                    for i, reconciled_partial in enumerate(reconciled_partials):
                        counterpart_line = reconciled_partial['aml']
                        pos_payment = counterpart_line.move_id.sudo().pos_payment_ids[:1]
                        move.invoice_payments_widget['content'][i].update({
                            'pos_payment_name': pos_payment.payment_method_id.name,
                        })

    def _compute_amount(self):
        super()._compute_amount()
        for move in self:
            if move.move_type == 'entry' and move.reversed_pos_order_id:
                move.amount_total_signed = move.amount_total_signed * -1

    def _compute_tax_totals(self):
        return super(AccountMove, self.with_context(linked_to_pos=bool(self.sudo().pos_order_ids)))._compute_tax_totals()

    def action_view_source_pos_orders(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('point_of_sale.action_pos_pos_form')

        if len(self.pos_order_ids) == 1:
            action['views'] = [(self.env.ref('point_of_sale.view_pos_pos_form', False).id, 'form')]
            action['res_id'] = self.pos_order_ids.id
        else:
            action['domain'] = [('id', 'in', self.pos_order_ids.ids)]
        return action

    @api.model
    def _load_pos_data_fields(self, config):
        result = super()._load_pos_data_fields(config)
        return result or ['id', 'name']

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_cogs_value(self):
        self.ensure_one()
        if not self.product_id:
            return self.price_unit
        price_unit = super()._get_cogs_value()
        sudo_order = self.move_id.sudo().pos_order_ids
        if sudo_order:
            price_unit = sudo_order._get_pos_anglo_saxon_price_unit(self.product_id, self.move_id.partner_id.id, self.quantity)
        return price_unit

    def _compute_name(self):
        amls = self.filtered(lambda l: not l.move_id.pos_session_ids)
        super(AccountMoveLine, amls)._compute_name()
