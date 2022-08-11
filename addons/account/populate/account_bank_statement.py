# -*- coding: utf-8 -*-
"""Classes defining the populate factory for Bank Statements and related models."""
import random

from odoo import models
from odoo.tools import populate

from dateutil.relativedelta import relativedelta
from functools import lru_cache
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)


class AccountBankStatement(models.Model):
    """Populate factory part for account.bank.statements."""

    _inherit = "account.bank.statement"
    _populate_sizes = {
        'small': 10,
        'medium': 1000,
        'large': 20000,
    }

    _populate_dependencies = ['account.bank.statement.line', ]

    def _populate_factories(self):

        return [
            ('name', populate.constant('statement_{counter}')),
        ]

    def _populate(self, size):
        """
        Populate the bank statements with random lines.

        The first half is all valid statements with no gaps, the second half is properly balanced but with gaps.
        :param size:
        :return:
        """
        records = super()._populate(size)
        _logger.info('Adjusting Bank Statements')
        total = len(records)
        for statement in records[:total//2]:
            first_line = self.env['account.bank.statement.line'].search(
                domain=[('statement_id', '=', False)],
                limit=1,
                order='date, sequence desc, id',
            )
            journal = first_line.journal_id
            st_lines = first_line | self.env['account.bank.statement.line'].search(
                domain=[
                    ('statement_id', '=', False),
                    ('journal_id', '=', journal.id)
                ],
                limit=random.randint(1, 19),
                order='date, sequence desc, id',
            )
            statement.line_ids = st_lines
            statement.balance_end_real = statement.balance_end
        for statement in records[total//2:total*3//4]:
            if random.random() < 0.1:
                continue
            first_line = random.choice(
                self.env['account.bank.statement.line'].search(
                    domain=[('statement_id', '=', False)],
                    limit=3,
                    order='date, sequence desc, id',
                )
            )
            journal = first_line.journal_id
            st_lines = first_line | self.env['account.bank.statement.line'].search(
                domain=[
                    ('statement_id', '=', False),
                    ('journal_id', '=', journal.id)
                ],
                limit=random.randint(1, 19),
                order='date, sequence desc, id'
            )
            statement.line_ids = st_lines
            statement.balance_end_real = statement.balance_end
        for statement in records[total*3//4:]:
            if random.random() < 0.2:
                continue
            first_line = random.choice(
                self.env['account.bank.statement.line'].search(
                    domain=[('statement_id', '=', False)],
                    limit=3,
                    order='date, sequence desc, id'
                )
            )
            journal = first_line.journal_id
            st_lines = sum(
                random.choices(
                    self.env['account.bank.statement.line'].search(
                        domain=[
                            ('statement_id', '=', False),
                            ('journal_id', '=', journal.id)
                        ],
                        limit=random.randint(1, 29),
                        order='date, sequence desc, id',
                    ),
                    k=random.randint(1, 19),
                ),
                first_line,
            )
            statement.line_ids = st_lines
            statement.balance_end_real = statement.balance_end * random.randint(1, 3)
        return records


class AccountBankStatementLine(models.Model):
    """Populate factory part for account.bank.statements.line."""

    _inherit = "account.bank.statement.line"

    _populate_sizes = {
        'small': 100,
        'medium': 10000,
        'large': 200000,
    }

    _populate_dependencies = ['account.journal', 'res.company', 'res.partner']

    def _populate_factories(self):
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

        def get_partner(random, values, **kwargs):
            """Get a partner by selecting inside the list of partner a company has access to.

            There is also a chance of having no partner set.
            :param random: seeded random number generator.
            :param values (dict): the values already selected for the record.
            :return (int): an id of a partner accessible by the company of the statement.
            """
            company_id = self.env['account.journal'].browse(values['journal_id']).company_id.id
            partner = search_partner_ids(company_id)
            return random.choices(partner + [False], [1/len(partner)] * len(partner) + [1])[0]

        def get_amount_currency(random, values, **kwargs):
            """
            Get a random amount currency between one tenth of  amount and 10 times amount with the same sign
             if foreign_currency_id is set

            :param random: seeded random number generator.
            :return (float): a number between amount / 10 and amount * 10.
            """
            return random.uniform(0.1 * values['amount'], 10 * values['amount']) if values['foreign_currency_id'] else 0

        def get_currency(random, values, **kwargs):
            """Get a random currency.

            The currency has to be empty if it is the same as the currency of the line's journal's.
            :param random: seeded random number generator.
            :param values (dict): the values already selected for the record.
            :return (int, bool): the id of an active currency or False if it is the same currency as
                                 the lines's journal's currency.
            """
            journal = self.env['account.journal'].browse(values['journal_id'])
            currency = random.choice(self.env['res.currency'].search([('active', '=', True)]).ids)
            return currency if currency != (journal.currency_id or journal.company_id.currency_id).id else False

        company_ids = self.env['res.company'].search([
            ('chart_template_id', '!=', False),
            ('id', 'in', self.env.registry.populated_models['res.company']),
        ])

        journal_ids = self.env['account.journal'].search([
            ('company_id', 'in', company_ids.ids),
            ('type', 'in', ('cash', 'bank')),
        ]).ids
        # Because we are accessing related fields of bank statements, a prefetch can improve the performances.
        # self = self.with_prefetch(self.env.registry.populated_models['account.bank.statement'])
        return [
            ('journal_id', populate.iterate(journal_ids)),
            ('partner_id', populate.compute(get_partner)),
            ('date', populate.randdatetime(relative_before=relativedelta(years=-4))),
            ('payment_ref', populate.constant('transaction_{values[date]}_{counter}')),
            ('amount', populate.randint(-1000, 1000)),
            ('foreign_currency_id', populate.compute(get_currency)),
            ('amount_currency', populate.compute(get_amount_currency)),
        ]
