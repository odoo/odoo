# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class PosOrder(models.Model):
    _inherit = 'pos.order'

    online_payment_method_id = fields.Many2one('pos.payment.method', compute="_compute_online_payment_method_id")
    next_online_payment_amount = fields.Float(string='Next online payment amount to pay', digits=0, required=False)  # unlimited precision

    @api.depends('config_id.payment_method_ids')
    def _compute_online_payment_method_id(self):
        for order in self:
            order.online_payment_method_id = order.config_id._get_cashier_online_payment_method()

    def get_amount_unpaid(self):
        self.ensure_one()
        if self.config_id.cash_rounding and self.config_id.only_round_cash_method:
            # Online payments are never rounded: pay the exact residual.
            return self.currency_id.round(self.amount_total - self.amount_paid)
        return self.currency_id.round(self._get_rounded_amount(self.amount_total) - self.amount_paid)

    def get_and_set_online_payments_data(self, next_online_payment_amount=False):
        """ Allows to update the amount to pay for the next online payment and
            get online payments already made and how much remains to be paid.
            If next_online_payment_amount is different than False, updates the
            next online payment amount, otherwise, the next online payment amount
            is unchanged.
        """
        self.ensure_one()
        is_paid = self.state in ('paid', 'done')
        if is_paid:
            return {
                'id': self.id,
                'paid_order': self.read([], load=False),
            }

        online_payments = self.sudo().env['pos.payment'].search_read(domain=['&', ('pos_order_id', '=', self.id), ('online_account_payment_id', '!=', False)], fields=['payment_method_id', 'amount'], load=False)
        return_data = {
            'id': self.id,
            'online_payments': online_payments,
            'amount_unpaid': self.get_amount_unpaid(),
        }
        if not isinstance(next_online_payment_amount, bool) and self._check_next_online_payment_amount(next_online_payment_amount):
            self.next_online_payment_amount = next_online_payment_amount

        return return_data

    def _check_next_online_payment_amount(self, amount):
        self.ensure_one()
        return tools.float_compare(amount, 0.0, precision_rounding=self.currency_id.rounding) >= 0 and tools.float_compare(amount, self.get_amount_unpaid(), precision_rounding=self.currency_id.rounding) <= 0

    def _get_checked_next_online_payment_amount(self):
        self.ensure_one()
        amount = self.next_online_payment_amount
        return amount if self._check_next_online_payment_amount(amount) else False
