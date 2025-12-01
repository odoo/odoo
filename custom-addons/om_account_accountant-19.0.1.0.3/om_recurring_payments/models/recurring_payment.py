from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RecurringPayment(models.Model):
    _name = 'recurring.payment'
    _description = 'Recurring Payment('
    _rec_name = 'name'

    name = fields.Char('Name', readonly=True)
    partner_id = fields.Many2one('res.partner', string="Partner", required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')
    amount = fields.Monetary(string="Amount", currency_field='currency_id')
    journal_id = fields.Many2one('account.journal', 'Journal',
                                 related='template_id.journal_id', readonly=False, required=True)
    payment_type = fields.Selection([
        ('outbound', 'Send Money'),
        ('inbound', 'Receive Money'),
    ], string='Payment Type', required=True, default='inbound')
    state = fields.Selection(selection=[('draft', 'Draft'),
                                        ('done', 'Done')], default='draft', string='Status')
    date_begin = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)
    template_id = fields.Many2one('account.recurring.template', 'Recurring Template',
                                  domain=[('state', '=', 'done')],required=True)
    recurring_period = fields.Selection(related='template_id.recurring_period')
    recurring_interval = fields.Integer('Recurring Interval', required=True,
                                        related='template_id.recurring_interval', readonly=True)
    journal_state = fields.Selection(required=True, string='Generate Journal As',
                                     related='template_id.journal_state')

    description = fields.Text('Description')
    line_ids = fields.One2many('recurring.payment.line', 'recurring_payment_id', string='Recurring Lines')

    def compute_next_date(self, date):
        period = self.recurring_period
        interval = self.recurring_interval
        if period == 'days':
            date += relativedelta(days=interval)
        elif period == 'weeks':
            date += relativedelta(weeks=interval)
        elif period == 'months':
            date += relativedelta(months=interval)
        else:
            date += relativedelta(years=interval)
        return date

    def action_create_lines(self, date):
        ids = self.env['recurring.payment.line']
        vals = {
            'partner_id': self.partner_id.id,
            'amount': self.amount,
            'date': date,
            'recurring_payment_id': self.id,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id.id,
            'state': 'draft'
        }
        ids.create(vals)

    def action_done(self):
        date_begin = self.date_begin
        while date_begin < self.date_end:
            date = date_begin
            self.action_create_lines(date)
            date_begin = self.compute_next_date(date)
        self.state = 'done'

    def action_draft(self):
        if self.line_ids.filtered(lambda t: t.state == 'done'):
            raise ValidationError(_('You cannot Set to Draft as one of the line is already in done state'))
        else:
            for line in self.line_ids:
                line.unlink()
            self.state = 'draft'

    def action_generate_payment(self):
        line_ids = self.env['recurring.payment.line'].search([('date', '<=', date.today()),
                                                                       ('state', '!=', 'done')])
        for line in line_ids:
            line.action_create_payment()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'recurring.payment') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('recurring.payment') or _('New')
        return super(RecurringPayment, self).create(vals)

    @api.constrains('amount')
    def _check_amount(self):
        if self.amount <= 0:
            raise ValidationError(_('Amount Must Be Non-Zero Positive Number'))

    def unlink(self):
        for rec in self:
            if rec.state == 'done':
                raise ValidationError(_('Cannot delete done records !'))
        return super(RecurringPayment, self).unlink()


class RecurringPaymentLine(models.Model):
    _name = 'recurring.payment.line'
    _description = 'Recurring Payment Line'

    recurring_payment_id = fields.Many2one('recurring.payment', string="Recurring Payment")
    partner_id = fields.Many2one('res.partner', 'Partner', required=True)
    amount = fields.Monetary('Amount', required=True, default=0.0)
    date = fields.Date('Date', required=True, default=date.today())
    journal_id = fields.Many2one('account.journal', 'Journal', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')
    payment_id = fields.Many2one('account.payment', string='Payment')
    state = fields.Selection(selection=[('draft', 'Draft'),
                                        ('done', 'Done')], default='draft', string='Status')

    def action_create_payment(self):
        vals = {
            'payment_type': self.recurring_payment_id.payment_type,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'date': self.date,
            'memo': self.recurring_payment_id.name,
            'partner_id': self.partner_id.id,
        }
        payment = self.env['account.payment'].create(vals)
        if payment:
            if self.recurring_payment_id.journal_state == 'posted':
                payment.action_post()
            self.write({'state': 'done', 'payment_id': payment.id})

