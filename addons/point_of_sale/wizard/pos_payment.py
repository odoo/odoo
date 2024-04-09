# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_is_zero
from odoo.exceptions import UserError


class PosMakePayment(models.TransientModel):
    _name = 'pos.make.payment'
    _description = 'Point of Sale Make Payment Wizard'

    def _default_config(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            return self.env['pos.order'].browse(active_id).session_id.config_id
        return False

    def _default_amount(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            order = self.env['pos.order'].browse(active_id)
            amount_total = order.amount_total
            # If we refund the entire order, we refund what was paid originally, else we refund the value of the items returned
            if float_is_zero(order.refunded_order_ids.amount_total + order.amount_total, precision_rounding=order.currency_id.rounding):
                amount_total = -order.refunded_order_ids.amount_paid
            return amount_total - order.amount_paid
        return False

    def _default_payment_method(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            order_id = self.env['pos.order'].browse(active_id)
            return order_id.session_id.payment_method_ids.sorted(lambda pm: pm.is_cash_count, reverse=True)[:1]
        return False

    config_id = fields.Many2one('pos.config', string='Point of Sale Configuration', required=True, default=_default_config)
    amount = fields.Float(digits=0, required=True, default=_default_amount)
    payment_method_id = fields.Many2one('pos.payment.method', string='Payment Method', required=True, default=_default_payment_method)
    payment_name = fields.Char(string='Payment Reference')
    payment_date = fields.Datetime(string='Payment Date', required=True, default=lambda self: fields.Datetime.now())

    def check(self):
        """Check the order:
        if the order is not paid: continue payment,
        if the order is paid print ticket.
        """
        self.ensure_one()

        order = self.env['pos.order'].browse(self.env.context.get('active_id', False))
        if self.payment_method_id.split_transactions and not order.partner_id:
            raise UserError(_(
                "Customer is required for %s payment method.",
                self.payment_method_id.name
            ))

        currency = order.currency_id

        init_data = self.read()[0]
        if not float_is_zero(init_data['amount'], precision_rounding=currency.rounding):
            order.add_payment({
                'pos_order_id': order.id,
                'amount': order._get_rounded_amount(init_data['amount']),
                'name': init_data['payment_name'],
                'payment_method_id': init_data['payment_method_id'][0],
            })

        if order._is_pos_order_paid():
            order.action_pos_order_paid()
            order._create_order_picking()
            order._compute_total_cost_in_real_time()
            return {'type': 'ir.actions.act_window_close'}

        return self.launch_payment()

    def launch_payment(self):
        return {
            'name': _('Payment'),
            'view_mode': 'form',
            'res_model': 'pos.make.payment',
            'view_id': False,
            'target': 'new',
            'views': False,
            'type': 'ir.actions.act_window',
            'context': self.env.context,
        }
