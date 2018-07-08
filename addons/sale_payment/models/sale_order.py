# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    transaction_ids = fields.Many2many('payment.transaction', 'sale_order_transaction_rel', 'sale_order_id', 'transaction_id',
                                       string='Transactions', copy=False, readonly=True)
    authorized_transaction_ids = fields.Many2many('payment.transaction', compute='_compute_authorized_transaction_ids',
                                                  string='Authorized Transactions', copy=False, readonly=True)

    @api.depends('transaction_ids')
    def _compute_authorized_transaction_ids(self):
        for trans in self:
            trans.authorized_transaction_ids = trans.transaction_ids.filtered(lambda t: t.state == 'authorized')

    @api.multi
    def get_portal_last_transaction(self):
        self.ensure_one()
        return self.transaction_ids.get_last_transaction()

    @api.multi
    def _create_payment_transaction(self, vals):
        '''Similar to self.env['payment.transaction'].create(vals) but the values are filled with the
        current sales orders fields (e.g. the partner or the currency).
        :param vals: The values to create a new payment.transaction.
        :return: The newly created payment.transaction record.
        '''
        # Ensure the currencies are the same.
        currency = self[0].pricelist_id.currency_id
        if any([so.pricelist_id.currency_id != currency for so in self]):
            raise ValidationError(_('A transaction can\'t be linked to sales orders having different currencies.'))

        # Ensure the partner are the same.
        partner = self[0].partner_id
        if any([so.partner_id != partner for so in self]):
            raise ValidationError(_('A transaction can\'t be linked to sales orders having different partners.'))

        # Try to retrieve the acquirer. However, fallback to the token's acquirer.
        acquirer_id = vals.get('acquirer_id')
        acquirer = False
        payment_token_id = vals.get('payment_token_id')

        if payment_token_id:
            payment_token = self.env['payment.token'].sudo().browse(payment_token_id)

            # Check payment_token/acquirer matching or take the acquirer from token
            if acquirer_id:
                acquirer = self.env['payment.acquirer'].browse(acquirer_id)
                if payment_token and payment_token.acquirer_id != acquirer:
                    raise ValidationError(_('Invalid token found! Token acquirer %s != %s') % (
                    payment_token.acquirer_id.name, acquirer.name))
                if payment_token and payment_token.partner_id != partner:
                    raise ValidationError(_('Invalid token found! Token partner %s != %s') % (
                    payment_token.partner.name, partner.name))
            else:
                acquirer = payment_token.acquirer_id

        # Check an acquirer is there.
        if not acquirer_id and not acquirer:
            raise ValidationError(_('A payment acquirer is required to create a transaction.'))

        if not acquirer:
            acquirer = self.env['payment.acquirer'].browse(acquirer_id)

        # Check a journal is set on acquirer.
        if not acquirer.journal_id:
            raise ValidationError(_('A journal must be specified of the acquirer %s.' % acquirer.name))

        if not acquirer_id and acquirer:
            vals['acquirer_id'] = acquirer.id

        vals.update({
            'amount': sum(self.mapped('amount_total')),
            'currency_id': currency.id,
            'partner_id': partner.id,
            'sale_order_ids': [(6, 0, self.ids)],
        })

        transaction = self.env['payment.transaction'].create(vals)

        # Process directly if payment_token
        if transaction.payment_token_id:
            transaction.s2s_do_transaction()

        return transaction

    def _force_lines_to_invoice_policy_order(self):
        for line in self.order_line:
            if self.state in ['sale', 'done']:
                line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

    @api.multi
    def _prepare_invoice(self):
        # Override
        # Add the transactions in the SO to the invoices.
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['transaction_ids'] = [(6, 0, self.transaction_ids.ids)]
        return invoice_vals

    @api.multi
    def payment_action_capture(self):
        self.authorized_transaction_ids.s2s_capture_transaction()

    @api.multi
    def payment_action_void(self):
        self.authorized_transaction_ids.s2s_void_transaction()
