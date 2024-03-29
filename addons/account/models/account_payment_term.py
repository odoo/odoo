# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_date, formatLang, frozendict, date_utils
from odoo.tools.float_utils import float_round

from dateutil.relativedelta import relativedelta


class AccountPaymentTerm(models.Model):
    _name = "account.payment.term"
    _description = "Payment Terms"
    _order = "sequence, id"

    def _default_line_ids(self):
        return [Command.create({'value': 'percent', 'value_amount': 100.0, 'nb_days': 0})]

    def _default_example_date(self):
        return self._context.get('example_date') or fields.Date.today()

    name = fields.Char(string='Payment Terms', translate=True, required=True)
    active = fields.Boolean(default=True, help="If the active field is set to False, it will allow you to hide the payment terms without removing it.")
    note = fields.Html(string='Description on the Invoice', translate=True)
    line_ids = fields.One2many('account.payment.term.line', 'payment_id', string='Terms', copy=True, default=_default_line_ids)
    company_id = fields.Many2one('res.company', string='Company')
    fiscal_country_codes = fields.Char(compute='_compute_fiscal_country_codes')
    sequence = fields.Integer(required=True, default=10)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, store=True)

    display_on_invoice = fields.Boolean(string='Show installment dates', default=True)
    example_amount = fields.Monetary(currency_field='currency_id', default=1000, store=False, readonly=True)
    example_date = fields.Date(string='Date example', default=_default_example_date, store=False)
    example_invalid = fields.Boolean(compute='_compute_example_invalid')
    example_preview = fields.Html(compute='_compute_example_preview')
    example_preview_discount = fields.Html(compute='_compute_example_preview')

    discount_percentage = fields.Float(string='Discount %', help='Early Payment Discount granted for this payment term', default=2.0)
    discount_days = fields.Integer(string='Discount Days', help='Number of days before the early payment proposition expires', default=10)
    early_pay_discount_computation = fields.Selection([
        ('included', 'On early payment'),
        ('excluded', 'Never'),
        ('mixed', 'Always (upon invoice)'),
    ], string='Cash Discount Tax Reduction', readonly=False, store=True, compute='_compute_discount_computation')
    early_discount = fields.Boolean(string='Early Discount')

    @api.depends('company_id')
    @api.depends_context('allowed_company_ids')
    def _compute_fiscal_country_codes(self):
        for record in self:
            allowed_companies = record.company_id or self.env.companies
            record.fiscal_country_codes = ",".join(allowed_companies.mapped('account_fiscal_country_id.code'))

    def _get_amount_due_after_discount(self, total_amount, untaxed_amount):
        self.ensure_one()
        if self.early_discount:
            percentage = self.discount_percentage / 100.0
            if self.early_pay_discount_computation in ('excluded', 'mixed'):
                discount_amount_currency = self.currency_id.round((total_amount - untaxed_amount) * percentage)
            else:
                discount_amount_currency = self.currency_id.round(total_amount - (total_amount * (1 - (percentage))))
            return total_amount - discount_amount_currency
        return total_amount

    @api.depends('company_id')
    def _compute_discount_computation(self):
        for pay_term in self:
            country_code = pay_term.company_id.country_code or self.env.company.country_code
            if country_code == 'BE':
                pay_term.early_pay_discount_computation = 'mixed'
            elif country_code == 'NL':
                pay_term.early_pay_discount_computation = 'excluded'
            else:
                pay_term.early_pay_discount_computation = 'included'

    @api.depends('line_ids')
    def _compute_example_invalid(self):
        for payment_term in self:
            payment_term.example_invalid = len(payment_term.line_ids) <= 1

    @api.depends('currency_id', 'example_amount', 'example_date', 'line_ids.value', 'line_ids.value_amount', 'line_ids.nb_days', 'early_discount', 'discount_percentage', 'discount_days')
    def _compute_example_preview(self):
        for record in self:
            example_preview = ""
            record.example_preview_discount = ""
            currency = record.currency_id
            if record.early_discount:
                date = record._get_last_discount_date_formatted(record.example_date or fields.Date.context_today(record))
                discount_amount = record._get_amount_due_after_discount(record.example_amount, 0.0)
                record.example_preview_discount = _(
                    "Early Payment Discount: <b>%(amount)s</b> if paid before <b>%(date)s</b>",
                    amount=formatLang(self.env, discount_amount, monetary=True, currency_obj=currency),
                    date=date,
                )

            if not record.example_invalid:
                terms = record._compute_terms(
                    date_ref=record.example_date or fields.Date.context_today(record),
                    currency=currency,
                    company=self.env.company,
                    tax_amount=0,
                    tax_amount_currency=0,
                    untaxed_amount=record.example_amount,
                    untaxed_amount_currency=record.example_amount,
                    sign=1)
                for i, info_by_dates in enumerate(record._get_amount_by_date(terms).values()):
                    date = info_by_dates['date']
                    amount = info_by_dates['amount']
                    example_preview += "<div>"
                    example_preview += _(
                        "<b>%(count)s#</b> Installment of <b>%(amount)s</b> due on <b style='color: #704A66;'>%(date)s</b>",
                        count=i+1,
                        amount=formatLang(self.env, amount, monetary=True, currency_obj=currency),
                        date=date,
                    )
                    example_preview += "</div>"

            record.example_preview = example_preview

    @api.model
    def _get_amount_by_date(self, terms):
        """
        Returns a dictionary with the amount for each date of the payment term
        (grouped by date, discounted percentage and discount last date,
        sorted by date and ignoring null amounts).
        """
        terms_lines = sorted(terms["line_ids"], key=lambda t: t.get('date'))
        amount_by_date = {}
        for term in terms_lines:
            key = frozendict({
                'date': term['date'],
            })
            results = amount_by_date.setdefault(key, {
                'date': format_date(self.env, term['date']),
                'amount': 0.0,
            })
            results['amount'] += term['foreign_amount']
        return amount_by_date

    @api.constrains('line_ids')
    def _check_lines(self):
        round_precision = self.env['decimal.precision'].precision_get('Payment Terms')
        for terms in self:
            total_percent = sum(line.value_amount for line in terms.line_ids if line.value == 'percent')
            if float_round(total_percent, precision_digits=round_precision) != 100:
                raise ValidationError(_('The Payment Term must have at least one percent line and the sum of the percent must be 100%.'))
            if len(terms.line_ids) > 1 and terms.early_discount:
                raise ValidationError(
                    _("The Early Payment Discount functionality can only be used with payment terms using a single 100% line. "))
            if terms.early_discount and terms.discount_percentage <= 0.0:
                raise ValidationError(_("The Early Payment Discount must be strictly positive."))
            if terms.early_discount and terms.discount_days <= 0:
                raise ValidationError(_("The Early Payment Discount days must be strictly positive."))

    def _compute_terms(self, date_ref, currency, company, tax_amount, tax_amount_currency, sign, untaxed_amount, untaxed_amount_currency):
        """Get the distribution of this payment term.
        :param date_ref: The move date to take into account
        :param currency: the move's currency
        :param company: the company issuing the move
        :param tax_amount: the signed tax amount for the move
        :param tax_amount_currency: the signed tax amount for the move in the move's currency
        :param untaxed_amount: the signed untaxed amount for the move
        :param untaxed_amount_currency: the signed untaxed amount for the move in the move's currency
        :param sign: the sign of the move
        :return (list<tuple<datetime.date,tuple<float,float>>>): the amount in the company's currency and
            the document's currency, respectively for each required payment date
        """
        self.ensure_one()
        company_currency = company.currency_id
        total_amount = tax_amount + untaxed_amount
        total_amount_currency = tax_amount_currency + untaxed_amount_currency

        pay_term = {
            'total_amount': total_amount,
            'discount_percentage': self.discount_percentage if self.early_discount else 0.0,
            'discount_date': date_ref + relativedelta(days=(self.discount_days or 0)) if self.early_discount else False,
            'discount_balance': 0,
            'line_ids': [],
        }

        if self.early_discount:
            # Early discount is only available on single line, 100% payment terms.
            discount_percentage = self.discount_percentage / 100.0
            if self.early_pay_discount_computation in ('excluded', 'mixed'):
                pay_term['discount_balance'] = company_currency.round(total_amount - untaxed_amount * discount_percentage)
                pay_term['discount_amount_currency'] = currency.round(total_amount_currency - untaxed_amount_currency * discount_percentage)
            else:
                pay_term['discount_balance'] = company_currency.round(total_amount * (1 - discount_percentage))
                pay_term['discount_amount_currency'] = currency.round(total_amount_currency * (1 - discount_percentage))

        rate = abs(total_amount_currency / total_amount) if total_amount else 0.0
        residual_amount = total_amount
        residual_amount_currency = total_amount_currency

        for i, line in enumerate(self.line_ids):
            term_vals = {
                'date': line._get_due_date(date_ref),
                'company_amount': 0,
                'foreign_amount': 0,
            }

            if i == len(self.line_ids) - 1:
                # The last line is always the balance, no matter the type
                term_vals['company_amount'] = residual_amount
                term_vals['foreign_amount'] = residual_amount_currency
            elif line.value == 'fixed':
                # Fixed amounts
                term_vals['company_amount'] = sign * company_currency.round(line.value_amount / rate) if rate else 0.0
                term_vals['foreign_amount'] = sign * currency.round(line.value_amount)
            else:
                # Percentage amounts
                line_amount = company_currency.round(total_amount * (line.value_amount / 100.0))
                line_amount_currency = currency.round(total_amount_currency * (line.value_amount / 100.0))
                term_vals['company_amount'] = line_amount
                term_vals['foreign_amount'] = line_amount_currency

            residual_amount -= term_vals['company_amount']
            residual_amount_currency -= term_vals['foreign_amount']
            pay_term['line_ids'].append(term_vals)

        return pay_term

    @api.ondelete(at_uninstall=False)
    def _unlink_except_referenced_terms(self):
        if self.env['account.move'].search([('invoice_payment_term_id', 'in', self.ids)]):
            raise UserError(_('You can not delete payment terms as other records still reference it. However, you can archive it.'))

    def unlink(self):
        for terms in self:
            self.env['ir.property'].sudo().search(
                [('value_reference', 'in', ['account.payment.term,%s'%payment_term.id for payment_term in terms])]
            ).unlink()
        return super(AccountPaymentTerm, self).unlink()

    def _get_last_discount_date(self, date_ref):
        self.ensure_one()
        return date_ref + relativedelta(days=self.discount_days or 0) if self.early_discount else False

    def _get_last_discount_date_formatted(self, date_ref):
        self.ensure_one()
        if not date_ref:
            return None
        return format_date(self.env, self._get_last_discount_date(date_ref))

