from dateutil.relativedelta import relativedelta

from odoo import models, fields, _, api
from odoo.tools.misc import format_date
from odoo.exceptions import ValidationError

from ..lib import pyloan


class AccountLoanComputeWizard(models.TransientModel):
    _name = 'account.loan.compute.wizard'
    _description = 'Loan Compute Wizard'

    loan_id = fields.Many2one(
        comodel_name='account.loan',
        string='Loan',
        required=True,
    )
    currency_id = fields.Many2one(related='loan_id.currency_id')
    loan_amount = fields.Monetary(
        string='Loan Amount',
        required=True,
    )
    interest_rate = fields.Float(
        string='Interest Rate',
        default=1.0,
        required=True,
        digits=(12, 10),
        min_display_digits=2,
    )
    loan_term = fields.Integer(
        string='Loan Term',
        default=1,
        required=True,
    )
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.context_today,
    )
    first_payment_date = fields.Date(
        string='First Payment',
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1) + relativedelta(months=1),  # first day of next month
    )
    payment_end_of_month = fields.Selection(
        string='Payment',
        selection=[
            ('end_of_month', 'End of Month'),
            ('at_anniversary', 'At Anniversary'),
        ],
        default='end_of_month',
        required=True,
    )
    compounding_method = fields.Selection(
        string='Compounding Method',
        selection=[
            ('30A/360', '30A/360'),
            ('30U/360', '30U/360'),
            ('30E/360', '30E/360'),
            ('30E/360 ISDA', '30E/360 ISDA'),
            ('A/360', 'A/360'),
            ('A/365F', 'A/365F'),
            ('A/A ISDA', 'A/A ISDA'),
            ('A/A AFB', 'A/A AFB'),
        ],
        default='30E/360',
        required=True,
    )
    preview = fields.Text(compute='_compute_preview')

    # Onchange
    @api.onchange('loan_amount', 'interest_rate', 'loan_term', 'start_date', 'first_payment_date')
    def _onchange_preview(self):
        if self.loan_amount < 0:
            raise ValidationError(_("Loan Amount must be positive"))
        if self.interest_rate < 0 or self.interest_rate > 100:
            raise ValidationError(_("Interest Rate must be between 0 and 100"))
        if self.loan_term < 0:
            raise ValidationError(_("Loan Term must be positive"))
        if self.first_payment_date and self.start_date and self.start_date + relativedelta(years=self.loan_term) < self.first_payment_date:
            raise ValidationError(_("The First Payment Date must be before the end of the loan."))

    @api.onchange('start_date')
    def _onchange_start_date(self):
        self.first_payment_date = self.start_date and self.start_date.replace(day=1) + relativedelta(months=1)  # first day of next month

    # Compute
    def _get_loan_payment_schedule(self):
        self.ensure_one()
        loan = pyloan.Loan(
            loan_amount=self.loan_amount,
            interest_rate=self.interest_rate,
            loan_term=self.loan_term,
            start_date=format_date(self.env, self.start_date, date_format='yyyy-MM-dd'),
            first_payment_date=format_date(self.env, self.first_payment_date, date_format='yyyy-MM-dd') if self.first_payment_date and self.payment_end_of_month == 'at_anniversary' else None,
            payment_end_of_month=self.payment_end_of_month == 'end_of_month',
            compounding_method=self.compounding_method,
            loan_type='annuity' if self.interest_rate else 'linear',
        )
        if schedule := loan.get_payment_schedule():
            return schedule[1:]  # Skip first line which is always 0 (simply the start of the loan)
        return []

    @api.depends('loan_amount', 'interest_rate', 'loan_term', 'start_date', 'first_payment_date', 'payment_end_of_month', 'compounding_method')
    def _compute_preview(self):
        def get_preview_row(payment):
            return (
                f"{format_date(self.env, payment.date): <12}  "
                f"{wizard.currency_id.format(float(payment.principal_amount)):>15}  "
                f"{wizard.currency_id.format(float(payment.interest_amount)):>15}  "
                f"{wizard.currency_id.format(float(payment.payment_amount)):>15}  "
                f"{wizard.currency_id.format(float(payment.loan_balance_amount)):>15}\n"
            )
        for wizard in self:
            if wizard.loan_amount and wizard.loan_term and wizard.start_date:
                schedule = self._get_loan_payment_schedule()
                if not schedule:
                    wizard.preview = ''
                    continue
                preview = "{: <12}  {:>15}  {:>15}  {:>15}  {:>15}\n".format(_('Date'), _('Principal'), _('Interest'), _('Payment'), _('Balance'))
                for payment in schedule[:5]:
                    preview += get_preview_row(payment)
                preview += "{: <12}  {:>15}  {:>15}  {:>15}  {:>15}\n".format("...", "...", "...", "...", "...")
                for payment in schedule[-5:]:
                    preview += get_preview_row(payment)
                wizard.preview = preview
            else:
                wizard.preview = ''

    # Actions
    def action_save(self):
        loan_lines_values = []
        for payment in self._get_loan_payment_schedule():
            loan_lines_values.append({
                'loan_id': self.loan_id.id,
                'date': payment.date,
                'principal': float(payment.principal_amount),
                'interest': float(payment.interest_amount),
            })
        self.env['account.loan.line'].create(loan_lines_values)
        self.loan_id.write({
            'date': self.start_date,
            'amount_borrowed': self.loan_amount,
            'interest': sum(self.loan_id.line_ids.mapped('interest')),
            'duration': len(self.loan_id.line_ids),
        })
        return {
            'name': self.loan_id.name,
            'res_id': self.loan_id.id,
            'type': 'ir.actions.act_window',
            'res_model': self.loan_id._name,
            'target': 'self',
            'views': [[False, 'form']],
            'context': self.env.context,
        }
