# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    payment_tx_id = fields.Many2one('payment.transaction', string='Last Transaction', copy=False)

    @api.multi
    def create_payment_transaction(self, vals):
        '''Similar to self.env['payment.transaction'].create(vals) but the values are filled with the
        current invoices fields (e.g. the partner or the currency).
        Furthermore, this method allows to tracking the last transaction done by the portal user.

        :param vals: The values to create a new payment.transaction.
        :return: The newly created payment.transaction record.
        '''
        # Ensure the currencies are the same.
        currency = self[0].currency_id
        if any([inv.currency_id != currency for inv in self]):
            raise UserError(_('A transaction can\'t be linked to invoices having different currencies.'))

        # Ensure the partner are the same.
        partner = self[0].partner_id
        if any([inv.partner_id != partner for inv in self]):
            raise UserError(_('A transaction can\'t be linked to invoices having different partners.'))

        # Try to retrieve the acquirer. However, fallback to the token's acquirer.
        acquirer_id = vals.get('acquirer_id')

        if vals.get('payment_token_id'):
            payment_token = self.env['payment.token'].sudo().browse(vals['payment_token_id'])

            # Check payment_token/acquirer matching or take the acquirer from token
            if acquirer_id:
                acquirer = self.env['payment.acquirer'].browse(vals['acquirer_id'])
                if payment_token and payment_token.acquirer_id != acquirer:
                    raise UserError(_('Invalid token found! Token acquirer %s != %s') % (
                    payment_token.acquirer_id.name, acquirer.name))
                if payment_token and payment_token.partner_id != partner:
                    raise UserError(_('Invalid token found! Token partner %s != %s') % (
                    payment_token.partner.name, partner.name))
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
            'invoice_ids': [(6, 0, self.ids)],
        })

        transaction = self.env['payment.transaction'].create(vals)

        # Track the last transaction (used on frontend)
        self.write({'payment_tx_id': transaction.id})

        # Process directly if payment_token
        if transaction.payment_token_id:
            transaction.s2s_do_transaction()

        return transaction
