# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ExpenseSampleRegister(models.TransientModel):
    _name = 'expense.sample.register'
    _description = 'Register Sample Payments'

    sheet_id = fields.Many2one('hr.expense.sheet', string='Expense')
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    memo = fields.Char(string='Memo')
    currency_id = fields.Many2one(related='sheet_id.currency_id')
    company_id = fields.Many2one(related='sheet_id.company_id')

    journal_id = fields.Many2one('account.journal', string='Journal',
        check_company=True,
        domain="[('type', 'in', ('bank', 'cash'))]",
        compute='_compute_journal', readonly=False, store=True)
    payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method',
        readonly=False, store=True,
        compute='_compute_journal',
        domain="[('id', 'in', available_payment_method_line_ids)]",
        help="Manual: Pay or Get paid by any method outside of Odoo.\n"
        "Payment Providers: Each payment provider has its own Payment Method. Request a transaction on/to a card thanks to a payment token saved by the partner when buying or subscribing online.\n"
        "Check: Pay bills by check and print it from Odoo.\n"
        "Batch Deposit: Collect several customer checks at once generating and submitting a batch deposit to your bank. Module account_batch_payment is necessary.\n"
        "SEPA Credit Transfer: Pay in the SEPA zone by submitting a SEPA Credit Transfer file to your bank. Module account_sepa is necessary.\n"
        "SEPA Direct Debit: Get paid in the SEPA zone thanks to a mandate your partner will have granted to you. Module account_sepa is necessary.\n")
    available_payment_method_line_ids = fields.Many2many('account.payment.method.line', compute='_compute_payment_method_line_fields')
    hide_payment_method_line = fields.Boolean(compute='_compute_payment_method_line_fields')
    date = fields.Date(string='Payment Date', required=True, default=lambda self: fields.Date.context_today(self))
    hide_partial = fields.Boolean(compute='_compute_partial')
    partial_mode = fields.Selection([
        ('open', 'Keep open'),
        ('paid', 'Mark as fully paid')
    ], string='Payment Difference', default='open')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'sheet_id' in fields_list:
            res['sheet_id'] = self.env.context.get('active_id')
            sheet_id = self.env['hr.expense.sheet'].browse(res['sheet_id'])

            if 'amount' in fields_list:
                res['amount'] = sheet_id.total_amount
            if 'memo' in fields_list:
                res['memo'] = sheet_id.name
        return res

    @api.depends('journal_id.outbound_payment_method_line_ids')
    def _compute_payment_method_line_fields(self):
        for wizard in self:
            wizard.available_payment_method_line_ids = wizard.journal_id.outbound_payment_method_line_ids

            if wizard.payment_method_line_id.id not in wizard.available_payment_method_line_ids.ids:
                # In some cases, we could be linked to a payment method line that has been unlinked from the journal.
                # In such cases, we want to show it on the payment.
                wizard.hide_payment_method_line = False
            else:
                wizard.hide_payment_method_line = len(wizard.available_payment_method_line_ids) == 1 and wizard.available_payment_method_line_ids.code == 'manual'

    @api.depends('company_id')
    def _compute_journal(self):
        for wizard in self:
            wizard.journal_id = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(wizard.company_id),
                ('type', 'in', ('bank', 'cash')),
            ], limit=1)
            wizard.payment_method_line_id = wizard.journal_id.outbound_payment_method_line_ids[0]._origin

    @api.depends('amount')
    def _compute_partial(self):
        for wizard in self:
            wizard.hide_partial = wizard.amount == wizard.sheet_id.total_amount

    def action_create_payments(self):
        self.ensure_one()
        if self.amount == self.sheet_id.total_amount or self.partial_mode == 'paid':
            self.sheet_id.set_to_paid()
