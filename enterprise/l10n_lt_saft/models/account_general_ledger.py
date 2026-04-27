# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import SQL


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)
        if self.env.company.account_fiscal_country_id.code == 'LT':
            options.setdefault('buttons', []).append({
                'name': _('SAF-T'),
                'sequence': 50,
                'action': 'export_file',
                'action_param': 'l10n_lt_export_saft_to_xml',
                'file_export_type': _('XML')
            })

    @api.model
    def _l10n_lt_saft_prepare_report_values(self, report, options):
        template_vals = self._saft_prepare_report_values(report, options)

        # The lithuanian version of the SAF-T requires account code to be provided along with the opening/closing
        # credit/debit of customers and suppliers
        accounts_by_partners = self._l10n_lt_saft_get_partners_accounts(report, options)

        for partner_vals in template_vals['customer_vals_list'] + template_vals['supplier_vals_list']:
            partner_id = partner_vals['partner'].id
            if partner_id in accounts_by_partners:
                partner_vals['accounts'] = list(accounts_by_partners[partner_id].values())

        # The owners also need account codes
        template_vals['owner_accounts'] = self._l10n_lt_saft_get_owner_accounts()

        template_vals.update({
            # Special LT SAF-T date format: YYYY-MM-DDThh:mm:ss
            'today_str': fields.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            'xmlns': 'https://www.vmi.lt/cms/saf-t',
            'file_version': '2.01',
            'accounting_basis': 'K',  # K (accrual - when recorded) or P (cash - when received)
            'entity': "COMPANY",
            'nb_of_parts': 1,
            'part_nb': 1,
        })
        return template_vals

    def _l10n_lt_saft_get_owner_accounts(self):
        """Retrieve the account codes for every owners' account.
        Owners' account can be identified by their tag, i.e. account_account_tag_d_1_3

        :rtype: str
        :return: a string of the account codes, comma separated, for instance "303, 305, 308"
        """
        tag_id = self.env.ref('l10n_lt.account_account_tag_d_1_3').id
        owner_accounts = self.env["account.account"].search([
            *self.env['account.account']._check_company_domain(self.env.company.id),
            ('tag_ids', 'in', tag_id)
        ])
        return ", ".join([account.code for account in owner_accounts])

    def _l10n_lt_saft_get_partners_accounts(self, report, options):
        """Retrieve the accounts used for transactions with the different partners (customer/supplier).

        The Lithuanian regulation (based on xsd file) requires a list of accounts for every partner, with starting and closing balances.
        The partner ledger in Odoo provides starting and closing balance for every partner, but it is account insensitive.
        So it is needed to fetch account lines in order to compute all of this, on account/partner basis.

        :rtype: dict
        :return: dictionary of partners' accounts with the account code and its opening/closing balance
        """
        date_from = fields.Date.to_date(options['date']['date_from'])
        date_to = fields.Date.to_date(options['date']['date_to'])
        # Fetch data from beginning
        query = report._get_report_query(options, 'from_beginning')
        account_alias = query.join(lhs_alias='account_move_line', lhs_column='account_id', rhs_table='account_account', rhs_column='id', link='account_id')
        account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)
        account_type = SQL.identifier(account_alias, 'account_type')

        # The balance dating from earlier periods are computed as opening
        # The balance up to the end of the current period are computed as closing
        self._cr.execute(SQL(
            '''
            SELECT DISTINCT
                account_move_line.partner_id,
                %(account_code)s AS code,
                CASE WHEN account_move_line.date < %(date_from)s THEN SUM(account_move_line.balance) ELSE 0 END AS opening_balance,
                CASE WHEN account_move_line.date <= %(date_to)s  THEN SUM(account_move_line.balance) ELSE 0 END AS closing_balance
            FROM %(table_references)s
            WHERE %(search_condition)s
            AND %(account_type)s IN ('asset_receivable', 'liability_payable')
            GROUP BY account_move_line.partner_id, %(account_code)s, account_move_line.date
            ''',
            account_code=account_code,
            date_from=date_from,
            date_to=date_to,
            table_references=query.from_clause,
            search_condition=query.where_clause,
            account_type=account_type,
        ))

        partners_accounts = {}
        for vals in self._cr.dictfetchall():
            partner_id = vals['partner_id']
            account_code = vals['code']
            partner_account_code_balances = partners_accounts.setdefault(partner_id, {}).setdefault(account_code, {
                'code': account_code,
                'opening_balance': 0,
                'closing_balance': 0,
            })
            partner_account_code_balances['opening_balance'] += vals['opening_balance']
            partner_account_code_balances['closing_balance'] += vals['closing_balance']

        return partners_accounts

    @api.model
    def l10n_lt_export_saft_to_xml(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        template_vals = self._l10n_lt_saft_prepare_report_values(report, options)
        file_data = report._generate_file_data_with_error_check(
            options,
            self.env['ir.qweb']._render,
            {'values': template_vals, 'template': 'l10n_lt_saft.saft_template_inherit_l10n_lt_saft', 'file_type': 'xml'},
            template_vals['errors'],
        )
        return file_data

    def _saft_get_account_type(self, account_type):
        # OVERRIDE account_saft/models/account_general_ledger
        if self.env.company.account_fiscal_country_id.code != 'LT':
            return super()._saft_get_account_type(account_type)

        # LT saf-t account types have to be identified as follows:
        # "IT" (Non-current assets), "TT" (Current assets), "NK" (Equity), "I" (Liabilities), "P" (Income), "S" (Costs), "KT" (Other)
        account_type_dict = {  # map between the account_types and the LT saf-t equivalent
            'asset_non_current': 'IT',
            'asset_fixed': 'IT',
            'asset_receivable': 'TT',
            'asset_cash': 'TT',
            'asset_current': 'TT',
            'asset_prepayments': 'TT',
            'equity': 'NK',
            'equity_unaffected': 'NK',
            'liability_payable': 'I',
            'liability_credit_card': 'I',
            'liability_current': 'I',
            'liability_non_current': 'I',
            'income': 'P',
            'income_other': 'P',
            'expense': 'S',
            'expense_depreciation': 'S',
            'expense_direct_cost': 'S',
            'off_balance': 'KT',
        }
        return account_type_dict[account_type]
