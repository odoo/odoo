# -*- coding: utf-8 -*-

from odoo import api, models, fields, tools, _
from odoo.exceptions import UserError

import random
import datetime
import logging
import datetime
try:
    from faker import Faker
except ImportError:
    raise UserError('You need to install faker (see https://pypi.org/project/Faker/) in order to install account_generator')
fake = Faker()
_logger = logging.getLogger(__name__)


class AccountGenerator(models.TransientModel):
    _name = "account.generator"
    _description = "Generator"

    generator = fields.Selection([('aml', 'Journal Entry'), ('partner', 'Partner'), ('invoice', 'Invoice'), ('payment', 'Payments'), ('bank_statement', 'Bank Statement')], required=True, default='aml')

    number_to_generate = fields.Integer(default=10)
    number_of_lines = fields.Integer(default=10)
    customer = fields.Boolean(default=True)
    supplier = fields.Boolean(default=True)
    company_type = fields.Selection([('person', 'Person'), ('company', 'Company')], default='person')
    post = fields.Boolean()
    end_date = fields.Date(default=fields.Date.today() + datetime.timedelta(days=30 * 3))
    start_date = fields.Date(default=fields.Date.today() + datetime.timedelta(days=-365 * 3))
    empty_field_probability = fields.Float(default=0.7)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    partner_ids = fields.Many2many('res.partner', relation="generator_partner_pool")
    account_ids = fields.Many2many('account.account', relation="generator_account_pool")
    journal_ids = fields.Many2many('account.journal', relation="generator_journal_pool")
    partner_excluded_ids = fields.Many2many('res.partner', relation="generator_excluded_partner")
    account_excluded_ids = fields.Many2many('account.account', relation="generator_excluded_account")
    journal_excluded_ids = fields.Many2many('account.journal', relation="generator_excluded_journal")

    ###### Wizard usability ####################################################

    @api.onchange('empty_field_probability')
    def _onchange_probability(self):
        if not (0 <= self.empty_field_probability <= 1):
            raise UserError(_('Probability must be between 0 and 1'))

    ###### Generation functions ################################################

    def generate_amls(self):
        def generate_line(amount=None):
            amount = amount or random.uniform(-10000, 10000)
            return (0, 0, {'debit': amount > 0 and amount or 0, 'credit': amount < 0 and -amount or 0, 'account_id': random.choice(account_ids).id, 'partner_id': random.choice(partner_ids).id})

        partner_ids, account_ids, journal_ids = self._get_records()
        self._check_records(locals())
        create_vals = []
        for i in range(self.number_to_generate):
            date = fake.date_time_between_dates(datetime_start=self.start_date, datetime_end=self.end_date)
            create_vals.append({
                'line_ids': [generate_line() for i in range(random.randint(1, self.number_of_lines - 1))],
                'date': date,
                'journal_id': random.choice(journal_ids).id,
            })
            amount = sum(line[2]['debit'] - line[2]['credit'] for line in create_vals[-1]['line_ids'])
            create_vals[-1]['line_ids'].append(generate_line(-amount))
        line_ids, view = self._create_records('account.move', create_vals)
        if self.post:
            line_ids.post()
            _logger.info('Journal Entries posted')
        return view

    def generate_partners(self):
        create_vals = []
        for i in range(self.number_to_generate):
            create_vals.append({
                'name': fake.name() if self.company_type == 'person' else fake.company(),
                'customer': self.customer,
                'supplier': self.supplier,
                'company_type': self.company_type,
                'street': fake.street_address(),
                'city': fake.city(),
                'phone': fake.phone_number(),
                'email': fake.email(),
            })
        partner_ids, view = self._create_records('res.partner', create_vals)
        return view

    def generate_invoices(self):
        def generate_line(type):
            account_id = random.choice(rev_account_ids).id if type.startswith('out_') else random.choice(exp_account_ids).id
            return (0, 0, {'name': fake.bs(), 'account_id': account_id, 'quantity': random.randint(1, 50), 'price_unit': random.uniform(1, 10000)})

        partner_ids = self.partner_ids or self.env['res.partner'].search([('customer_rank', '>=', self.customer and 1 or 0), ('supplier_rank', '>=', self.supplier and 1 or 0), ('id', 'not in', self.partner_excluded_ids.ids)])
        if not partner_ids:
            raise UserError(_('No partner found'))
        exp_account_ids = self.account_ids or self.env['account.account'].search([('company_id', '=', self.company_id.id), ('user_type_id', '=', self.env.ref('account.data_account_type_expenses').id), ('id', 'not in', self.account_excluded_ids.ids)])
        rev_account_ids = self.account_ids or self.env['account.account'].search([('company_id', '=', self.company_id.id), ('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id), ('id', 'not in', self.account_excluded_ids.ids)])
        account_ids = exp_account_ids + rev_account_ids
        if not account_ids:
            raise UserError(_('No account found'))
        rec_journal_ids = self.journal_ids or self.env['account.journal'].search([('company_id', '=', self.company_id.id), ('type', '=', 'sale'), ('id', 'not in', self.journal_excluded_ids.ids)])
        pay_journal_ids = self.journal_ids or self.env['account.journal'].search([('company_id', '=', self.company_id.id), ('type', '=', 'purchase'), ('id', 'not in', self.journal_excluded_ids.ids)])
        journal_ids = rec_journal_ids + pay_journal_ids
        if not journal_ids:
            raise UserError(_('No journal found'))

        create_vals = []
        for i in range(self.number_to_generate):
            date = fake.date_time_between_dates(datetime_start=self.start_date, datetime_end=self.end_date).date()
            partner_id = random.choice(partner_ids)
            type = random.choice([t[1] for t in [('supplier_rank', 'in_'), ('customer_rank', 'out_')] if getattr(partner_id, t[0])]) + random.choice(['invoice', 'receipt', 'refund'])
            create_vals.append({
                'partner_id': partner_id.id,
                'invoice_line_ids': [generate_line(type) for i in range(random.randint(1, self.number_of_lines))],
                'invoice_date': date,
                'type': type,
                'journal_id': random.choice(rec_journal_ids).id if type.startswith('out_') else random.choice(pay_journal_ids).id
            })
        invoice_ids, view = self._create_records('account.move', create_vals)
        if self.post:
            invoice_ids.post()
            _logger.info('Invoices posted')
        return view

    def generate_payments(self):
        currencies = self.env['res.currency'].search([])

        company_ids = self.company_ids or self.env['res.company'].search([('id', 'not in', self.company_excluded_ids.ids)])
        partner_ids = self.partner_ids or self.env['res.partner'].search([('customer_rank', '>=', self.customer and 1 or 0), ('supplier_rank', '>=', self.supplier and 1 or 0), ('id', 'not in', self.partner_excluded_ids.ids)])
        journal_ids = self.journal_ids or self.env['account.journal'].search([('company_id', '=', self.company_id.id), ('type', 'in', ['cash', 'bank']), ('id', 'not in', self.journal_excluded_ids.ids)])
        self._check_records(locals())

        create_vals = []
        for i in range(self.number_to_generate):
            partner_id = random.choice(partner_ids)
            journal_id = random.choice(journal_ids)
            amount = random.uniform(-1000000, 1000000)
            direction = ('inbound' if amount > 0 else 'outbound')
            create_vals.append({
                'journal_id': journal_id.id,
                'payment_method_id': random.choice(journal_id.inbound_payment_method_ids if direction == 'inbound' else journal_id.outbound_payment_method_ids).id,
                'payment_date': fake.date_time_between_dates(datetime_start=self.start_date, datetime_end=self.end_date).date(),
                'communication': fake.bs(),
                'payment_type': direction,
                'amount': abs(amount),
                'currency_id': random.choice(currencies).id,
                'partner_id': partner_id.id,
                'partner_type': random.choice([t for t in ['supplier', 'customer'] if getattr(partner_id, t)]),
                'partner_bank_account_id': self._random_or_empty(partner_id.bank_ids.ids),
            })
        payment_ids, view = self._create_records('account.payment', create_vals)
        if self.post:
            payment_ids.post()
            _logger.info('Payments posted')
        return view

    def generate_bank_statement(self):
        def generate_line():
            return (0, 0, {'date': fake.date_between_dates(date_start=self.start_date, date_end=self.end_date), 'name': fake.bs(), 'partner_id': random.choice(partner_ids).id, 'amount': random.uniform(-10000, 10000)})

        journal_ids = self.journal_ids or self.env['account.journal'].search([('type', '=', 'bank'), ('id', 'not in', self.journal_excluded_ids.ids)])
        partner_ids = self.partner_ids or self.env['res.partner'].search([('customer', '=', self.customer), ('supplier', '=', self.supplier), ('id', 'not in', self.partner_excluded_ids.ids)])
        self._check_records(locals())

        create_vals = []
        for i in range(self.number_to_generate):
            create_vals.append({
                'journal_id': random.choice(journal_ids).id,
                'line_ids': [generate_line() for i in range(random.randint(1, self.number_of_lines))],
                'date': self.end_date,
            })
        bank_statement_ids, view = self._create_records('account.bank.statement', create_vals)
        return view

    ###### Tools and Misc ######################################################

    def _create_records(self, model_name, create_vals):
        model = self.env[model_name]
        _logger.info('Start Create')
        model.check_access_rights('write')
        self.env.su = True
        record_ids = model.create(create_vals)
        self.env.su = False
        _logger.info('{} created'.format(model._description))
        return record_ids, {
            'name': _('Generated {}'.format(model._description)),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': model_name,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', record_ids.ids)],
        }

    def _random_or_empty(self, items):
        if random.uniform(0, 1) > self.empty_field_probability or not len(items):
            return False
        return random.choice(items)

    def _get_records(self):
        partner_ids = self.partner_ids or self.env['res.partner'].search([('id', 'not in', self.partner_excluded_ids.ids)])
        account_ids = self.account_ids or self.env['account.account'].search([('company_id', '=', self.company_id.id), ('id', 'not in', self.account_excluded_ids.ids)])
        journal_ids = self.journal_ids or self.env['account.journal'].search([('company_id', '=', self.company_id.id), ('id', 'not in', self.journal_excluded_ids.ids)])

        return company_ids, partner_ids, account_ids, journal_ids

    def _check_records(self, locals):
        for i in locals:
            if i.endswith('_ids') and not locals[i]:
                raise UserError(_("No {} found").format(i))
