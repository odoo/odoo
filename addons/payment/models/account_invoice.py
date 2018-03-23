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
        acquirer = None
        payment_token_id = vals.get('payment_token_id')
        payment_token = None

        if payment_token_id:
            payment_token = self.env['payment.token'].sudo().browse(payment_token_id)

            # Check payment_token/acquirer matching or take the acquirer from token
            if acquirer_id:
                acquirer = self.env['payment.acquirer'].browse(acquirer_id)
                if payment_token and payment_token.acquirer_id != acquirer:
                    raise UserError(_('Invalid token found! Token acquirer %s != %s') % (
                    payment_token.acquirer_id.name, acquirer.name))
                if payment_token and payment_token.partner_id != partner:
                    raise UserError(_('Invalid token found! Token partner %s != %s') % (
                    payment_token.partner.name, partner.name))
            else:
                acquirer = payment_token.acquirer_id

        # Check an acquirer is there.
        if not acquirer_id and not acquirer:
            raise UserError(_('A payment acquirer is required to create a transaction.'))

        if not acquirer:
            acquirer = self.env['payment.acquirer'].browse(acquirer_id)

        # Check a journal is set on acquirer.
        if not acquirer.journal_id:
            raise UserError(_('A journal must be specified of the acquirer %s.' % acquirer.name))

        amount = sum(self.mapped('amount_total'))
        payment_type = 'inbound' if amount > 0 else 'outbound'
        payment_vals = {
            'amount': amount,
            'payment_type': payment_type,
            'currency_id': currency.id,
            'partner_id': partner.id,
            'partner_type': 'customer',
            'invoice_ids': [(6, 0, self.ids)],
            'journal_id': acquirer.journal_id.id,
            'company_id': acquirer.company_id.id,
            'payment_method_id': self.env.ref('payment.account_payment_method_electronic_in').id,
        }

        vals.update({
            'acquirer_id': acquirer.id,
            'partner_country_id': partner.country_id.id,
            # Do not pass the token to the payment to avoid creating a transaction automatically.
            'payment_token_id': payment_token and payment_token.id or None,
        })

        payment = self.env['account.payment'].sudo().create(payment_vals).with_transaction(vals)
        transaction = payment.payment_transaction_id

        # Track the last transaction (used on frontend)
        self.write({'payment_tx_id': transaction.id})

        # Process directly if payment_token
        if transaction.payment_token_id:
            payment.post()

        return transaction
