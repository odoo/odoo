# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    pos_order_id = fields.Many2one('pos.order', string='POS Order', help='The Point of Sale order linked to the payment transaction', readonly=True)

    @api.model
    def _compute_reference_prefix(self, separator, **values):
        """ Override of payment to compute the reference prefix based on POS-specific values.

        :return: The computed reference prefix if POS order id is found, the one of `super` otherwise
        :rtype: str
        """
        pos_order_id = values.get('pos_order_id')
        if pos_order_id:
            pos_order = self.env['pos.order'].sudo().browse(pos_order_id).exists()
            if pos_order:
                return pos_order.pos_reference
        return super()._compute_reference_prefix(separator, **values)

    def _post_process(self):
        """ Override of payment to process POS online payments automatically. """
        super()._post_process()
        self._process_pos_online_payment()

    def _process_pos_online_payment(self):
        for tx in self:
            if tx and tx.pos_order_id and tx.state in ('authorized', 'done') and not tx.payment_id.pos_order_id:
                pos_order = tx.pos_order_id
                if tools.float_compare(tx.amount, 0.0, precision_rounding=pos_order.currency_id.rounding) <= 0:
                    raise ValidationError(_('The payment transaction (%d) has a negative amount.', tx.id))

                if not tx.payment_id: # the payment could already have been created by account_payment module
                    tx._create_payment()
                if not tx.payment_id:
                    raise ValidationError(_('The POS online payment (tx.id=%d) could not be saved correctly', tx.id))

                payment_method = pos_order.online_payment_method_id
                if not payment_method:
                    pos_config = pos_order.config_id
                    payment_method = self.env['pos.payment.method'].sudo()._get_or_create_online_payment_method(pos_config.company_id.id, pos_config.id)
                    if not payment_method:
                        raise ValidationError(_('The POS online payment (tx.id=%d) could not be saved correctly because the online payment method could not be found', tx.id))

                pos_order.add_payment({
                    'amount': tx.amount,
                    'payment_date': tx.last_state_change,
                    'payment_method_id': payment_method.id,
                    'online_account_payment_id': tx.payment_id.id,
                    'pos_order_id': pos_order.id,
                })
                tx.payment_id.update({
                    'pos_payment_method_id': payment_method.id,
                    'pos_order_id': pos_order.id,
                    'pos_session_id': pos_order.session_id.id,
                })
                if pos_order.state == 'draft' and pos_order._is_pos_order_paid():
                    pos_order._process_saved_order(False)
                # The bus communication is only protected by the name of the channel.
                # Therefore, no sensitive information is sent through it, only a
                # notification to invite the local browser to do a safe RPC to
                # the server to check the new state of the order.
                pos_order.config_id._notify('ONLINE_PAYMENTS_NOTIFICATION', {'id': pos_order.id})

    def action_view_pos_order(self):
        """ Return the action for the view of the pos order linked to the transaction.
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
