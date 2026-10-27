# -*- coding: utf-8 -*-
"""Classes defining the populate factory for Payments and related models."""
from odoo import models, fields
from odoo.tools import populate

from dateutil.relativedelta import relativedelta
import logging
import math
from functools import lru_cache

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    """Populate factory part for account.payment."""

    _inherit = "account.payment"

    _populate_sizes = {
        'small': 100,
        'medium': 5000,
        'large': 50000,
    }

    _populate_dependencies = ['res.company', 'res.partner', 'account.journal']

    def _populate_factories(self):
        @lru_cache()
        def search_partner_ids(company_id):
            """Search all the partners that a company has access to.

            This method is cached, only one search is done per company_id.
            :param company_id (int): the company to search partners for.
            :return (list<int>): the ids of partner the company has access to.
            """
            return self.env['res.partner'].search([
                *self.env['res.partner']._check_company_domain(company_id),
                ('id', 'in', self.env.registry.populated_models['res.partner']),
            ]).ids

        @lru_cache()
        def search_journal_ids(company_id):
            """Search all the journal of a certain type for a company.

            This method is cached, only one search is done per company_id.
            :param company_id (int): the company to search journals for.
            :return (list<int>): the ids of the bank and cash journals of a company
            """
            return self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(company_id),
                ('type', 'in', ('cash', 'bank')),
            ]).ids

        @lru_cache()
        def search_payment_method_line_ids(payment_type, journal):
            """Search all the payment methods of a certain type.

            This method is cached, only one search is done per type.
            :param payment_type (str): the type of payment method. Valid values are customer and supplier.
            :param journal (int): the journal of the payment method.
            :return list<int>: list of ids of payment methods of the selected type
            """
            need_bank_account = self._get_method_codes_needing_bank_account()
            other_blacklist = ['sdd', 'bacs_dd']
            return self.env['account.payment.method.line'].search([
                ('journal_id', '=', journal),
                ('payment_method_id.payment_type', '=', payment_type),
                ('code', 'not in', need_bank_account + other_blacklist),
            ]).ids

        def get_partner(random, values, **kwargs):
            """Get a random partner depending on the company and the partner_type.

            The first 3/5 of the available partners are used as customer
            The last 3/5 of the available partners are used as suppliers
            It means 1/5 is both customer/supplier
            -> Same proportions as in account.move
            :param random: seeded random number generator.
            :param values (dict): the values already selected for the record.
            :return (int): the id of the partner randomly selected.
            """
            partner_type = values['partner_type']
            company_id = values['company_id']
            partner_ids = search_partner_ids(company_id)
            if partner_type == 'customer':
                return random.choice(partner_ids[:math.ceil(len(partner_ids)/5*2)])
            else:
                return random.choice(partner_ids[math.floor(len(partner_ids)/5*2):])

        def get_journal(random, values, **kwargs):
            """Get a random bank or cash journal depending on the company.

            :param random: seeded random number generator.
            :param values (dict): the values already selected for the record.
            :return (int): the id of the journal randomly selected
            """
            return random.choice(search_journal_ids(values['company_id']))

        def get_payment_method_line(random, values, **kwargs):
            """Get the payment method depending on the payment type.

            :param random: seeded random number generator.
            :param values (dict): the values already selected for the record.
            """
            return random.choice(search_payment_method_line_ids(values['payment_type'], values['journal_id']))

        company_ids = self.env['res.company'].search([
            ('chart_template', '!=', False),
            ('id', 'in', self.env.registry.populated_models['res.company']),
        ])
        if not company_ids:
            return []
        return [
            ('company_id', populate.cartesian(company_ids.ids)),
            ('payment_type', populate.cartesian(['inbound', 'outbound'])),
            ('partner_type', populate.cartesian(['customer', 'supplier'])),
            ('journal_id', populate.compute(get_journal)),
            ('payment_method_line_id', populate.compute(get_payment_method_line)),
            ('partner_id', populate.compute(get_partner)),
            ('amount', populate.randfloat(0, 1000)),
            ('date', populate.randdatetime(relative_before=relativedelta(years=-4))),
        ]

    def _populate(self, size):
        records = super()._populate(size)
        _logger.info('Validating Payments')
        records.move_id.filtered(lambda r: r.date < fields.Date.today()).action_post()
        return records
