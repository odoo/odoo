# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo import api, models, fields


class RecurringPayments(models.Model):
    """Created the module for recurring payments"""
    _name = 'account.recurring.payments'
    _description = 'Accounting Recurring Payment'

    def _get_next_schedule(self):
        """Function for adding the schedule process"""
        if self.date:
            recurr_dates = []
            today = datetime.today()
            start_date = datetime.strptime(str(self.date), '%Y-%m-%d')
            while start_date <= today:
                recurr_dates.append(str(start_date.date()))
                if self.recurring_period == 'days':
                    start_date += relativedelta(days=self.recurring_interval)
                elif self.recurring_period == 'weeks':
                    start_date += relativedelta(weeks=self.recurring_interval)
                elif self.recurring_period == 'months':
                    start_date += relativedelta(months=self.recurring_interval)
                else:
                    start_date += relativedelta(years=self.recurring_interval)
            self.next_date = start_date.date()

    name = fields.Char(string='Name')
    debit_account = fields.Many2one('account.account', 'Debit Account',
                                    required=True)
    credit_account = fields.Many2one('account.account', 'Credit Account',
                                     required=True)
    journal_id = fields.Many2one('account.journal', 'Journal', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account',
                                          'Analytic Account')
    date = fields.Date('Starting Date', required=True, default=date.today())
    next_date = fields.Date('Next Schedule', compute=_get_next_schedule,
                            readonly=True, copy=False)
    recurring_period = fields.Selection(selection=[('days', 'Days'),
                                                   ('weeks', 'Weeks'),
                                                   ('months', 'Months'),
                                                   ('years', 'Years')],
                                        store=True, required=True)
    amount = fields.Float('Amount')
    description = fields.Text('Description')
    state = fields.Selection(selection=[('draft', 'Draft'),
                                        ('running', 'Running')],
                             default='draft', string='Status')
    journal_state = fields.Selection(selection=[('draft', 'Unposted'),
                                                ('posted', 'Posted')],
                                     required=True, default='draft',
                                     string='Generate Journal As')
    recurring_interval = fields.Integer('Recurring Interval', default=1)
    partner_id = fields.Many2one('res.partner', 'Partner')
    pay_time = fields.Selection(selection=[('pay_now', 'Pay Directly'),
                                           ('pay_later', 'Pay Later')],
                                store=True, required=True)
    company_id = fields.Many2one('res.company',
                                 default=lambda l: l.env.company.id)
    recurring_lines = fields.One2many('account.recurring.entries.line', 'tmpl_id')

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """Onchange partner field for updating the credit account value"""
        if self.partner_id.property_account_receivable_id:
            self.credit_account = self.partner_id.property_account_payable_id

    @api.model
    def _cron_generate_entries(self):
        """Generate recurring entries based on the defined schedule
        and create corresponding accounting moves."""
        data = self.env['account.recurring.payments'].search(
            [('state', '=', 'running')])
        entries = self.env['account.move'].search(
            [('recurring_ref', '!=', False)])
        journal_dates = []
        journal_codes = []
        remaining_dates = []
        for entry in entries:
            journal_dates.append(str(entry.date))
            if entry.recurring_ref:
                journal_codes.append(str(entry.recurring_ref))
        today = datetime.today()
        for line in data:
            if line.date:
                recurr_dates = []
                start_date = datetime.strptime(str(line.date), '%Y-%m-%d')
                while start_date <= today:
                    recurr_dates.append(str(start_date.date()))
                    if line.recurring_period == 'days':
                        start_date += relativedelta(
                            days=line.recurring_interval)
                    elif line.recurring_period == 'weeks':
                        start_date += relativedelta(
                            weeks=line.recurring_interval)
                    elif line.recurring_period == 'months':
                        start_date += relativedelta(
                            months=line.recurring_interval)
                    else:
                        start_date += relativedelta(
                            years=line.recurring_interval)
                for rec in recurr_dates:
                    recurr_code = str(line.id) + '/' + str(rec)
                    if recurr_code not in journal_codes:
                        remaining_dates.append({
                            'date': rec,
                            'template_name': line.name,
                            'amount': line.amount,
                            'tmpl_id': line.id,
                        })
        child_ids = self.recurring_lines.create(remaining_dates)
        for line in child_ids:
            tmpl_id = line.tmpl_id
            recurr_code = str(tmpl_id.id) + '/' + str(line.date)
            line_ids = [(0, 0, {
                'account_id': tmpl_id.credit_account.id,
                'partner_id': tmpl_id.partner_id.id,
                'credit': line.amount,
                # 'analytic_account_id': tmpl_id.analytic_account_id.id,
            }), (0, 0, {
                'account_id': tmpl_id.debit_account.id,
                'partner_id': tmpl_id.partner_id.id,
                'debit': line.amount,
                # 'analytic_account_id': tmpl_id.analytic_account_id.id,
            })]
            vals = {
                'date': line.date,
                'recurring_ref': recurr_code,
                'company_id': self.env.company.id,
                'journal_id': tmpl_id.journal_id.id,
                'ref': line.template_name,
                'narration': 'Recurring entry',
                'line_ids': line_ids
            }
            move_id = self.env['account.move'].create(vals)
            if tmpl_id.journal_state == 'posted':
                move_id.post()
