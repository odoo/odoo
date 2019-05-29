# -*- coding: utf-8 -*-

from odoo import api, exceptions, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons import decimal_precision as dp

from dateutil.relativedelta import relativedelta


class AccountPaymentTerm(models.Model):
    _name = "account.payment.term"
    _description = "Payment Terms"
    _order = "sequence, id"

    def _default_line_ids(self):
        return [(0, 0, {'value': 'balance', 'value_amount': 0.0, 'sequence': 9, 'days': 0, 'option': 'day_after_invoice_date'})]

    name = fields.Char(string='Payment Terms', translate=True, required=True)
    active = fields.Boolean(default=True, help="If the active field is set to False, it will allow you to hide the payment terms without removing it.")
    note = fields.Text(string='Description on the Invoice', translate=True)
    line_ids = fields.One2many('account.payment.term.line', 'payment_id', string='Terms', copy=True, default=_default_line_ids)
    company_id = fields.Many2one('res.company', string='Company')
    sequence = fields.Integer(required=True, default=10)

    @api.constrains('line_ids')
    def _check_lines(self):
        for terms in self:
            payment_term_lines = terms.line_ids.sorted()
            if payment_term_lines and payment_term_lines[-1].value != 'balance':
                raise ValidationError(_('The last line of a Payment Term should have the Balance type.'))
            lines = terms.line_ids.filtered(lambda r: r.value == 'balance')
            if len(lines) > 1:
                raise ValidationError(_('A Payment Term should have only one line of type Balance.'))

    @api.multi
    def compute(self, value, date_ref=False, currency=None):
        self.ensure_one()
        date_ref = date_ref or fields.Date.today()
        amount = value
        sign = value < 0 and -1 or 1
        result = []
        if not currency and self.env.context.get('currency_id'):
            currency = self.env['res.currency'].browse(self.env.context['currency_id'])
        elif not currency:
            currency = self.env.company.currency_id
        for line in self.line_ids:
            if line.value == 'fixed':
                amt = sign * currency.round(line.value_amount)
            elif line.value == 'percent':
                amt = currency.round(value * (line.value_amount / 100.0))
            elif line.value == 'balance':
                amt = currency.round(amount)
            next_date = fields.Date.from_string(date_ref)
            if line.option == 'day_after_invoice_date':
                next_date += relativedelta(days=line.days)
                if line.day_of_the_month > 0:
                    months_delta = (line.day_of_the_month < next_date.day) and 1 or 0
                    next_date += relativedelta(day=line.day_of_the_month, months=months_delta)
            elif line.option == 'day_following_month':
                next_date += relativedelta(day=line.days, months=1)
            elif line.option == 'day_current_month':
                next_date += relativedelta(day=line.days, months=0)
            result.append((fields.Date.to_string(next_date), amt))
            amount -= amt
        amount = sum(amt for _, amt in result)
        dist = currency.round(value - amount)
        if dist:
            last_date = result and result[-1][0] or fields.Date.today()
            result.append((last_date, dist))
        return result

    @api.multi
    def unlink(self):
        for terms in self:
            if self.env['account.move'].search([('payment_term_id', 'in', terms.ids)]):
                raise UserError(_('You can not delete payment terms as other records still reference it. However, you can archive it.'))
            property_recs = self.env['ir.property'].search([('value_reference', 'in', ['account.payment.term,%s'%payment_term.id for payment_term in terms])])
            property_recs.unlink()
        return super(AccountPaymentTerm, self).unlink()


class AccountPaymentTermLine(models.Model):
    _name = "account.payment.term.line"
    _description = "Payment Terms Line"
    _order = "sequence, id"

    value = fields.Selection([
            ('balance', 'Balance'),
            ('percent', 'Percent'),
            ('fixed', 'Fixed Amount')
        ], string='Type', required=True, default='balance',
        help="Select here the kind of valuation related to this payment terms line.")
    value_amount = fields.Float(string='Value', digits=dp.get_precision('Payment Terms'), help="For percent enter a ratio between 0-100.")
    days = fields.Integer(string='Number of Days', required=True, default=0)
    day_of_the_month = fields.Integer(string='Day of the month', help="Day of the month on which the invoice must come to its term. If zero or negative, this value will be ignored, and no specific day will be set. If greater than the last day of a month, this number will instead select the last day of this month.")
    option = fields.Selection([
            ('day_after_invoice_date', "day(s) after the invoice date"),
            ('day_following_month', "of the following month"),
            ('day_current_month', "of the current month"),
        ],
        default='day_after_invoice_date', required=True, string='Options'
        )
    payment_id = fields.Many2one('account.payment.term', string='Payment Terms', required=True, index=True, ondelete='cascade')
    sequence = fields.Integer(default=10, help="Gives the sequence order when displaying a list of payment terms lines.")

    @api.constrains('value', 'value_amount')
    def _check_percent(self):
        for term_line in self:
            if term_line.value == 'percent' and (term_line.value_amount < 0.0 or term_line.value_amount > 100.0):
                raise ValidationError(_('Percentages on the Payment Terms lines must be between 0 and 100.'))

    @api.constrains('days')
    def _check_days(self):
        for term_line in self:
            if term_line.option in ('day_following_month', 'day_current_month') and term_line.days <= 0:
                raise ValidationError(_("The day of the month used for this term must be stricly positive."))
            elif term_line.days < 0:
                raise ValidationError(_("The number of days used for a payment term cannot be negative."))

    @api.onchange('option')
    def _onchange_option(self):
        if self.option in ('day_current_month', 'day_following_month'):
            self.days = 0
