# -*- coding: utf-8 -*-
"""Classes defining the populate factory for Bank Statements and related models."""

from odoo import models, Command
from odoo.tools import populate

from dateutil.relativedelta import relativedelta
from functools import lru_cache
import logging

_logger = logging.getLogger(__name__)


class AccountBankStatement(models.Model):
    """Populate factory part for account.bank.statements."""

    _inherit = "account.bank.statement"
    _populate_dependencies = ['account.bank.statement.line']

    def _populate(self, size):
        """
        Populate the bank statements with random lines.
        :param size:
        :return:
        """
        rand = populate.Random('account_bank_statement+Populate')

        read_group_res = self.env['account.bank.statement.line'].read_group(
            [('statement_id', '=', False)],
            ['ids:array_agg(id)'],
            ['journal_id'],
        )

        bank_statement_vals_list = []
        for res in read_group_res:
            available_ids = res['ids']
            nb_ids = len(available_ids)
            while nb_ids > 0:
                batch_size = min(rand.randint(1, 19), nb_ids)
                nb_ids -= batch_size

                # 50% to create a statement.
                statement_needed = bool(rand.randint(0, 1))
                if not statement_needed:
                    continue

                bank_statement_vals_list.append({
                    'name': f"statement_{len(bank_statement_vals_list) + 1}",
                    'journal_id': res['journal_id'][0],
                    'line_ids': [Command.set(res['ids'])],
                })

        return self.env['account.bank.statement'].create(bank_statement_vals_list)


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

        def get_amount(random, **kwargs):
            """Get a random amount between -1000 and 1000.
            It is impossible to get a null amount. Because it would not be a valid statement line.
            :param random: seeded random number generator.
            :return (float): a number between -1000 and 1000.
            """
            return random.uniform(-1000, 1000) or 1

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
        if not company_ids:
            return []

        journal_ids = self.env['account.journal'].search([
            ('company_id', 'in', company_ids.ids),
            ('type', 'in', ('cash', 'bank')),
        ]).ids
        return [
            ('journal_id', populate.iterate(journal_ids)),
            ('partner_id', populate.compute(get_partner)),
            ('date', populate.randdatetime(relative_before=relativedelta(years=-4))),
            ('payment_ref', populate.constant('transaction_{values[date]}_{counter}')),
            ('amount', populate.compute(get_amount)),
            ('foreign_currency_id', populate.compute(get_currency)),
            ('amount_currency', populate.compute(get_amount_currency)),
        ]
