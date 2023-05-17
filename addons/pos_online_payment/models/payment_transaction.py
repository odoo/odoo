# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, Command, tools
from odoo.exceptions import ValidationError

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    pos_order_id = fields.Many2one('pos.order', string='POS Order', help='The Point of Sale order linked to the payment transaction', readonly=True)

    @api.model
    def _compute_reference_prefix(self, provider_code=None, separator='-', **values):
        """ Override of payment to compute the reference prefix based on POS-specific values.

        :return: The computed reference prefix if POS order id is found, the one of `super` otherwise
        :rtype: str
        """
        pos_order_id = values.get('pos_order_id')
        if pos_order_id:
            pos_order = self.env['pos.order'].sudo().browse(pos_order_id).exists()
            if pos_order:
                return pos_order.pos_reference
        return super()._compute_reference_prefix(provider_code, separator, **values)

    def _set_authorized(self, state_message=None, **kwargs):
        """ Override of payment to process POS online payments automatically. """
        super()._set_authorized(state_message=state_message, **kwargs)
        self._process_pos_online_payment()

    def _reconcile_after_done(self):
        """ Override of payment to process POS online payments automatically. """
        super()._reconcile_after_done()
        self._process_pos_online_payment()

    def _process_pos_online_payment(self):
        for tx in self:
            if tx and tx.pos_order_id and tx.state in ('authorized', 'done') and (not tx.payment_id or not tx.payment_id.pos_order_id):
                if tools.float_compare(tx.amount, 0.0, precision_rounding=tx.pos_order_id.currency_id.rounding) <= 0:
                    raise ValidationError("The payment transaction (%d) has a negative amount." % tx.id);
                if not tx.payment_id: # the payment could already have been created by account_payment module
                    account_payment = tx._create_payment()
                    if not account_payment or tx.payment_id.id != account_payment.id:
                        raise ValidationError(
                            "The POS online payment was not saved correctly (tx.id=%d)" % tx.id)
                tx.pos_order_id.online_payment_ids = [Command.link(tx.payment_id.id)]
                tx.payment_id.pos_order_id = tx.pos_order_id.id
                tx.pos_order_id._update_amount_paid()
                if tx.pos_order_id._is_pos_order_paid():
                    tx.pos_order_id.action_pos_order_paid()

    def action_view_pos_order(self):
        """ Return the action for the view of the pos order linked to the transaction.

        Note: self.ensure_one()

        :return: The action
        :rtype: dict
        """
        self.ensure_one()

        action = {
            'name': _("POS Order"),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.order',
            'target': 'current',
            'res_id': self.pos_order_id.id,
            'view_mode': 'form'
        }
        return action
