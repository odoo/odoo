# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrExpenseRegisterPaymentWizard(models.TransientModel):
    _inherit = "hr.expense.sheet.register.payment.wizard"

    check_amount_in_words = fields.Char(string="Amount in Words", compute='_compute_check_amount_in_words', store=True, readonly=False)
    check_manual_sequencing = fields.Boolean(related='journal_id.check_manual_sequencing', readonly=False)
    # Note: a check_number == 0 means that it will be attributed when the check is printed
    check_number = fields.Char(string="Check Number", compute='_compute_check_number', store=True, copy=False,
        help="Number of the check corresponding to this payment. If your pre-printed check are not already numbered, "
             "you can manage the numbering in the journal configuration page.")
    payment_method_code_2 = fields.Char(related='payment_method_id.code',
                                      help="Technical field used to adapt the interface to the payment type selected.",
                                      string="Payment Method Code 2",
                                      readonly=True)

    @api.depends('journal_id')
    def _compute_check_number(self):
        for wizard in self:
            if wizard.journal_id.check_manual_sequencing:
                wizard.check_number = wizard.journal_id.check_sequence_id.number_next_actual
            else:
                wizard.check_number = 0

    @api.depends('amount')
    def _compute_check_amount_in_words(self):
        for wizard in self:
            wizard.check_amount_in_words = wizard.currency_id.amount_to_text(wizard.amount)

    def _get_payment_vals(self):
        res = super(HrExpenseRegisterPaymentWizard, self)._get_payment_vals()
        if self.payment_method_id == self.env.ref('account_check_printing.account_payment_method_check'):
            res.update({
                'check_amount_in_words': self.check_amount_in_words,
                'check_manual_sequencing': self.check_manual_sequencing,
            })
        return res
