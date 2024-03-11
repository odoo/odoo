# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import psycopg2
from . import models
from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

def _l10n_it_edi_add_accounts(env, company):
    """ Create the transition accounts """
    generated_accounts_ref = {}
    account_templates = {account_code: env.ref(f'l10n_it_edi_withholding.{account_code}') for account_code in ['1611', '2603']}
    try:
        with env.cr.savepoint():
            for account_code, account_template in account_templates.items():
                template_vals = [(account_template, company.chart_template_id._get_account_vals(company, account_template, account_code, {}))]
                generated_accounts_ref[account_template] = company.chart_template_id._create_records_with_xmlid('account.account', template_vals, company)
            _logger.info("Created withholding accounts for company: %s(%s).", company.name, company.id)
    except psycopg2.errors.UniqueViolation:
        generated_accounts_ref = {}
        _logger.error("Cash basis transition accounts already exist for company: %s(%s).", company.name, company.id)
    return generated_accounts_ref

def _l10n_it_edi_withholding_add_taxes(env, company):
    """ Create the new taxes on existing company """
    templates = env['account.tax.template']
    generated_taxes_ref = {}
    try:
        with env.cr.savepoint():
            for xml_id in (
                '20awi', '20vwi',
                '20awc', '20vwc',
                '23awo', '23vwo',
                '4vcp', '4acp',
                '4vinps', '4ainps'
            ):
                templates |= env.ref(f"l10n_it_edi_withholding.{xml_id}")
            generated_taxes_ref = templates._generate_tax(company)
            _logger.info("Created withholding taxes for company: %s(%s).", company.name, company.id)

            # Increase the sequence number of the old taxes multiplying it by 10 and adding 21
            # so that the withholding can have sequence=10 and the pension fund sequence=20
            offset = 21
            all_taxes = env['account.tax'].with_context(active_test=False).search([('company_id', '=', company.id)])
            for tax in all_taxes.filtered(lambda x: (x.sequence <= 20 and not x.l10n_it_pension_fund_type and not x.l10n_it_withholding_type)):
                if not tax.l10n_it_withholding_type and not tax.l10n_it_pension_fund_type:
                    tax.sequence += offset
            _logger.info("Increased sequence number of old taxes by %s for company: %s(%s).", offset, company.name, company.id)
    except psycopg2.errors.UniqueViolation:
        generated_taxes_ref = {}
        _logger.error("Withholding and Pension Fund taxes already exist for company: %s(%s).", company.name, company.id)

    return generated_taxes_ref

def _l10n_it_edi_setup_accounts_on_taxes(env, company, generated_taxes_ref, generated_accounts_ref):
    """ Setup the accounts on the taxes, after the accounts have been created """
    # Set the transition account
    for tax, value in generated_taxes_ref['account_dict']['account.tax'].items():
        transition_account = value['cash_basis_transition_account_id']
        if transition_account:
            tax.cash_basis_transition_account_id = generated_accounts_ref.get(transition_account)

    # The tax repartition lines accounts has already been generated from the template by l10n_it
    referenced_accounts = {}
    repartitions_dict = generated_taxes_ref['account_dict']['account.tax.repartition.line']
    for dummy, value_dict in repartitions_dict.items():
        account_template = value_dict['account_id']
        template_xml_id = account_template.get_external_id()[account_template.id]
        xml_id = template_xml_id.split('.')
        referenced_accounts[template_xml_id] = env.ref(f'{xml_id[0]}.{company.id}_{xml_id[1]}')

    # Set the tax repartition lines accounts on the generated taxes
    for repartition_line, value in repartitions_dict.items():
        template = value['account_id']
        if template:
            repartition_line.account_id = referenced_accounts[template.get_external_id()[template.id]]
    _logger.info("Cash Basis Transition Accounts and Repartition accounts on taxes for company: %s(%s).", company.name, company.id)

def _l10n_it_edi_withholding_post_init(cr, registry):
    """ Existing companies that have the Italian Chart of Accounts set """
    env = api.Environment(cr, SUPERUSER_ID, {})
    chart_template = env.ref('l10n_it.l10n_it_chart_template_generic')
    if chart_template:
        for company in env['res.company'].search([('chart_template_id', '=', chart_template.id)]):
            _logger.info("Company %s already has the Italian localization installed, updating...", company.name)
            generated_taxes_ref = _l10n_it_edi_withholding_add_taxes(env, company)
            generated_accounts_ref = {} if not generated_taxes_ref else _l10n_it_edi_add_accounts(env, company)
            if generated_accounts_ref:
                _l10n_it_edi_setup_accounts_on_taxes(env, company, generated_taxes_ref, generated_accounts_ref)
