# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from odoo import api, fields, models
from odoo.exceptions import AccessError


class AccountPaymentRequest(models.Model):
    _name = "account.payment.request"
    _rec_name = 'reference'

    access_token = fields.Char(
        string='Security Token', copy=False,
        default=lambda self: str(uuid.uuid4()), required=True)
    state = fields.Selection([
        ('open', 'Open'),
        ('pending', 'Pending'),
        ('paid', 'Paid')],
        required=True, default='open')
    invoice_id = fields.Many2one('account.invoice', string='Invoice', readonly=True, copy=False)
    reference = fields.Char(string="Reference")
    partner_id = fields.Many2one('res.partner', string="Customer")
    amount_total = fields.Float(string="Total")
    payment_acquirer_id = fields.Many2one('payment.acquirer', string='Payment Acquirer', copy=False)
    payment_tx_id = fields.Many2one('payment.transaction', string='Transaction', copy=False)

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
            ('company_id', '=', self.invoice_id.company_id.id)
        ])

        payment_method = []
        for acquirer in acquirers:
            acquirer.button = acquirer.render(reference, self.amount_total, self.invoice_id.currency_id.id, values=values)
            payment_method.append(acquirer)

        return {'acquirers': payment_method, 'tokens': None, 'save_option': False}

    @api.multi
    def _prepare_payment_transaction(self, acquirer_id, tx_type='form', transaction=None, token=None):
        self.ensure_one()
        Transaction = self.env['payment.transaction'].sudo()

        if transaction:
            if transaction.payment_request_id.id != self.id or transaction.state in ['error', 'cancel'] or transaction.acquirer_id.id != acquirer_id:
                transaction = False
            elif token and transaction.payment_token_id and token != transaction.payment_token_id.id:
                # new or distinct token
                transaction = False
            elif transaction.state == 'draft':  # button cliked but no more info -> rewrite on tx or create a new one ?
                transaction.write(dict(amount=self.amount_total, type=tx_type))
        if not transaction:
            tx_values = {
                'acquirer_id': acquirer_id,
                'type': tx_type,
                'amount': self.amount_total,
                'currency_id': self.invoice_id.currency_id.id,
                'partner_id': self.partner_id.id,
                'partner_country_id': self.partner_id.country_id.id,
                'reference': Transaction.get_next_reference(self.reference),
                'payment_request_id': self.id,
            }
            if token and self.env['payment.token'].sudo().browse(int(token)).partner_id == self.partner_id:
                tx_values['payment_token_id'] = token

            transaction = Transaction.create(tx_values)
            # update record
            self.write({
                'payment_acquirer_id': acquirer_id,
                'payment_tx_id': transaction.id,
            })
        return transaction


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    payment_acquirer_id = fields.Many2one('payment.acquirer', string='Payment Acquirer', copy=False)
    payment_tx_id = fields.Many2one('payment.transaction', string='Transaction', copy=False)
    payment_request_id = fields.Many2one('account.payment.request', string='Request for Online Payment', copy=False)

    @api.multi
    def action_invoice_open(self):
        result = super(AccountInvoice, self).action_invoice_open()
        if result:
            # create record for online payment request and record use for view
            PaymentRequest = self.env['account.payment.request']
            for invoice in self:
                if not invoice.payment_request_id:
                    invoice.payment_request_id = PaymentRequest.create({
                        'invoice_id': invoice.id,
                        'partner_id': invoice.partner_id.id,
                        'reference': invoice.number,
                        'amount_total': invoice.amount_total,
                    })
        return result

    @api.multi
    def get_access_action(self):
        """Instead of the classic form view, redirect to the online invoice."""
        self.ensure_one()
        if self.env.user.share or self.env.context.get('force_website'):
            try:
                self.check_access_rule('read')
            except AccessError:
                pass
            else:
                if not self.payment_request_id:
                    self.payment_request_id = self.env['account.payment.request'].create({
                        'invoice_id': self.id,
                        'partner_id': self.partner_id.id,
                        'reference': self.number,
                        'amount_total': self.amount_total,
                    })

                return {
                    'type': 'ir.actions.act_url',
                    'url': '/payment/%s' % self.payment_request_id.access_token,
                    'target': 'self',
                    'res_id': self.id,
                }
        return super(AccountInvoice, self).get_access_action()
