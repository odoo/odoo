# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_tx_id = fields.Many2one('payment.transaction', string='Last Transaction', copy=False)
    payment_acquirer_id = fields.Many2one('payment.acquirer', string='Payment Acquirer', related='payment_tx_id.acquirer_id', store=True)

    def _force_lines_to_invoice_policy_order(self):
        for line in self.order_line:
            if self.state in ['sale', 'done']:
                line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

    # ==============
    # Payment #
    # ==============

    @api.multi
    def _prepare_payment_acquirer(self, values=None):
        self.ensure_one()
        env = self.env
        # auto-increment reference with a number suffix
        # if the reference already exists
        reference = env['payment.transaction'].get_next_reference(self.reference)
        acquirers = env['payment.acquirer'].sudo().search([
            ('website_published', '=', True),
            ('company_id', '=', self.company_id.id)
        ])
        payment_method = []
        for acquirer in acquirers:
            acquirer.button = acquirer.render(reference, self.amount_total, self.currency_id.id, values=values)
            payment_method.append(acquirer)

        return {'acquirers': payment_method, 'tokens': None, 'save_option': False}

    @api.multi
    def _prepare_payment_transaction(self, acquirer, tx_type='form', transaction=None, payment_token=None, add_tx_values=None, reset_draft=True):
        self.ensure_one()
        Transaction = self.env['payment.transaction'].sudo()
        # incorrect state or unexisting tx
        if not transaction or transaction.state in ['error', 'cancel']:
            transaction = False
        # unmatching
        if (transaction and acquirer and transaction.acquirer_id != acquirer) or (transaction and transaction.sale_order_id != self):
            transaction = False
        # new or distinct token
        if payment_token and transaction.payment_token_id and payment_token != transaction.payment_token_id:
            transaction = False

        # still draft tx, no more info -> rewrite on tx or create a new one depending on parameter
        if transaction and transaction.state == 'draft':
            if reset_draft:
                transaction.write(dict(
                    transaction.on_change_partner_id(self.partner_id.id).get('value', {}),
                    amount=self.amount_total,
                    type=tx_type)
                )
            else:
                transaction = False

        if not transaction:
            tx_values = {
                'acquirer_id': acquirer.id,
                'type': tx_type,
                'amount': self.amount_total,
                'currency_id': self.currency_id.id,
                'partner_id': self.partner_id.id,
                'partner_country_id': self.partner_id.country_id.id,
                'reference': Transaction.get_next_reference(self.reference),
                'payment_request_id': self.id,
            }
            if add_tx_values:
                tx_values.update(add_tx_values)
            if payment_token and payment_token.sudo().partner_id == self.partner_id:
                tx_values['payment_token_id'] = payment_token.id

            transaction = Transaction.create(tx_values)
            # update record
        self.write({
            'payment_acquirer_id': acquirer.id,
            'payment_tx_id': transaction.id,
        })
        return transaction

    @api.multi
    def render_sale_payment_button(self, transaction, return_url, submit_txt=None, render_values=None):
        self.ensure_one()
        values = {
            'return_url': return_url,
            'partner_id': self.partner_shipping_id.id or self.partner_invoice_id.id,
            'billing_partner_id': self.partner_invoice_id.id,
        }
        if render_values:
            values.update(render_values)

        return transaction.acquirer_id.with_context(submit_class='btn btn-primary', submit_txt=submit_txt or _('Pay Now')).sudo().render(
            transaction.reference,
            self.amount_total,
            self.pricelist_id.currency_id.id,
            values=values,
        )
