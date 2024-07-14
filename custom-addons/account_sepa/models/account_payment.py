# -*- coding: utf-8 -*-

from uuid import uuid4

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    sepa_pain_version = fields.Selection(related='journal_id.sepa_pain_version')
    sepa_uetr = fields.Char(
        string='UETR',
        compute='_compute_sepa_uetr',
        store=True,
        help='Unique end-to-end transaction reference',
    )

    @api.model
    def _get_method_codes_using_bank_account(self):
        res = super(AccountPayment, self)._get_method_codes_using_bank_account()
        res += ['sepa_ct']
        return res

    @api.model
    def _get_method_codes_needing_bank_account(self):
        res = super(AccountPayment, self)._get_method_codes_needing_bank_account()
        res += ['sepa_ct']
        return res

    @api.constrains('payment_method_line_id', 'journal_id')
    def _check_sepa_bank_account(self):
        sepa_payment_method = self.env.ref('account_sepa.account_payment_method_sepa_ct')
        for rec in self:
            if rec.payment_method_id == sepa_payment_method:
                if not rec.journal_id.bank_account_id or not rec.journal_id.bank_account_id.acc_type == 'iban':
                    raise ValidationError(_("The journal '%s' requires a proper IBAN account to pay via SEPA. Please configure it first.", rec.journal_id.name))

    def _get_payment_method_codes_to_exclude(self):
        res = super()._get_payment_method_codes_to_exclude()
        currency_codes = ['BGN', 'HRK', 'CZK', 'DKK', 'GIP', 'HUF', 'ISK', 'CHF', 'NOK', 'PLN', 'RON', 'SEK', 'GBP', 'EUR', 'XPF']
        currency_ids = self.env['res.currency'].with_context(active_test=False).search([('name', 'in', currency_codes)])
        sepa_ct = self.env.ref('account_sepa.account_payment_method_sepa_ct', raise_if_not_found=False)
        if sepa_ct and self.currency_id not in currency_ids:
            res.append(sepa_ct.code)
        return res

    @api.depends('payment_method_id')
    def _compute_sepa_uetr(self):
        # don't make changes to the existing uetr even if the pain version changes
        # add uetr only on payments with a SEPA credit transfer
        payments = self.filtered(
            lambda p: not p.sepa_uetr and p.payment_method_id.code == 'sepa_ct'
        )
        for payment in payments:
            payment.sepa_uetr = uuid4() if payment.journal_id.sepa_pain_version == 'pain.001.001.09' else False
