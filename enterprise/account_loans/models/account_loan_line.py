from odoo import fields, models, api


class AccountLoanLine(models.Model):
    _name = 'account.loan.line'
    _description = 'Loan Line'
    _order = 'date, id'

    sequence = fields.Integer("#", compute='_compute_sequence')
    loan_id = fields.Many2one('account.loan', string='Loan', required=True, ondelete="cascade", index=True)
    loan_name = fields.Char(related='loan_id.name')
    loan_state = fields.Selection(related='loan_id.state')
    loan_date = fields.Date(related='loan_id.date')
    loan_asset_group_id = fields.Many2one(related='loan_id.asset_group_id')
    active = fields.Boolean(related='loan_id.active')
    company_id = fields.Many2one(related='loan_id.company_id')
    currency_id = fields.Many2one(related='company_id.currency_id')
    date = fields.Date('Date', required=True)
    principal = fields.Monetary(string='Principal')
    interest = fields.Monetary(string='Interest')
    payment = fields.Monetary(
        string='Payment',
        compute='_compute_payment',
        store=True,  # stored for pivot view
    )
    outstanding_balance = fields.Monetary(
        string='Outstanding Balance',
        compute='_compute_outstanding_balance',
    )  # theoretical outstanding balance at the date of the line
    long_term_theoretical_balance = fields.Monetary(
        string='Long-Term',
        compute='_compute_theoretical_balances',
        store=True,  # stored for pivot view
    )
    short_term_theoretical_balance = fields.Monetary(
        string='Short-Term',
        compute='_compute_theoretical_balances',
        store=True,  # stored for pivot view
    )
    generated_move_ids = fields.One2many(
        comodel_name='account.move',
        inverse_name='generating_loan_line_id',
        string='Generated Entries',
        readonly=True,
        copy=False,
        help="Entries that we generated from this loan line"
    )
    is_payment_move_posted = fields.Boolean(compute='_compute_is_payment_move_posted')

    @api.depends('principal', 'interest')
    def _compute_payment(self):
        for line in self:
            line.payment = line.principal + line.interest

    @api.depends('loan_id.line_ids', 'loan_id.amount_borrowed', 'principal')
    def _compute_outstanding_balance(self):
        for line in self:
            line.outstanding_balance = line.loan_id.amount_borrowed - sum(line.loan_id.line_ids.filtered(lambda l: line.date and l.date <= line.date).mapped('principal'))

    @api.depends('principal', 'date', 'loan_id.line_ids.date', 'loan_id.line_ids.principal')
    def _compute_theoretical_balances(self):
        for line in self:
            filtered_lines = line.loan_id.line_ids.filtered(lambda l: line.date and l.date and l.date > line.date)
            line.long_term_theoretical_balance = sum(filtered_lines[12:].mapped('principal'))
            line.short_term_theoretical_balance = sum(filtered_lines[:12].mapped('principal'))

    @api.depends('loan_id.line_ids', 'date')
    def _compute_sequence(self):
        for line in self.sorted('date'):
            line.sequence = len(line.loan_id.line_ids.filtered(lambda l: line.date and l.date <= line.date))

    @api.depends('generated_move_ids.state')
    def _compute_is_payment_move_posted(self):
        for line in self:
            generated_moves = line.generated_move_ids.filtered(lambda m: m.is_loan_payment_move)
            # In case of audit trail being activated, we can have more than 1 generated move (i.e. after loan closing/cancellation and re-confirmation),
            # so we take the one that has no reversal move.
            if len(generated_moves) > 1 and any(m.reversal_move_ids for m in generated_moves):
                generated_moves = generated_moves.filtered(lambda m: not m.reversal_move_ids)
            line.is_payment_move_posted = any(m.state == 'posted' for m in generated_moves)
