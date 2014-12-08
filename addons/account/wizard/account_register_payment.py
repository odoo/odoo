# -*- coding: utf-8 -*-
import time

from openerp import models, fields, api, _
from openerp.exceptions import Warning
import openerp.addons.decimal_precision as dp

# Map invoice type to prefix of the aml created in the invoice account
TYPE2PREFIX = {
    'out_invoice': 'Payment from ',
    'in_invoice': 'Payment to ',
    'out_refund': 'Refund from ',
    'in_refund': 'Refund to ',
}

class account_register_payment(models.TransientModel):
    _name = "account.register.payment"
    _description = "Register payment"
    
    invoice_id = fields.Many2one('account.invoice', String="Related invoice", required=True)
    payment_amount = fields.Float(String='Amount paid', required=True, digits=0)
    date_paid = fields.Date(String='Date paid', default=fields.Date.context_today, required=True)
    reference = fields.Char('Ref #', help="Transaction reference number.")
    journal_id = fields.Many2one('account.journal', String='Payment Method', required=True, domain=[('type', 'in', ('bank', 'cash'))])
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', readonly=True,
        default=lambda self: self.env.user.company_id)
    partner_id = fields.Many2one('res.partner', related='invoice_id.partner_id', String='Partner')
    payment_difference = fields.Selection([('open', 'Keep Open'), ('reconcile', 'Reconcile Payment Balance')], required=True, String="Payment difference")
    writeoff_account = fields.Many2one('account.account', String="Counterpart Account")

    @api.one
    @api.constrains('payment_amount')
    def _check_amount(self):
        if self.payment_amount == 0.0:
            raise Warning('Please enter payment amount.')

    @api.model
    def default_get(self, fields):
        context = dict(self._context or {})
        res = super(account_register_payment, self).default_get(fields)
        if context.get('active_id'):
            invoice = self.env['account.invoice'].browse(context.get('active_id'))
            res.update({
                'invoice_id': invoice.id,
                'payment_amount': invoice.residual,
                'payment_difference': 'open',
            })
        return res

    @api.multi
    def pay(self):
        """ Create an account_move and account_move_line based on payment then reconcile the invoice with the payment """

        # Compute values

        if not self.journal_id.sequence_id:
            raise Warning(_('Configuration Error !'), _('The journal ' + self.journal_id.name + ' does not have a sequence, please specify one.'))
        if not self.journal_id.sequence_id.active:
            raise Warning(_('Configuration Error !'), _('The sequence of journal ' + self.journal_id.name + ' is deactivated.'))
        move_name = self.journal_id.sequence_id.next_by_id()

        sign = self.invoice_id.type in ('out_invoice', 'in_refund') and -1 or 1
        amount = sign * self.payment_amount
        debit, credit, amount_currency = self.env['account.move.line'].compute_amount_fields(amount, self.journal_id.currency, self.company_id.currency_id)

        invoice_account_aml_name = self.invoice_id.number
        payment_account_aml_name = TYPE2PREFIX[self.invoice_id.type] + self.partner_id.name

        # Create move

        invoice_account_aml = {
            'name': invoice_account_aml_name,
            'account_id': self.invoice_id.account_id.id,
            'journal_id': self.journal_id.id,
            'debit': debit,
            'credit': credit,
            'partner_id': self.invoice_id.partner_id.id,
            'currency_id': self.journal_id.currency.id,
            'amount_currency': amount_currency or False,
            'date': self.date_paid,
            'invoice': self.invoice_id.id,
        }

        payment_account_aml = invoice_account_aml.copy()
        payment_account_aml.update({
            'name': payment_account_aml_name,
            # TOCHECK :   self.journal_id.default_credit_account_id.id if self.invoice_id.type in ('out_invoice', 'in_refund') ?
            'account_id': self.journal_id.default_debit_account_id.id,
            'debit': credit,
            'credit': debit,
            'amount_currency': amount_currency and - amount_currency or False,
        })

        move_id = self.env['account.move'].create({
            'name': move_name,
            'date': self.date_paid,
            'ref': self.reference,
            'company_id': self.company_id.id,
            'journal_id': self.journal_id.id,
            'line_id': [(0, 0, invoice_account_aml), (0, 0, payment_account_aml)],
        })

        move_id.post()

        # Reconcile
        payment_line = move_id.line_id.filtered(lambda r: r.account_id == self.invoice_id.account_id)
        writeoff_account = self.writeoff_account if self.payment_difference == 'reconcile' else False
        writeoff_journal = self.journal_id if self.payment_difference == 'reconcile' else False
        self.invoice_id.register_payment(payment_line, writeoff_account, writeoff_journal)
