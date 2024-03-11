# -*- coding: utf-8 -*-
"""Classes defining the populate factory for Bank Statements and related models."""
from odoo import models
from odoo.tools import populate

import logging

_logger = logging.getLogger(__name__)


class AccountReconcileModel(models.Model):
    """Populate factory part for account.reconcile.model."""

    _inherit = "account.reconcile.model"

    _populate_sizes = {
        'small': 5,
        'medium': 100,
        'large': 1000,
    }

    _populate_dependencies = ['res.company']

    def _populate_factories(self):
        def get_name(counter, **kwargs):
            return 'model_%s' % counter

        company_ids = self.env['res.company'].search([
            ('chart_template_id', '!=', False),
            ('id', 'in', self.env.registry.populated_models['res.company']),
        ])
        if not company_ids:
            return []
        return [
            ('company_id', populate.cartesian(company_ids.ids)),
            ('rule_type', populate.cartesian(['writeoff_button', 'writeoff_suggestion'])),
            # ('auto_reconcile', populate.cartesian([True, False], [0.1, 0.9])),
            ('name', populate.compute(get_name)),
        ]


class AccountReconcileModelLine(models.Model):
    """Populate factory part for account.reconcile.model.line."""

    _inherit = "account.reconcile.model.line"

    _populate_sizes = {
        'small': 10,
        'medium': 200,
        'large': 2000,
    }

    _populate_dependencies = ['account.reconcile.model']

    def _populate_factories(self):
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
                domain += [('account_type', '=', type)]
            if group:
                domain += [('internal_group', '=', group)]
            return self.env['account.account'].search(domain)

        def get_amount(random, values, **kwargs):
            """Get an amount dending on the amount_type.

            :param random: seeded random number generator.
            :param values (dict): the values already selected for the record.
            :return (int, str):
                If amount_type is fixed, a random number between 1 and 1000
                If amount type is percentage, a random number between 1 and 100
                Else, amount_type is regex, a random regex out of 2
            """
            if values['amount_type'] == 'fixed':
                return '%s' % random.randint(1, 1000)
            elif values['amount_type'] == 'percentage':
                return '%s' % random.randint(1, 100)
            else:
                return random.choice([r'^invoice \d+ (\d+)$', r'xd no-(\d+)'])

        def get_account(random, values, **kwargs):
            """Get a random account depending on the company.

            :param random: seeded random number generator.
            :param values (dict): the values already selected for the record.
            :return (int): the id of the account randomly selected
            """
            company_id = self.env['account.reconcile.model'].browse(values['model_id']).company_id.id
            return random.choice(search_account_ids(company_id).ids)

        company_ids = self.env['res.company'].search([
            ('chart_template_id', '!=', False),
            ('id', 'in', self.env.registry.populated_models['res.company']),
        ])
        if not company_ids:
            return []
        return [
            ('model_id', populate.cartesian(self.env.registry.populated_models['account.reconcile.model'])),
            ('amount_type', populate.randomize(['fixed', 'percentage', 'regex'])),
            ('amount_string', populate.compute(get_amount)),
            ('account_id', populate.compute(get_account)),
        ]
