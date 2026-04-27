# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, Command, models, _

from odoo.addons.account.models.chart_template import template, TAX_TAG_DELIMITER


_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _post_load_data(self, template_code, company, template_data):
        super()._post_load_data(template_code, company, template_data)
        self._load_payroll_accounts(template_code, company)

    def _load_payroll_accounts(self, template_code, companies):
        config_method = getattr(self, f'_configure_payroll_account_{template_code}', None)
        if config_method:
            config_method(companies)

    @api.model
    def _configure_payroll_account(self, companies, country_code, account_codes=None, rules_mapping=None, default_account=None):
        # companies: Recordset of the companies to configure
        # country_code: list containing all the needed accounts code
        # rule_mapping: dictionary of the debit/credit accounts and tax tags for each related rule
        # default_account: Defaut account to specify on the created journals
        structures = self.env['hr.payroll.structure'].search([('country_id.code', '=', country_code)])
        AccountAccount = self.env['account.account']
        rule_tag_mapper = self._get_tag_mapper(self.env['res.country'].search([('code', '=', country_code)]).id)
        if not companies or not structures:
            return
        for company in companies:
            self = self.with_company(company)

            # Enable SEPA batch payment by default for some countries
            if company.country_id.code in ['BE', 'CH']:
                company.batch_payroll_move_lines = True
            accounts = {}
            for code in account_codes:
                account = AccountAccount.with_company(company).search([
                    *AccountAccount._check_company_domain(company),
                    ('code', '=like', '%s%%' % code)], limit=1)
                if not account:
                    _logger.warning("Payroll configuration: Missing account %s", code)
                accounts[code] = account

            journal = self.ref('hr_payroll_account_journal')
            if not journal.default_account_id and default_account:
                journal.default_account_id = accounts[default_account].id
            structures.with_company(company).journal_id = journal

            for rule, rule_mapping in rules_mapping.items():
                vals = {}
                if 'credit' in rule_mapping:
                    vals['account_credit'] = accounts.get(rule_mapping['credit'], AccountAccount).id
                if 'debit' in rule_mapping:
                    vals['account_debit'] = accounts.get(rule_mapping['debit'], AccountAccount).id
                if 'debit_tags' in rule_mapping:
                    vals['debit_tag_ids'] = [Command.set(rule_tag_mapper(*rule_mapping['debit_tags'].split(TAX_TAG_DELIMITER)))]
                if 'credit_tags' in rule_mapping:
                    vals['credit_tag_ids'] = [Command.set(rule_tag_mapper(*rule_mapping['credit_tags'].split(TAX_TAG_DELIMITER)))]
                if vals:
                    rule.with_company(company).write(vals)

    @template(model='account.journal')
    def _get_payroll_account_journal(self, template_code):
        return {
            'hr_payroll_account_journal': {
                'name': _("Salaries"),
                'code': _("SLR"),
                'type': 'general',
                'sequence': 99,
            },
        }

    @template(model='hr.payroll.structure')
    def _get_payroll_structure(self, template_code):
        return {
            'hr_payroll.structure_002': {
                'journal_id': 'hr_payroll_account_journal',
            },
            'hr_payroll.structure_worker_001': {
                'journal_id': 'hr_payroll_account_journal',
            },
            'hr_payroll.default_structure': {
                'journal_id': 'hr_payroll_account_journal',
            },
        }

    def _get_demo_data(self, company):
        demo_data = super()._get_demo_data(company)
        if not self.env['account.account'].search_count(
            [
                *self.env['account.account']._check_company_domain(company),
                ('code', '=', "123456"),
            ],
            limit=1,
        ):
            account_data = demo_data.setdefault('account.account', {})
            account_data['hr_payslip_account'] = {
                'name': _("Account Payslip Houserental"),
                'code': "123456",
                'account_type': 'liability_payable',
                'reconcile': True,
            }
        if self.env.ref('hr_payroll.hr_salary_rule_houserentallowance1', raise_if_not_found=False) and self.ref('hr_payslip_account', raise_if_not_found=False):
            demo_data['hr.salary.rule'] = {
                'hr_payroll.hr_salary_rule_houserentallowance1': {
                    'account_debit': 'hr_payslip_account',
                    'account_credit': 'hr_payslip_account',
                }
            }
        if self.env.ref('hr_payroll.structure_003', raise_if_not_found=False) and self.ref('hr_payroll_account_journal', raise_if_not_found=False):
            demo_data['hr.payroll.structure'] = {
                'hr_payroll.structure_003': {
                    'journal_id': 'hr_payroll_account_journal',
                }
            }

        return demo_data
