# -*- coding: utf-8 -*-
"""Classes defining the populate factory for Bank Statements and related models."""
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

    _populate_dependencies = ['account.journal', 'res.company']

    def _populate_factories(self):
        company_ids = self.env['res.company'].search([
            ('chart_template_id', '!=', False),
            ('id', 'in', self.env.registry.populated_models['res.company']),
        ])
        journal_ids = self.env['account.journal'].search([
            ('company_id', 'in', company_ids.ids),
            ('type', 'in', ('cash', 'bank')),
        ]).ids
        return [
            ('journal_id', populate.iterate(journal_ids)),
            ('name', populate.constant('statement_{counter}')),
            ('date', populate.randdatetime(relative_before=relativedelta(years=-4))),
        ]


class AccountBankStatementLine(models.Model):
    """Populate factory part for account.bank.statements.line."""

    _inherit = "account.bank.statement.line"

    _populate_sizes = {
        'small': 100,
        'medium': 10000,
        'large': 200000,
    }

    _populate_dependencies = ['account.bank.statement', 'res.partner']

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
            company_id = self.env['account.bank.statement'].browse(values['statement_id']).company_id.id
            partner = search_partner_ids(company_id)
            return random.choices(partner + [False], [1/len(partner)] * len(partner) + [1])[0]

        def get_date(random, values, **kwargs):
            """Get a date in the past.

            This date can but up to 31 days before the statement linked to this line.
            :param random: seeded random number generator.
            :param values (dict): the values already selected for the record.
            :return (datetime.date): a date up to 31 days before the date of the statement.
            """
            statement_date = self.env['account.bank.statement'].browse(values['statement_id']).date
            return statement_date + relativedelta(days=random.randint(-31, 0))

        def get_amount(random, **kwargs):
            """Get a random amount between -1000 and 1000.

            It is impossible to get a null amount. Because it would not be a valid statement line.
            :param random: seeded random number generator.
            :return (float): a number between -1000 and 1000.
            """
            return random.uniform(-1000, 1000) or 1

        def get_currency(random, values, **kwargs):
            """Get a randome currency.

            The currency has to be empty if it is the same as the currency of the statement's journal's.
            :param random: seeded random number generator.
            :param values (dict): the values already selected for the record.
            :return (int, bool): the id of an active currency or False if it is the same currency as
                                 the statement's journal's currency.
            """
            journal = self.env['account.bank.statement'].browse(values['statement_id']).journal_id
            currency = random.choice(self.env['res.currency'].search([('active', '=', True)]).ids)
            return currency if currency != (journal.currency_id or journal.company_id.currency_id).id else False

        # Because we are accessing related fields of bank statements, a prefetch can improve the performances.
        self = self.with_prefetch(self.env.registry.populated_models['account.bank.statement'])
        return [
            ('statement_id', populate.randomize(self.env.registry.populated_models['account.bank.statement'])),
            ('partner_id', populate.compute(get_partner)),
            ('payment_ref', populate.constant('statement_{values[statement_id]}_{counter}')),
            ('date', populate.compute(get_date)),
            ('amount', populate.compute(get_amount)),
            ('currency_id', populate.compute(get_currency)),
        ]

    def _populate(self, size):
        records = super()._populate(size)
        _logger.info('Posting Bank Statements')
        statements = records.statement_id.sorted(lambda r: (r.date, r.name, r.id))
        previous = defaultdict(int)
        for statement in statements:
            statement.balance_start = previous[statement.journal_id]
            previous[statement.journal_id] = statement.balance_end_real = statement.balance_start + statement.total_entry_encoding
        statements.button_post()
        return records
