# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_ids = fields.Many2many('account.payment', 'account_payment_sale_order_rel', 'sale_order_id', 'account_payment_id',
                                   string='Payments', readonly=True)
    payment_ids_nbr = fields.Integer(string='# of Payments', compute='_compute_payment_ids_nbr')
    payment_tx_id = fields.Many2one('payment.transaction', string='Last Transaction', copy=False)

    @api.depends('payment_ids')
    def _compute_payment_ids_nbr(self):
        for so in self:
            so.payment_ids_nbr = len(so.payment_ids)

    @api.multi
    def get_portal_transactions(self):
        '''Retrieve the transactions to display in the portal.
        The transactions must be 'posted' (e.g. success with Paypal) or 'draft' + pending (Wire Transfer)
        but not in 'capture' (the user must capture the amount manually to get paid and set the transaction to
        'posted').

        :return: The transactions to display in the portal.
        '''
        return self.mapped('payment_ids.payment_transaction_id')\
            .filtered(lambda trans: trans.state == 'posted' or (trans.state == 'draft' and trans.pending))

    @api.multi
    def get_portal_last_transaction(self):
        return self.sudo().payment_tx_id

    @api.multi
    def create_payment_transaction(self, vals):
        # Ensure the currencies are the same.
        currency = self[0].pricelist_id.currency_id
        if any([so.pricelist_id.currency_id != currency for so in self]):
            raise UserError(_('A transaction can\'t be linked to sales orders having different currencies.'))

        # Ensure the partner are the same.
        partner = self[0].partner_id
        if any([so.partner_id != partner for so in self]):
            raise UserError(_('A transaction can\'t be linked to sales orders having different partners.'))

        # Try to retrieve the acquirer. However, fallback to the token's acquirer.
        acquirer_id = vals.get('acquirer_id')

        if vals.get('payment_token_id'):
            payment_token = self.env['payment.token'].sudo().browse(vals['payment_token_id'])

            # Check payment_token/acquirer matching or take the acquirer from token
            if acquirer_id:
                acquirer = self.env['payment.acquirer'].browse(vals['acquirer_id'])
                if payment_token and payment_token.acquirer_id != acquirer:
                    raise UserError(_('Invalid token found! Token acquirer %s != %s') % (payment_token.acquirer_id.name, acquirer.name))
                if payment_token and payment_token.partner_id != partner:
                    raise UserError(_('Invalid token found! Token partner %s != %s') % (payment_token.partner.name, partner.name))
            else:
                acquirer_id = payment_token.acquirer_id.id

        # Check an acquirer was found.
        if not acquirer_id:
            raise UserError(_('A payment acquirer is required to create a transaction.'))

        vals.update({
            'acquirer_id': acquirer_id,
            'amount': sum(self.mapped('amount_total')),
            'currency_id': currency.id,
            'partner_id': partner.id,
            'partner_country_id': partner.country_id.id,
            'sale_order_ids': [(6, 0, self.ids)],
        })

        transaction = self.env['payment.transaction'].create(vals)

        # Track the last transaction (used on frontend)
        self.write({'payment_tx_id': transaction.id})

        # Process directly if payment_token
        if transaction.payment_token_id:
            transaction.s2s_do_transaction()

        return transaction

    @api.multi
    def action_view_payments(self):
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Payment(s)'),
            'res_model': 'account.payment',
        }
        payment_ids = self.payment_ids
        if len(payment_ids) == 1:
            action.update({
                'res_id': payment_ids[0].id,
                'view_mode': 'form',
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payment_ids.ids)],
            })
        return action

    @api.multi
    def _force_lines_to_invoice_policy_order(self):
        for line in self.order_line:
            if self.state in ['sale', 'done']:
                line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
            else:
                line.qty_to_invoice = 0
