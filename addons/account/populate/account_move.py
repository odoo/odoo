# -*- coding: utf-8 -*-
"""Classes defining the populate factory for Journal Entries, Invoices and related models."""
from odoo import models, fields
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

    _populate_dependencies = ['res.partner', 'account.journal']

    def _populate_factories(self):
        @lru_cache()
        def search_account_ids(company_id, type=None, group=None):
            """Search all the accounts of a certain type and group for a company.

            This method is cached, only one search is done per tuple(company_id, type, group).
            :param company_id (int): the company to search accounts for.
            :param type (str): the type to filter on. If not set, do not filter. Valid values are:
                               payable, receivable, liquidity, other, False.
            :param group (str): the group to filter on. If not set, do not filter. Valid values are:
                                asset, liability, equity, off_balance, False.
            :return (Model<account.account>): the recordset of accounts found.
            """
            domain = [('company_id', '=', company_id)]
            if type:
                domain += [('internal_type', '=', type)]
            if group:
                domain += [('internal_group', '=', group)]
            return self.env['account.account'].search(domain)

        @lru_cache()
        def search_journal_ids(company_id, journal_type):
            """Search all the journal of a certain type for a company.

            This method is cached, only one search is done per tuple(company_id, journal_type).
            :param company_id (int): the company to search journals for.
            :param journal_type (str): the journal type to filter on.
                                       Valid values are sale, purchase, cash, bank and general.
            :return (list<int>): the ids of the journals of a company and a certain type
            """
            return self.env['account.journal'].search([
                ('company_id', '=', company_id),
                ('type', '=', journal_type),
            ]).ids

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
            def get_line(account, label, balance=None, balance_sign=False, exclude_from_invoice_tab=False):
                company_currency = account.company_id.currency_id
                currency = self.env['res.currency'].browse(currency_id)
                balance = balance or balance_sign * round(random.uniform(0, 1000))
                amount_currency = company_currency._convert(balance, currency, account.company_id, date)
                return (0, 0, {
                    'name': 'label_%s' % label,
                    'debit': balance > 0 and balance or 0,
                    'credit': balance < 0 and -balance or 0,
                    'account_id': account.id,
                    'partner_id': partner_id,
                    'currency_id': currency_id,
                    'amount_currency': amount_currency,
                    'exclude_from_invoice_tab': exclude_from_invoice_tab,
                })
            move_type = values['move_type']
            date = values['date']
            company_id = values['company_id']
            currency_id = values['currency_id']
            partner_id = values['partner_id']

            # Determine the right sets of accounts depending on the move_type
            if move_type in self.get_sale_types(include_receipts=True):
                account_ids = search_account_ids(company_id, 'other', 'income')
                balance_account_ids = search_account_ids(company_id, 'receivable', 'asset')
            elif move_type in self.get_purchase_types(include_receipts=True):
                account_ids = search_account_ids(company_id, 'other', 'expense')
                balance_account_ids = search_account_ids(company_id, 'payable', 'liability')
            else:
                account_ids = search_account_ids(company_id, 'other', 'asset')
                balance_account_ids = account_ids

            # Determine the right balance sign depending on the move_type
            if move_type in self.get_inbound_types(include_receipts=True):
                balance_sign = -1
            elif move_type in self.get_outbound_types(include_receipts=True):
                balance_sign = 1
            else:
                # balance sign will be alternating each line
                balance_sign = False

            # Add a random number of lines (between 1 and 20)
            lines = [get_line(
                account=random.choice(account_ids),
                label=i,
                balance_sign=balance_sign or (i % 2) or -1,  # even -> negative, odd -> positive if balance_sign=False
            ) for i in range(random.randint(1, 20))]

            # Add a last line containing the balance.
            # For invoices, etc., it will be on the receivable/payable account.
            lines += [get_line(
                account=random.choice(balance_account_ids),
                balance=sum(l[2]['credit'] - l[2]['debit'] for l in lines),
                label='balance',
                exclude_from_invoice_tab=move_type in self.get_invoice_types(include_receipts=True),
            )]

            return lines

        def get_journal(random, values, **kwargs):
            """Get a random journal depending on the company and the move_type.

            :param random: seeded random number generator.
            :param values (dict): the values already selected for the record.
            :return (int): the id of the journal randomly selected
            """
            move_type = values['move_type']
            company_id = values['company_id']
            if move_type in self.get_sale_types(include_receipts=True):
                journal_type = 'sale'
            elif move_type in self.get_purchase_types(include_receipts=True):
                journal_type = 'purchase'
            else:
                journal_type = 'general'
            journal = search_journal_ids(company_id, journal_type)
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
        if not company_ids:
            return []
        return [
            ('move_type', populate.randomize(
                ['entry', 'in_invoice', 'out_invoice', 'in_refund', 'out_refund', 'in_receipt', 'out_receipt'],
                [0.2, 0.3, 0.3, 0.07, 0.07, 0.03, 0.03],
            )),
            ('company_id', populate.randomize(company_ids.ids)),
            ('currency_id', populate.randomize(self.env['res.currency'].search([
                ('active', '=', True),
            ]).ids)),
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
