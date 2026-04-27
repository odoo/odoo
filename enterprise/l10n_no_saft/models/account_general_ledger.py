# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools import SQL

import re


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)
        if self.env.company.account_fiscal_country_id.code == 'NO':
            options.setdefault('buttons', []).append({
                'name': _('SAF-T'),
                'sequence': 50,
                'action': 'export_file',
                'action_param': 'l10n_no_export_saft_to_xml',
                'file_export_type': _('XML')
            })

    @api.model
    def _l10n_no_prepare_saft_report_values(self, report, options):
        options['saft_allow_empty_address'] = self.env.company.country_code == 'NO'
        template_vals = self._saft_prepare_report_values(report, options)

        if not self.env.ref('l10n_no_saft.balance_account', raise_if_not_found=False):
            # The update to SAF-T 1.30 changed and added some templates. The module needs to be upgraded if those templates are not found
            raise RedirectWarning(
                message=_("The version for the SAF-T file has been updated. Please upgrade its module (l10n_no_saft) for the export to work properly."),
                action=self.env.ref('base.open_module_tree').id,
                button_text=_("Go to Apps"),
                additional_context={
                    'search_default_name': 'l10n_no_saft',
                    'search_default_extra': True,
                },
            )

        # The Norwegian version of the SAF-T asks for a standard tax code to be given. This code is only present in the name
        # or description (depending on the Odoo version) of the tax. The code, as set in Odoo, is the first digit in the name or description.
        # If no code is found, we set it to a default non-existant '02' tax code, as it was done since Odoo 13.
        # TODO Create a dedicated field for the standard tax code for Norwegian loca in master and change to take the code from the description in 17.0 and later
        for tax_vals in template_vals['tax_vals_list']:
            for word in re.split(r'\W+', tax_vals['description']):
                if word.isdigit():
                    tax_vals['standard_code'] = int(word)
                    break
            if not tax_vals.get('standard_code'):
                raise UserError(_("Please change your tax descriptions to include their Norwegian standard tax code, delimited by spaces.\n"
                    "It should be the first number in your description.\n"
                    "For example: 'Utgående mva lav sats 12%' => '33 Utgående mva lav sats 12%'"))

        # The Norwegian version of the SAF-T requires account code to be provided along with the opening/closing
        # credit/debit of customers and suppliers
        accounts_by_partners = self._l10n_no_saft_get_partners_accounts(report, options)

        for partner_vals in template_vals['customer_vals_list'] + template_vals['supplier_vals_list']:
            partner_id = partner_vals['partner'].id
            if partner_id in accounts_by_partners:
                partner_vals['accounts'] = list(accounts_by_partners[partner_id].values())

        template_vals.update({
            'xmlns': 'urn:StandardAuditFile-Taxation-Financial:NO',
            'file_version': '1.30',
            'accounting_basis': 'A',
        })
        return template_vals

    @api.model
    def l10n_no_export_saft_to_xml(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        template_vals = self._l10n_no_prepare_saft_report_values(report, options)
        file_data = report._generate_file_data_with_error_check(
            options,
            self.env['ir.qweb']._render,
            {'values': template_vals, 'template': 'l10n_no_saft.saft_template_inherit_l10n_no_saft', 'file_type': 'xml'},
            template_vals['errors'],
        )
        return file_data

    def _saft_get_account_type(self, account):
        # OVERRIDE account_saft/models/account_general_ledger
        if self.env.company.account_fiscal_country_id.code != 'NO':
            return super()._saft_get_account_type(account)
        return "GL"

    def _l10n_no_saft_get_partners_accounts(self, report, options):
        """Retrieve the accounts used for transactions with the different partners (customer/supplier).

        The Norwegian regulation (based on xsd file) requires a list of accounts for every partner, with starting and closing balances.
        The partner ledger in Odoo provides starting and closing balance for every partner, but it is account insensitive.
        So it is needed to fetch account lines in order to compute all of this, on account/partner basis.
        This is based on the Lithuanian method of the same name (next SAF-T needing this might do it in account_saft directly).

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
                CASE WHEN account_move_line.date <= %(date_to)s THEN SUM(account_move_line.balance) ELSE 0 END AS closing_balance
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
