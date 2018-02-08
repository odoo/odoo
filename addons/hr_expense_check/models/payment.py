# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrExpenseRegisterPaymentWizard(models.TransientModel):
    _inherit = "hr.expense.sheet.register.payment.wizard"

    check_amount_in_words = fields.Char(string="Amount in Words")
    check_manual_sequencing = fields.Boolean(related='journal_id.check_manual_sequencing')
    # Note: a check_number == 0 means that it will be attributed when the check is printed
    check_number = fields.Integer(string="Check Number", readonly=True, copy=False, default=0,
        help="Number of the check corresponding to this payment. If your pre-printed check are not already numbered, "
             "you can manage the numbering in the journal configuration page.")
    payment_method_code_2 = fields.Char(related='payment_method_id.code',
                                      help="Technical field used to adapt the interface to the payment type selected.",
                                      string="Payment Method Code 2",
                                      readonly=True)

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if hasattr(super(HrExpenseRegisterPaymentWizard, self), '_onchange_journal_id'):
            super(HrExpenseRegisterPaymentWizard, self)._onchange_journal_id()
        if self.journal_id.check_manual_sequencing:
            self.check_number = self.journal_id.check_sequence_id.number_next_actual

    @api.onchange('amount')
    def _onchange_amount(self):
        if hasattr(super(HrExpenseRegisterPaymentWizard, self), '_onchange_amount'):
            super(HrExpenseRegisterPaymentWizard, self)._onchange_amount()
        self.check_amount_in_words = self.currency_id.amount_to_text(self.amount)

    def _get_payment_vals(self):
        res = super(HrExpenseRegisterPaymentWizard, self)._get_payment_vals()
        if self.payment_method_id == self.env.ref('account_check_printing.account_payment_method_check'):
            res.update({
                'check_amount_in_words': self.check_amount_in_words,
                'check_manual_sequencing': self.check_manual_sequencing,
            })
        return res
