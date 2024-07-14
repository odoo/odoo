# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
from collections import defaultdict

from odoo.addons.account_reports.models.account_report import AccountReportFileDownloadException
from odoo.exceptions import UserError
from odoo.tools import float_repr, get_lang

from odoo import api, fields, models, release, _


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_line_postprocessor(self, report, options, lines, warnings=None):
        lines = super()._custom_line_postprocessor(report, options, lines, warnings=warnings)
        if warnings is not None:
            company = self.env.company
            args = []
            if not company.company_registry:
                args.append(_('the Company ID'))
            if not (company.phone or company.mobile):
                args.append(_('the phone or mobile number'))
            if not (company.zip or company.city):
                args.append(_('the city or zip code'))

            if args:
                warnings['account_saft.company_data_warning'] = {
                    'alert_type': 'warning',
                    'args': _(', ').join(args),
                }

        return lines

    ####################################################
    # ACTIONS
    ####################################################

    def action_fill_company_details(self, options, params):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Missing company details.'),
            'res_model': 'res.company',
            'views': [(False, 'form')],
            'res_id': self.env.company.id,
        }

    def _saft_get_account_type(self, account_type):
        """To be overridden if specific account types are needed.
        Some countries need to specify an account type, unique to the saf-t report.

        :return: False if no account type needed, otherwise a string with the account type"""
        return False

    @api.model
    def _saft_fill_report_general_ledger_values(self, report, options, values):
        res = {
            'total_debit_in_period': 0.0,
            'total_credit_in_period': 0.0,
            'account_vals_list': [],
            'journal_vals_list': [],
            'move_vals_list': [],
            'tax_detail_per_line_map': {},
        }

        # Fill 'account_vals_list'.
        accounts_results = self._query_values(report, options)
        rslts_array = tuple((account, res_col_gr[options['single_column_group']]) for account, res_col_gr in accounts_results)
        init_bal_res = self._get_initial_balance_values(report, tuple(account.id for account, results in rslts_array), options)
        initial_balances_map = {}
        initial_balance_gen = ((account, init_bal_dict.get(options['single_column_group'])) for account, init_bal_dict in init_bal_res.values())
        for account, initial_balance in initial_balance_gen:
            initial_balances_map[account.id] = initial_balance
        for account, results in rslts_array:
            account_init_bal = initial_balances_map[account.id]
            account_un_earn = results.get('unaffected_earnings', {})
            account_balance = results.get('sum', {})
            opening_balance = account_init_bal.get('balance', 0.0) + account_un_earn.get('balance', 0.0)
            closing_balance = account_balance.get('balance', 0.0)
            res['account_vals_list'].append({
                'account': account,
                'account_type': dict(self.env['account.account']._fields['account_type']._description_selection(self.env))[account.account_type],
                'saft_account_type': self._saft_get_account_type(account.account_type),
                'opening_balance': opening_balance,
                'closing_balance': closing_balance,
            })
        # Fill 'total_debit_in_period', 'total_credit_in_period', 'move_vals_list'.
        tables, where_clause, where_params = report._query_get(options, 'strict_range')
        lang = self.env.user.lang or get_lang(self.env).code
        tax_name = f"COALESCE(tax.name->>'{lang}', tax.name->>'en_US')" if \
            self.pool['account.tax'].name.translate else 'tax.name'
        journal_name = f"COALESCE(journal.name->>'{lang}', journal.name->>'en_US')" if \
            self.pool['account.journal'].name.translate else 'journal.name'
        uom_name = f"""COALESCE(uom.name->>'{lang}', uom.name->>'en_US')"""
        query = f'''
            SELECT
                account_move_line.id,
                account_move_line.display_type,
                account_move_line.date,
                account_move_line.name,
                account_move_line.account_id,
                account_move_line.partner_id,
                account_move_line.currency_id,
                account_move_line.amount_currency,
                account_move_line.debit,
                account_move_line.credit,
                account_move_line.balance,
                account_move_line.tax_line_id,
                account_move_line.quantity,
                account_move_line.price_unit,
                account_move_line.product_id,
                account_move_line.product_uom_id,
                account_move.id                             AS move_id,
                account_move.name                           AS move_name,
                account_move.move_type                      AS move_type,
                account_move.create_date                    AS move_create_date,
                account_move.invoice_date                   AS move_invoice_date,
                account_move.invoice_origin                 AS move_invoice_origin,
                account_move.statement_line_id              AS move_statement_line_id,
                tax.id                                      AS tax_id,
                {tax_name}                                  AS tax_name,
                tax.amount                                  AS tax_amount,
                tax.amount_type                             AS tax_amount_type,
                journal.id                                  AS journal_id,
                journal.code                                AS journal_code,
                {journal_name}                              AS journal_name,
                journal.type                                AS journal_type,
                account.account_type                        AS account_type,
                currency.name                               AS currency_code,
                product.default_code                        AS product_default_code,
                {uom_name}                                  AS product_uom_name
            FROM ''' + tables + '''
            JOIN account_move ON account_move.id = account_move_line.move_id
            JOIN account_journal journal ON journal.id = account_move_line.journal_id
            JOIN account_account account ON account.id = account_move_line.account_id
            JOIN res_currency currency ON currency.id = account_move_line.currency_id
            LEFT JOIN product_product product ON product.id = account_move_line.product_id
            LEFT JOIN uom_uom uom ON uom.id = account_move_line.product_uom_id
            LEFT JOIN account_tax tax ON tax.id = account_move_line.tax_line_id
            WHERE ''' + where_clause + '''
            ORDER BY account_move_line.date, account_move_line.id
        '''
        self._cr.execute(query, where_params)

        journal_vals_map = {}
        move_vals_map = {}
        inbound_types = self.env['account.move'].get_inbound_types(include_receipts=True)
        while True:
            batched_line_vals = self._cr.dictfetchmany(10**4)
            if not batched_line_vals:
                break
            for line_vals in batched_line_vals:
                line_vals['rate'] = abs(line_vals['amount_currency']) / abs(line_vals['balance']) if line_vals['balance'] else 1.0
                line_vals['tax_detail_vals_list'] = []

                journal_vals_map.setdefault(line_vals['journal_id'], {
                    'id': line_vals['journal_id'],
                    'name': line_vals['journal_name'],
                    'type': line_vals['journal_type'],
                    'move_vals_map': {},
                })
                journal_vals = journal_vals_map[line_vals['journal_id']]

                move_vals = {
                    'id': line_vals['move_id'],
                    'name': line_vals['move_name'],
                    'type': line_vals['move_type'],
                    'sign': -1 if line_vals['move_type'] in inbound_types else 1,
                    'invoice_date': line_vals['move_invoice_date'],
                    'invoice_origin': line_vals['move_invoice_origin'],
                    'date': line_vals['date'],
                    'create_date': line_vals['move_create_date'],
                    'partner_id': line_vals['partner_id'],
                    'journal_type': line_vals['journal_type'],
                    'statement_line_id': line_vals['move_statement_line_id'],
                    'line_vals_list': [],
                }
                move_vals_map.setdefault(line_vals['move_id'], move_vals)
                journal_vals['move_vals_map'].setdefault(line_vals['move_id'], move_vals)

                move_vals = move_vals_map[line_vals['move_id']]
                move_vals['line_vals_list'].append(line_vals)

                # Track the total debit/period of the whole period.
                res['total_debit_in_period'] += line_vals['debit']
                res['total_credit_in_period'] += line_vals['credit']

                res['tax_detail_per_line_map'][line_vals['id']] = line_vals

        # Fill 'journal_vals_list'.
        for journal_vals in journal_vals_map.values():
            journal_vals['move_vals_list'] = list(journal_vals.pop('move_vals_map').values())
            res['journal_vals_list'].append(journal_vals)
            res['move_vals_list'] += journal_vals['move_vals_list']

        # Add newly computed values to the final template values.
        values.update(res)

    @api.model
    def _saft_fill_report_tax_details_values(self, report, options, values):
        tax_vals_map = {}

        tables, where_clause, where_params = report._query_get(options, 'strict_range')
        tax_details_query, tax_details_params = self.env['account.move.line']._get_query_tax_details(tables, where_clause, where_params)
        if self.pool['account.tax'].name.translate:
            lang = self.env.user.lang or get_lang(self.env).code
            tax_name = f"COALESCE(tax.name->>'{lang}', tax.name->>'en_US')"
        else:
            tax_name = 'tax.name'
        self._cr.execute(f'''
            SELECT
                tax_detail.base_line_id,
                tax_line.currency_id,
                tax.id AS tax_id,
                tax.type_tax_use AS tax_type,
                tax.amount_type AS tax_amount_type,
                {tax_name} AS tax_name,
                tax.amount AS tax_amount,
                tax.create_date AS tax_create_date,
                SUM(tax_detail.tax_amount) AS amount,
                SUM(tax_detail.tax_amount) AS amount_currency
            FROM ({tax_details_query}) AS tax_detail
            JOIN account_move_line tax_line ON tax_line.id = tax_detail.tax_line_id
            JOIN account_tax tax ON tax.id = tax_detail.tax_id
            GROUP BY tax_detail.base_line_id, tax_line.currency_id, tax.id
        ''', tax_details_params)
        for tax_vals in self._cr.dictfetchall():
            line_vals = values['tax_detail_per_line_map'][tax_vals['base_line_id']]
            line_vals['tax_detail_vals_list'].append({
                **tax_vals,
                'rate': line_vals['rate'],
                'currency_code': line_vals['currency_code'],
            })
            tax_vals_map.setdefault(tax_vals['tax_id'], {
                'id': tax_vals['tax_id'],
                'name': tax_vals['tax_name'],
                'amount': tax_vals['tax_amount'],
                'amount_type': tax_vals['tax_amount_type'],
                'type': tax_vals['tax_type'],
                'create_date': tax_vals['tax_create_date']
            })

        # Fill 'tax_vals_list'.
        values['tax_vals_list'] = list(tax_vals_map.values())

    @api.model
    def _saft_fill_report_partner_ledger_values(self, options, values):
        res = {
            'customer_vals_list': [],
            'supplier_vals_list': [],
            'partner_detail_map': defaultdict(lambda: {
                'type': False,
                'addresses': [],
                'contacts': [],
            }),
        }

        all_partners = self.env['res.partner']

        # Fill 'customer_vals_list' and 'supplier_vals_list'
        report = self.env.ref('account_reports.partner_ledger_report')
        new_options = report.get_options(options)
        new_options['account_type'] = [
            {'id': 'trade_receivable', 'selected': True},
            {'id': 'non_trade_receivable', 'selected': True},
            {'id': 'trade_payable', 'selected': True},
            {'id': 'non_trade_payable', 'selected': True},
        ]
        handler = self.env['account.partner.ledger.report.handler']
        partners_results = handler._query_partners(new_options)
        partner_vals_list = []
        rslts_array = tuple((partner, res_col_gr[options['single_column_group']]) for partner, res_col_gr in partners_results)
        init_bal_res = handler._get_initial_balance_values(tuple(partner.id for partner, results in rslts_array if partner), options)

        initial_balances_map = {}
        initial_balance_gen = ((partner_id, init_bal_dict.get(options['single_column_group'])) for partner_id, init_bal_dict in init_bal_res.items())

        for partner_id, initial_balance in initial_balance_gen:
            initial_balances_map[partner_id] = initial_balance
        for partner, results in rslts_array:
            # Ignore Falsy partner.
            if not partner:
                continue

            all_partners |= partner
            partner_init_bal = initial_balances_map[partner.id]

            opening_balance = partner_init_bal.get('balance', 0.0)
            closing_balance = results.get('balance', 0.0)
            partner_vals_list.append({
                'partner': partner,
                'opening_balance': opening_balance,
                'closing_balance': closing_balance,
            })

        if all_partners:
            domain = [('partner_id', 'in', tuple(all_partners.ids))]
            tables, where_clause, where_params = report._query_get(new_options, 'strict_range', domain=domain)
            self._cr.execute(f'''
                SELECT
                    account_move_line.partner_id,
                    SUM(account_move_line.balance)
                FROM {tables}
                JOIN account_account account ON account.id = account_move_line.account_id
                WHERE {where_clause}
                AND account.account_type IN ('asset_receivable', 'liability_payable')
                GROUP BY account_move_line.partner_id
            ''', where_params)

            for partner_id, balance in self._cr.fetchall():
                res['partner_detail_map'][partner_id]['type'] = 'customer' if balance >= 0.0 else 'supplier'

        for partner_vals in partner_vals_list:
            partner_id = partner_vals['partner'].id
            if res['partner_detail_map'][partner_id]['type'] == 'customer':
                res['customer_vals_list'].append(partner_vals)
            elif res['partner_detail_map'][partner_id]['type'] == 'supplier':
                res['supplier_vals_list'].append(partner_vals)

        # Fill 'partner_detail_map'.
        all_partners |= values['company'].partner_id
        partner_addresses_map = defaultdict(dict)
        partner_contacts_map = defaultdict(lambda: self.env['res.partner'])

        def _track_address(current_partner, partner):
            if partner.zip and partner.city:
                address_key = (partner.zip, partner.city)
                partner_addresses_map[current_partner][address_key] = partner

        def _track_contact(current_partner, partner):
            partner_contacts_map[current_partner] |= partner

        for partner in all_partners:
            _track_address(partner, partner)
            # For individual partners, they are their own ContactPerson.
            # For company partners, the child contact with lowest ID is the ContactPerson.
            # For the current company, all child contacts are ContactPersons
            # (to give users flexibility to indicate several ContactPersons).
            if partner.is_company:
                children = partner.child_ids.filtered(lambda p: p.type == 'contact' and p.active and not p.is_company).sorted('id')
                if partner == values['company'].partner_id:
                    if not children:
                        values['errors'].append({
                            'message': _('Please define one or more Contacts belonging to your company.'),
                            'action_text': _('Define Contact(s)'),
                            'action_name': 'action_open_partner_company',
                            'action_params': partner.id,
                            'critical': True,
                        })
                    for child in children:
                        _track_contact(partner, child)
                elif children:
                    _track_contact(partner, children[0])
            else:
                _track_contact(partner, partner)

        no_partner_address = self.env['res.partner']
        for partner in all_partners:
            res['partner_detail_map'][partner.id].update({
                'partner': partner,
                'addresses': list(partner_addresses_map[partner].values()),
                'contacts': partner_contacts_map[partner],
            })
            if not res['partner_detail_map'][partner.id]['addresses']:
                no_partner_address |= partner

        if no_partner_address:
            values['errors'].append({
                'message': _('Some partners are missing at least one address (Zip/City).'),
                'action_text': _('View Partners'),
                'action_name': 'action_open_partners',
                'action_params': no_partner_address.ids,
            })

        # Add newly computed values to the final template values.
        values.update(res)

    @api.model
    def _saft_prepare_report_values(self, report, options):
        def format_float(amount, digits=2):
            return float_repr(amount or 0.0, precision_digits=digits)

        def format_date(date_str, formatter):
            date_obj = fields.Date.to_date(date_str)
            return date_obj.strftime(formatter)

        if len(options["column_groups"]) > 1:
            raise UserError(_("SAF-T is only compatible with one column group."))

        company = self.env.company
        options["single_column_group"] = tuple(options["column_groups"].keys())[0]

        template_values = {
            'company': company,
            'xmlns': '',
            'file_version': 'undefined',
            'accounting_basis': 'undefined',
            'today_str': fields.Date.to_string(fields.Date.context_today(self)),
            'software_version': release.version,
            'date_from': options['date']['date_from'],
            'date_to': options['date']['date_to'],
            'format_float': format_float,
            'format_date': format_date,
            'errors': [],
        }
        self._saft_fill_report_general_ledger_values(report, options, template_values)
        self._saft_fill_report_tax_details_values(report, options, template_values)
        self._saft_fill_report_partner_ledger_values(options, template_values)
        return template_values

    def _saft_generate_file_data_with_error_check(self, report, options, values, template_ref):
        """ Checks for critical errors (i.e. errors that would cause the rendering to fail) in template values .
            If at least one error is critical, the 'account.report.file.download.error.wizard' wizard is opened
            before rendering the file, so they can be fixed.
            If there are only non-critical errors, the wizard is opened after the file has been generated,
            allowing the user to download it anyway.

            :param dict options: The report options.
            :param dict values: The template values, returned as a dict by '_saft_prepare_report_values()',
                                where the 'errors' key contains a list of errors in the following format:
                'errors': [
                    {
                        'message': The error message to be displayed in the wizard,
                        'action_text': The text of the action button,
                        'action_name': The name of the method called to handle the issue,
                        'action_params': The parameter(s) passed to the 'action_name' method,
                        'critical': Whether the error will cause the file generation to crash (Boolean).
                    },
                    {...},
                ]
            :param str template_ref: The xmlid of the template to be used in the rendering.
            :returns: The data that will be used by the file generator.
            :rtype: dict
        """

        if any(error.get('critical') for error in values['errors']):
            # Errors are sorted in order to show the critical ones first.
            sorted_errors = sorted(values['errors'], key=lambda error: not error.get('critical'))
            raise AccountReportFileDownloadException(sorted_errors)

        content = self.env['ir.qweb']._render(template_ref, values)

        file_data = {
            'file_name': report.get_default_report_filename(options, 'xml'),
            'file_content': re.sub(r'\n\s*\n', '\n', content).encode(),
            'file_type': 'xml',
        }

        if values['errors']:
            raise AccountReportFileDownloadException(values['errors'], file_data)

        return file_data
