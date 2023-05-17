# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class PosOrder(models.Model):
    _inherit = "pos.order"

    online_payment_ids = fields.One2many('account.payment', 'pos_order_id', string='Online payments', help='The accounting online payments linked to this Point of Sale order', readonly=True)

    def _update_amount_paid(self):
        super()._update_amount_paid()

        for order in self:
            if order.online_payment_ids:
                order.amount_paid += sum(order.online_payment_ids.mapped('amount'))

    def _compute_batch_amount_all(self):
        super()._compute_batch_amount_all()

        for pos_order, amount in self.env['account.payment']._read_group([('pos_order_id', 'in', self.ids)], ['pos_order_id'], ['amount:sum']):
            pos_order.amount_paid += amount

    def action_view_online_payments(self):
        """ Return the action for the view of the pos order linked to the transaction.

        Note: self.ensure_one()

        :return: The action
        :rtype: dict
        """
        self.ensure_one()

        if self.online_payment_ids:
            if len(self.online_payment_ids) == 1:
                action = {
                    'name': _("Online payment"),
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.payment',
                    'target': 'current',
                    'res_id': self.online_payment_ids[0].id,
                    'view_mode': 'form'
                }
            else:
                action = {
                    'name': _("Online payments"),
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.payment',
                    'target': 'current',
                    'domain': [('id', 'in', self.online_payment_ids.ids)],
                    'view_mode': 'tree,form'
                }
        return action