class AccountPaymentTermLine(models.Model):
    _name = "account.payment.term.line"
    _description = "Payment Terms Line"
    _order = "id"

    value = fields.Selection([
            ('percent', 'Percent'),
            ('fixed', 'Fixed')
        ], required=True, default='percent',
        help="Select here the kind of valuation related to this payment terms line.")
    value_amount = fields.Float(string='Due', digits='Payment Terms',
                                help="For percent enter a ratio between 0-100.",
                                compute='_compute_value_amount', store=True, readonly=False)
    delay_type = fields.Selection([
            ('days_after', 'Days after invoice date'),
            ('days_after_end_of_month', 'Days after end of month'),
            ('days_after_end_of_next_month', 'Days after end of next month'),
        ], required=True, default='days_after')
    nb_days = fields.Integer(string='Days', readonly=False, store=True, compute='_compute_days')
    payment_id = fields.Many2one('account.payment.term', string='Payment Terms', required=True, index=True, ondelete='cascade')

    def _get_due_date(self, date_ref):
        self.ensure_one()
        due_date = fields.Date.from_string(date_ref) or fields.Date.today()
        if self.delay_type == 'days_after_end_of_month':
            return date_utils.end_of(due_date, 'month') + relativedelta(days=self.nb_days)
        elif self.delay_type == 'days_after_end_of_next_month':
            return date_utils.end_of(due_date + relativedelta(months=1), 'month') + relativedelta(days=self.nb_days)
        return due_date + relativedelta(days=self.nb_days)

    @api.constrains('value', 'value_amount')
    def _check_percent(self):
        for term_line in self:
            if term_line.value == 'percent' and (term_line.value_amount < 0.0 or term_line.value_amount > 100.0):
                raise ValidationError(_('Percentages on the Payment Terms lines must be between 0 and 100.'))

    @api.depends('payment_id')
    def _compute_days(self):
        for line in self:
            #Line.payment_id.line_ids[-1] is the new line that has been just added when clicking "add a new line"
            if not line.nb_days and len(line.payment_id.line_ids) > 1:
                line.nb_days = line.payment_id.line_ids[-2].nb_days + 30
            else:
                line.nb_days = line.nb_days

    @api.depends('payment_id')
    def _compute_value_amount(self):
        for line in self:
            if line.value == 'fixed':
                line.value_amount = 0
            else:
                amount = 0
                for i in line.payment_id.line_ids.filtered(lambda r: r.value == 'percent'):
                    amount += i['value_amount']
                line.value_amount = 100 - amount
