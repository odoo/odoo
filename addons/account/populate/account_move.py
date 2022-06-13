# -*- coding: utf-8 -*-
"""Classes defining the populate factory for Journal Entries, Invoices and related models."""
from odoo import models, fields, Command
from odoo.tools import populate

import logging
import math
from functools import lru_cache
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    """Populate factory part for account.move.

    Because of the complicated nature of the interraction of account.move and account.move.line,
    both models are actualy generated in the same factory.
    """

    _inherit = "account.move"

    _populate_sizes = {
        'small': 1000,
        'medium': 10000,
        'large': 500000,
    }

    _populate_dependencies = ['res.partner', 'account.journal', 'product.product']

    def _populate_factories(self):
        @lru_cache()
        def search_accounts(company_id, types=None):
            """Search all the accounts of a certain type for a company.

            This method is cached, only one search is done per tuple(company_id, type).
            :param company_id (int): the company to search accounts for.
            :param type (str): the type to filter on. If not set, do not filter. Valid values are:
                               payable, receivable, liquidity, other, False.
            :return (Model<account.account>): the recordset of accounts found.
            """
            domain = [('company_id', '=', company_id), ('account_type', '!=', 'off_balance')]
            if types:
                domain += [('account_type', 'in', types)]
            return self.env['account.account'].search(domain)

        @lru_cache()
        def search_journals(company_id, journal_type, currency_id):
            """Search all the journal of a certain type for a company.

            This method is cached, only one search is done per tuple(company_id, journal_type).
            :param company_id (int): the company to search journals for.
            :param journal_type (str): the journal type to filter on.
                                       Valid values are sale, purchase, cash, bank and general.
            :param currency_id (int): the currency to search journals for.
            :return (list<int>): the ids of the journals of a company and a certain type
            """
            return self.env['account.journal'].search([
                ('company_id', '=', company_id),
                ('currency_id', 'in', (False, currency_id)),
                ('type', '=', journal_type),
            ]).ids

        @lru_cache()
        def search_products(company_id):
            """Search all the products a company has access to.

            This method is cached, only one search is done per company_id.
            :param company_id (int): the company to search products for.
            :return (Model<product.product>): all the products te company has access to
            """
            return self.env['product.product'].search([
                ('company_id', 'in', (False, company_id)),
                ('id', 'in', self.env.registry.populated_models['product.product']),
            ])

        @lru_cache()
        def search_partner_ids(company_id):
            """Search all the partners that a company has access to.

            This method is cached, only one search is done per company_id.
            :param company_id (int): the company to search partners for.
            :return (list<int>): the ids of partner the company has access to.
            """
            return self.env['res.partner'].search([
                '|', ('company_id', '=', company_id), ('company_id', '=', False),
                ('id', 'in', self.env.registry.populated_models['res.partner']),
            ]).ids

        def get_invoice_date(values, **kwargs):
            """Get the invoice date date.

            :param values (dict): the values already selected for the record.
            :return (datetime.date, bool): the accounting date if it is an invoice (or similar) document
                                           or False otherwise.
            """
            if values['move_type'] in self.get_invoice_types(include_receipts=True):
                return values['date']
            return False

        def get_lines(random, values, **kwargs):
            """Build the dictionary of account.move.line.

            Generate lines depending on the move_type, company_id and currency_id.
            :param random: seeded random number generator.
            :param values (dict): the values already selected for the record.
            :return list: list of ORM create commands for the field line_ids
            """
            def get_entry_line(label, balance=None):
                account = random.choice(accounts)
                currency = account.currency_id != account.company_id.currency_id and account.currency_id or random.choice(currencies)
                balance = balance or round(random.uniform(-10000, 10000))
                return Command.create({
                    'name': 'label_%s' % label,
                    'balance': balance,
                    'account_id': account.id,
                    'partner_id': partner_id,
                    'currency_id': currency.id,
                    'amount_currency': account.company_id.currency_id._convert(balance, currency, account.company_id, date),
                })

            def get_invoice_line():
                return Command.create({
                    'product_id': random.choice(products).id,
                    'account_id': random.choice(accounts).id,
                    'price_unit': round(random.uniform(0, 10000)),
                    'quantity': round(random.uniform(0, 100)),
                })

            move_type = values['move_type']
            date = values['date']
            company_id = values['company_id']
            partner_id = values['partner_id']

            # Determine the right sets of accounts depending on the move_type
            if move_type in self.get_sale_types(include_receipts=True):
                accounts = search_accounts(company_id, ('income',))
            elif move_type in self.get_purchase_types(include_receipts=True):
                accounts = search_accounts(company_id, ('expense',))
            else:
                accounts = search_accounts(company_id)

            products = search_products(company_id)

            if move_type == 'entry':
                # Add a random number of lines (between 1 and 20)
                lines = [get_entry_line(
                    label=i,
                ) for i in range(random.randint(1, 20))]

                # Add a last line containing the balance.
                # For invoices, etc., it will be on the receivable/payable account.
                lines += [get_entry_line(
                    balance=-sum(vals['balance'] for _command, _id, vals in lines),
                    label='balance',
                )]
            else:
                lines = [get_invoice_line() for _i in range(random.randint(1, 20))]

            return lines

        def get_journal(random, values, **kwargs):
            """Get a random journal depending on the company and the move_type.

            :param random: seeded random number generator.
            :param values (dict): the values already selected for the record.
            :return (int): the id of the journal randomly selected
            """
            move_type = values['move_type']
            company_id = values['company_id']
            currency_id = values['company_id']
            if move_type in self.get_sale_types(include_receipts=True):
                journal_type = 'sale'
            elif move_type in self.get_purchase_types(include_receipts=True):
                journal_type = 'purchase'
            else:
                journal_type = 'general'
            journal = search_journals(company_id, journal_type, currency_id)
            return random.choice(journal)

        def get_partner(random, values, **kwargs):
            """Get a random partner depending on the company and the move_type.

            The first 3/5 of the available partners are used as customer
            The last 3/5 of the available partners are used as suppliers
            It means 1/5 is both customer/supplier
            -> Same proportions as in account.payment
            :param random: seeded random number generator.
            :param values (dict): the values already selected for the record.
            :return (int, bool): the id of the partner randomly selected if it is an invoice document
                                 False if it is a Journal Entry.
            """
            move_type = values['move_type']
            company_id = values['company_id']
            partner_ids = search_partner_ids(company_id)

            if move_type in self.get_sale_types(include_receipts=True):
                return random.choice(partner_ids[:math.ceil(len(partner_ids)/5*2)])
            if move_type in self.get_purchase_types(include_receipts=True):
                return random.choice(partner_ids[math.floor(len(partner_ids)/5*2):])
            return False

        company_ids = self.env['res.company'].search([
            ('chart_template_id', '!=', False),
            ('id', 'in', self.env.registry.populated_models['res.company']),
        ])
        currencies = self.env['res.currency'].search([
            ('active', '=', True),
        ])

        return [
            ('move_type', populate.randomize(
                ['entry', 'in_invoice', 'out_invoice', 'in_refund', 'out_refund', 'in_receipt', 'out_receipt'],
                [0.2, 0.3, 0.3, 0.07, 0.07, 0.03, 0.03],
            )),
            ('company_id', populate.randomize(company_ids.ids)),
            ('currency_id', populate.randomize(currencies.ids)),
            ('journal_id', populate.compute(get_journal)),
            ('date', populate.randdatetime(relative_before=relativedelta(years=-4), relative_after=relativedelta(years=1))),
            ('invoice_date', populate.compute(get_invoice_date)),
            ('partner_id', populate.compute(get_partner)),
            ('line_ids', populate.compute(get_lines)),
        ]

    def _populate(self, size):
        records = super()._populate(size)
        _logger.info('Posting Journal Entries')
        to_post = records.filtered(lambda r: r.date < fields.Date.today())
        to_post.action_post()

        # TODO add some reconciliations. Not done initially because of perfs.
        # _logger.info('Registering Payments for Invoices and Bills')
        # random = populate.Random('account.move+register_payment')
        # for invoice in to_post:
        #     if invoice.is_invoice() and random.uniform(0, 1) < 0.9:  # 90% of invoices are at least partialy paid
        #         payment_wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({})
        #         if random.uniform(0, 1) > 0.9:  # 90% of paid invoices have the exact amount, others vary a little
        #             payment_wizard.amount *= random.uniform(0.5, 1.5)
        #         payment_wizard._create_payments()
        return records
