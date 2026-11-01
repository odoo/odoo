# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


WHT_TYPE_SELECTION = [
    ('1', 'WHT 1% / ภาษีหัก ณ ที่จ่าย 1%'),
    ('2', 'WHT 2% / ภาษีหัก ณ ที่จ่าย 2%'),
    ('3', 'WHT 3% / ภาษีหัก ณ ที่จ่าย 3%'),
    ('5', 'WHT 5% / ภาษีหัก ณ ที่จ่าย 5%'),
]


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    od19_is_expense_payment = fields.Boolean(
        string='Expense Payment / การชำระค่าใช้จ่าย',
        default=lambda self: self._default_is_expense_payment(),
        help='Indicates this payment is related to an expense reimbursement.',
    )
    od19_wht_type = fields.Selection(
        WHT_TYPE_SELECTION,
        string='WHT Type / ประเภทภาษีหัก',
        help='Withholding tax type applied to this expense payment.',
    )
    od19_wht_base_amount = fields.Monetary(
        string='WHT Base Amount / มูลค่าคิดภาษี',
        currency_field='currency_id',
        help='Base amount used to compute the withholding tax.',
    )
    od19_wht_amount = fields.Monetary(
        string='WHT Amount / จำนวนภาษีหัก',
        currency_field='currency_id',
        compute='_compute_od19_wht_amount',
        store=True,
        readonly=True,
        help='Computed withholding tax amount.',
    )
    od19_wht_expense_account_id = fields.Many2one(
        'account.account',
        string='WHT Expense Account / บัญชีค่าใช้จ่ายภาษีหัก',
        domain="[('account_type', 'in', ('expense', 'expense_direct_cost'))]",
        help='Account to debit the withholding tax expense.',
    )
    od19_wht_payable_account_id = fields.Many2one(
        'account.account',
        string='WHT Payable Account / บัญชีภาษีหักต้องชำระ',
        domain="[('account_type', '=', 'liability')]",
        help='Account to credit the withholding tax payable.',
    )
    od19_wht_move_id = fields.Many2one(
        'account.move',
        string='WHT Journal Entry / ผังรายการภาษีหัก',
        readonly=True,
        copy=False,
    )

    @api.model
    def _default_is_expense_payment(self):
        """Default True when the payment is opened from an expense."""
        active_model = self.env.context.get('active_model')
        if active_model == 'hr.expense':
            return True
        # Also treat as expense payment when partner is an employee
        default_partner_id = self.env.context.get('default_partner_id')
        if default_partner_id:
            partner = self.env['res.partner'].browse(default_partner_id)
            if partner and self.env['hr.employee'].search(
                [('work_contact_id', '=', partner.id)], limit=1
            ):
                return True
        return False

    @api.depends('od19_wht_type', 'od19_wht_base_amount')
    def _compute_od19_wht_amount(self):
        for payment in self:
            if payment.od19_wht_type and payment.od19_wht_base_amount:
                try:
                    rate = float(payment.od19_wht_type)
                except (ValueError, TypeError):
                    rate = 0.0
                payment.od19_wht_amount = payment.od19_wht_base_amount * rate / 100.0
            else:
                payment.od19_wht_amount = 0.0

    @api.constrains('od19_wht_base_amount', 'od19_wht_amount')
    def _check_od19_wht_amounts(self):
        for payment in self:
            if payment.od19_wht_base_amount < 0:
                raise ValidationError(_('WHT base amount cannot be negative.'))

    def action_post(self):
        """Create WHT journal entry when posting an expense payment with WHT."""
        res = super().action_post()
        for payment in self:
            if (
                payment.od19_is_expense_payment
                and payment.od19_wht_type
                and payment.od19_wht_amount
                and not payment.od19_wht_move_id
            ):
                payment._create_od19_wht_move()
                payment._od19_reconcile_wht_lines()
        return res

    def _od19_reconcile_wht_lines(self):
        """Settle the payable left open by a WHT bearing expense payment.

        The withholding tax reduces what the supplier/employee really
        receives, so the payable booked by the source document must be
        matched with the payment entry and - when the WHT is booked on the
        payable account itself - with the WHT journal entry as well. The
        match is delegated to the central helper
        ``account.move._od19_reconcile_account_lines`` (the same helper the
        expense return-cash wizard uses), which works account by account
        because Odoo only reconciles journal items sharing one account.
        """
        for payment in self.filtered("od19_wht_move_id"):
            lines = (
                payment.move_id.line_ids + payment.od19_wht_move_id.line_ids
            ).filtered_domain([
                ("parent_state", "=", "posted"),
                ("reconciled", "=", False),
                ("account_type", "in", ("liability_payable", "asset_receivable")),
            ])
            for account in lines.account_id:
                payment.move_id._od19_reconcile_account_lines(
                    account.id, payment.partner_id.id
                )
        return True

    def _create_od19_wht_move(self):
        """Create the WHT journal entry: debit WHT expense, credit WHT payable."""
        self.ensure_one()
        if not self.od19_wht_expense_account_id:
            raise UserError(_(
                'Please configure the WHT Expense Account before posting.'
            ))
        if not self.od19_wht_payable_account_id:
            raise UserError(_(
                'Please configure the WHT Payable Account before posting.'
            ))

        company_currency = self.company_id.currency_id
        wht_amount = self.od19_wht_amount
        wht_balance = self.currency_id._convert(
            wht_amount, company_currency, self.company_id, self.date
        )

        move_vals = {
            'date': self.date,
            'journal_id': self.journal_id.id,
            'ref': _('WHT for Expense Payment: %s') % self.name,
            'line_ids': [
                (0, 0, {
                    'name': _('WHT Expense - %s') % self.name,
                    'account_id': self.od19_wht_expense_account_id.id,
                    'partner_id': self.partner_id.id,
                    'currency_id': self.currency_id.id,
                    'amount_currency': wht_amount,
                    'debit': wht_balance if wht_balance > 0 else 0.0,
                    'credit': -wht_balance if wht_balance < 0 else 0.0,
                    'date_maturity': self.date,
                }),
                (0, 0, {
                    'name': _('WHT Payable - %s') % self.name,
                    'account_id': self.od19_wht_payable_account_id.id,
                    'partner_id': self.partner_id.id,
                    'currency_id': self.currency_id.id,
                    'amount_currency': -wht_amount,
                    'debit': -wht_balance if wht_balance < 0 else 0.0,
                    'credit': wht_balance if wht_balance > 0 else 0.0,
                    'date_maturity': self.date,
                }),
            ],
        }
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        self.od19_wht_move_id = move
        return move
