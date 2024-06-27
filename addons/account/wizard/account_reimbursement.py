from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountReimbursement(models.TransientModel):
    _name = 'account.reimbursement'
    _description = 'Reimburse Payment Wizard'
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin']

    payment_id = fields.Many2one('account.payment', readonly=True, default=lambda self: self.env.context.get('active_id'))  # payment to reimburse
    total_amount_to_reimburse = fields.Monetary(currency_field='currency_id', related='payment_id.amount', string="Reimbursed Payment Amount")
    reimbursement_payment_id = fields.Many2one('account.payment')
    reimbursement_date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', help="The payment's currency.")
    company_id = fields.Many2one('res.company', required=True, readonly=True)
    payment_method_id = fields.Many2one(
        related='payment_method_line_id.payment_method_id',
        string="Method",
        tracking=True,
        store=True
    )
    # == Computed fields ==
    already_repaid_amount = fields.Monetary(currency_field='currency_id', store=True, readonly=True, compute='_compute_already_repaid_amount')
    amount = fields.Monetary(currency_field='currency_id', store=True, readonly=False, compute='_compute_amount')
    communication = fields.Char(string='Memo', store=True, compute='_compute_communication')
    payment_type = fields.Char(compute='_compute_payment_type', store=True)
    partner_type = fields.Char(compute='_compute_partner_type', store=True)

    available_journal_ids = fields.Many2many(comodel_name='account.journal', compute='_compute_available_journal_ids')
    journal_id = fields.Many2one(comodel_name='account.journal', compute='_compute_journal_id', readonly=False, store=True, domain="[('id', 'in', available_journal_ids)]")

    available_partner_bank_ids = fields.Many2many(comodel_name='res.partner.bank', compute='_compute_available_partner_bank_ids')
    partner_bank_id = fields.Many2one(comodel_name='res.partner.bank', compute='_compute_partner_bank_id', readonly=False, store=True, domain="[('id', 'in', available_partner_bank_ids)]")

    available_payment_method_line_ids = fields.Many2many('account.payment.method.line', compute='_compute_available_payment_method_line_ids')
    payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method',
                                             domain="[('id', 'in', available_payment_method_line_ids)]",
                                             compute='_compute_payment_method_line_id', store=True, readonly=False,
                                             help="Manual: Pay or Get paid by any method outside of Odoo.\n"
                                                  "Payment Providers: Each payment provider has its own Payment Method. Request a transaction on/to a card thanks to a payment token saved by the partner when buying or subscribing online.\n"
                                                  "Check: Pay bills by check and print it from Odoo.\n"
                                                  "Batch Deposit: Collect several customer checks at once generating and submitting a batch deposit to your bank. Module account_batch_payment is necessary.\n"
                                                  "SEPA Credit Transfer: Pay in the SEPA zone by submitting a SEPA Credit Transfer file to your bank. Module account_sepa is necessary.\n"
                                                  "SEPA Direct Debit: Get paid in the SEPA zone thanks to a mandate your partner will have granted to you. Module account_sepa is necessary.\n")
    reimbursement_message = fields.Char(string="Reimbursement Message", compute='_compute_reimbursement_message')
    partially_repaid_message = fields.Char(string="Partially Repaid Message", compute='_compute_partially_repaid_message')

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------
    @api.model
    def _get_available_payment_method_line_ids(self):
        return self.journal_id._get_available_payment_method_lines(self.payment_type) if self.journal_id else False

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('payment_id')
    def _compute_already_repaid_amount(self):
        reimbursements_ids = self.payment_id.reimbursement_payment_ids
        if reimbursements_ids:
            self.already_repaid_amount = sum(self.payment_id.reimbursement_payment_ids.mapped('amount'))

    @api.depends('payment_id', 'already_repaid_amount')
    def _compute_amount(self):
        payment_to_reimburse = self.payment_id
        if payment_to_reimburse.reimbursement_payment_ids:
            self.amount = payment_to_reimburse.amount - self.already_repaid_amount
        else:
            self.amount = payment_to_reimburse.amount

    @api.depends('payment_id')
    def _compute_available_journal_ids(self):
        journals = self.env['account.journal'].search([('company_id', '=', self.payment_id.company_id.id), ('type', 'in', ('bank', 'cash'))])
        self.available_journal_ids = journals.filtered('inbound_payment_method_line_ids') if self.payment_type == 'inbound' else journals.filtered('outbound_payment_method_line_ids')

    @api.depends('payment_id', 'available_journal_ids')
    def _compute_journal_id(self):
        payment_to_reimburse_id = self.payment_id
        self.journal_id = self.env['account.journal'].search([
            ('type', '=', payment_to_reimburse_id.journal_id.type),
            ('company_id', '=', payment_to_reimburse_id.company_id.id),
            ('id', 'in', self.available_journal_ids.ids)
        ], limit=1)

    @api.depends('payment_id')
    def _compute_available_partner_bank_ids(self):
        payment_id = self.payment_id
        #  TODO discuss this, not sure it should be like this
        self.available_partner_bank_ids = payment_id.move_id.line_ids.partner_id.bank_ids.filtered(lambda bank: bank.company_id.id in (False, payment_id.company_id))._origin

    @api.depends('payment_id')
    def _compute_payment_type(self):
        self.payment_type = 'inbound' if self.payment_id.payment_type == 'outbound' else 'outbound'

    @api.depends('payment_id')
    def _compute_partner_type(self):
        self.partner_type = str(self.payment_id.partner_type)

    @api.depends('payment_id')
    def _compute_communication(self):
        payment_to_reimburse_id = self.payment_id
        self.communication = f'R - {payment_to_reimburse_id.ref or payment_to_reimburse_id.name}'

    @api.depends('payment_type', 'journal_id')
    def _compute_available_payment_method_line_ids(self):
        self.available_payment_method_line_ids = self._get_available_payment_method_line_ids()

    @api.depends('payment_type', 'journal_id')
    def _compute_payment_method_line_id(self):
        available_payment_method_line_ids = self._get_available_payment_method_line_ids()
        self.payment_method_line_id = available_payment_method_line_ids[0]._origin if available_payment_method_line_ids else False

    @api.depends('total_amount_to_reimburse')
    def _compute_reimbursement_message(self):
        self.reimbursement_message = _('The initial payment amount was %s', self.total_amount_to_reimburse)

    @api.depends('total_amount_to_reimburse', 'already_repaid_amount')
    def _compute_partially_repaid_message(self):
        self.partially_repaid_message = _('The initial payment amount was %s among which %s have already been repaid.', self.total_amount_to_reimburse, self.already_repaid_amount)

    # -------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # -------------------------------------------------------------------------
    @api.constrains('amount', 'already_repaid_amount')
    def _check_amount(self):
        """ Ensures that the amount is <= payment to reimburse - already reimbursed amount"""
        if not 0 < self.amount <= self.payment_id.amount - self.already_repaid_amount:
            # TODO maybe store and indicate the maximum amount to pay
            raise ValidationError(_('Reimbursement amount cannot exceed remaining amount to reimburse and must be superior to zero'))

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------
    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        payment_id = self.env['account.payment'].browse(self.env.context['active_id']) if self.env.context.get(
            'active_model') == 'account.payment' else self.env['account.payment']
        if payment_id.state != "posted":
            raise UserError(_('You can only reimburse posted payments.'))
        if 'company_id' in fields:
            res['company_id'] = payment_id.company_id.id or self.env.company.id
        if 'currency_id' in fields:
            res['currency_id'] = payment_id.currency_id

        return res

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def reimburse_payments(self):
        """ Reimburses a payment
        First reverse moves related to the payment to reimburse and link it to the reversal moves
        then create the reimbursement payment and link it to the reimbursed payment
        then return an action window opening the newly created reimbursement payment
        """
        self.ensure_one()
        payment_to_reimburse = self.payment_id

        # create reimbursement payments
        reimbursement_payment_id = self.env['account.payment'].create({
            'date': self.reimbursement_date,
            'amount': self.amount,
            'payment_type': self.payment_type,
            'partner_type': self.partner_type,
            'partner_id': payment_to_reimburse.partner_id.id,
            'ref': self.communication,
            'currency_id': self.currency_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'journal_id': payment_to_reimburse.journal_id.id,
            'company_id': self.company_id.id,
            'reimbursed_payment_id': payment_to_reimburse.id,
        })

        # If fully reimbursed in one reimbursement, post the reimbursement and reconcile both payments if possible.
        if payment_to_reimburse.reimbursements_count == 1 and not payment_to_reimburse.amount_residual and payment_to_reimburse.amount_total == reimbursement_payment_id.amount_total:
            reimbursement_payment_id.action_post()
            payment_to_reimburse_aml_to_reconcile = self.env['account.move.line'].search([('payment_id', '=', payment_to_reimburse.id), ('debit', '=', 0)])
            if not payment_to_reimburse_aml_to_reconcile.reconciled:
                reimbursement_payment_aml_to_reconcile = self.env['account.move.line'].search([('payment_id', '=', reimbursement_payment_id.id), ('credit', '=', 0)])
                reconciliation_batch = self.env['account.move.line'].browse([payment_to_reimburse_aml_to_reconcile.id, reimbursement_payment_aml_to_reconcile.id])
                self.env['account.move.line']._reconcile_plan([reconciliation_batch])

        # Create and return action
        return {
            'name': _('Reimburse Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'res_id': reimbursement_payment_id.id,
        }
