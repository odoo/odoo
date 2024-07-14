# -*- coding: utf-8 -*-

import calendar
from collections import namedtuple
from markupsafe import Markup
from itertools import chain

from dateutil.rrule import rrule, MONTHLY

from odoo import models, fields, registry, release, _
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools import get_lang
from odoo.tools.misc import street_split


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options)

        if self.env.company.account_fiscal_country_id.code != 'NL':
            return

        xaf_export_button = {
            'name': _('XAF'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'l10n_nl_get_xaf',
            'file_export_type': _('XAF'),
        }
        options['buttons'].append(xaf_export_button)

    def _l10n_nl_compute_period_number(self, date_str):
        date = fields.Date.from_string(date_str)
        return date.strftime('%y%m')[1:]

    def _l10n_nl_get_opening_balance_query(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        new_options = self._get_options_initial_balance(options)
        tables, where_clause, where_params = report._query_get(new_options, 'normal')
        return f"""
            SELECT acc.id AS account_id,
                   acc.code AS account_code,
                   COUNT(*) AS lines_count,
                   SUM(account_move_line.debit) AS sum_debit,
                   SUM(account_move_line.credit) AS sum_credit
              FROM {tables}
              JOIN account_account acc ON account_move_line.account_id = acc.id
             WHERE {where_clause}
               AND acc.include_initial_balance
          GROUP BY acc.id
        """, where_params

    def _l10n_nl_get_partner_values_query(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        tables, where_clause, where_params = report._query_get(options, 'strict_range')
        return f"""
               SELECT partner.id AS partner_id,
                      partner.name AS partner_name,
                      partner.commercial_company_name AS partner_commercial_company_name,
                      partner.commercial_partner_id AS partner_commercial_partner_id,
                      partner.is_company AS partner_is_company,
                      partner.phone AS partner_phone,
                      partner.email AS partner_email,
                      partner.website AS partner_website,
                      partner.vat AS partner_vat,
                      credit_limit.value_float AS partner_credit_limit,
                      partner.street AS partner_street,
                      partner.city AS partner_city,
                      partner.zip AS partner_zip,
                      partner.country_id AS partner_country_id,
                      partner.customer_rank AS partner_customer_rank,
                      partner.supplier_rank AS partner_supplier_rank,
                      partner.write_uid AS partner_write_uid,
                      TO_CHAR(partner.write_date, 'YYYY-MM-DD"T"HH24:MI:SS') AS partner_write_date,
                      country.code AS partner_country_code,
                      state.name AS partner_state_name,
                      res_partner_bank.id AS partner_bank_id,
                      res_partner_bank.sanitized_acc_number AS partner_sanitized_acc_number,
                      res_bank.bic AS partner_bic,
                      contact.name AS partner_contact_name
                 FROM res_partner partner
            LEFT JOIN res_country country ON partner.country_id = country.id
            LEFT JOIN res_country_state state ON partner.state_id = state.id
            LEFT JOIN res_partner_bank ON res_partner_bank.partner_id = partner.id
            LEFT JOIN res_bank ON res_partner_bank.bank_id = res_bank.id
            LEFT JOIN ir_property credit_limit ON credit_limit.res_id = 'res.partner,' || partner.id AND credit_limit.name = 'credit_limit'
    LEFT JOIN LATERAL (
                            SELECT contact.name
                              FROM res_partner contact
                             WHERE contact.parent_id = partner.id
                             LIMIT 1
                      ) AS contact ON TRUE
                WHERE partner.id IN (
                          SELECT DISTINCT account_move_line.partner_id
                            FROM {tables}
                           WHERE {where_clause}
                      )
             ORDER BY partner.id
        """, where_params

    def _l10n_nl_get_config_values_query(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        tables, where_clause, where_params = report._query_get(options, 'strict_range')
        return f"""
            SELECT COUNT(account_move_line.id) AS moves_count,
                   ROUND(SUM(account_move_line.debit), 2) AS moves_debit,
                   ROUND(SUM(account_move_line.credit), 2) AS moves_credit,
                   ARRAY_AGG(DISTINCT account_id) AS account_ids,
                   ARRAY_AGG(DISTINCT tax_line_id) AS tax_ids
              FROM {tables}
             WHERE {where_clause}
        """, where_params

    def _l10n_nl_get_transaction_values_query(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        tables, where_clause, where_params = report._query_get(options, 'strict_range')
        lang = self.env.user.lang or get_lang(self.env).code
        journal_name = f"COALESCE(journal.name->>'{lang}', journal.name->>'en_US')" if \
            self.pool['account.journal'].name.translate else 'journal.name'
        return f"""
            SELECT journal.id AS journal_id,
                   {journal_name} AS journal_name,
                   journal.code AS journal_code,
                   journal.type AS journal_type,
                   account.id AS account_id,
                   account.code AS account_code,
                   account_move_line__move_id.id AS move_id,
                   account_move_line__move_id.name AS move_name,
                   account_move_line__move_id.date AS move_date,
                   account_move_line__move_id.move_type IN ('out_invoice', 'out_refund', 'in_refund', 'in_invoice', 'out_receipt', 'in_receipt') AS move_is_invoice,
                   ROUND(account_move_line__move_id.amount_total, 2) AS move_amount,
                   account_move_line.id AS line_id,
                   account_move_line.name AS line_name,
                   account_move_line.display_type AS line_display_type,
                   account_move_line.ref AS line_ref,
                   account_move_line.date AS line_date,
                   account_move_line.full_reconcile_id AS line_reconcile_id,
                   account_move_line.partner_id AS line_partner_id,
                   account_move_line.move_id AS line_move_id,
                   account_move_line.move_name AS line_move_name,
                   ROUND(account_move_line.credit, 2) AS line_credit,
                   ROUND(account_move_line.debit, 2) AS line_debit,
                   ROUND(account_move_line.balance, 2) AS line_balance,
                   ROUND(account_move_line.amount_currency, 2) AS line_amount_currency,
                   reconcile.id AS line_reconcile_name,
                   currency.id AS line_currency_id,
                   currency2.id AS line_company_currency_id,
                   currency.name AS line_currency_name,
                   currency2.name AS line_company_currency_name
              FROM {tables}
              JOIN account_journal journal ON account_move_line.journal_id = journal.id
              JOIN account_account account ON account_move_line.account_id = account.id
         LEFT JOIN account_move account_move_line__move_id ON account_move_line__move_id.id = account_move_line.move_id
         LEFT JOIN account_full_reconcile reconcile ON account_move_line.full_reconcile_id = reconcile.id
         LEFT JOIN res_currency currency ON account_move_line.currency_id = currency.id
         LEFT JOIN res_currency currency2 ON account_move_line.company_currency_id = currency2.id
             WHERE {where_clause}
          ORDER BY account_move_line.journal_id, account_move_line.id
        """, where_params

    def _l10n_nl_get_header_values(self, options):
        def cust_sup_tp(customer, supplier):
            if supplier and customer:
                return 'B'
            if supplier:
                return 'C'
            if customer:
                return 'S'
            return 'O'

        def acc_tp(internal_group):
            if internal_group in ['income', 'expense']:
                return 'P'
            if internal_group in ['asset', 'liability']:
                return 'B'
            return 'M'

        def format_date_time(date):
            return date.strftime('%Y-%m-%dT%H:%M:%S')

        def check_forbidden_countries(report, res_list, iso_country_codes):
            forbidden_country_ids = {
                row['partner_country_id']
                for row in res_list
                if row['partner_country_code'] and row['partner_country_code'] not in iso_country_codes
            }

            if forbidden_country_ids and 'l10n_nl_skip_forbidden_countries' not in options:
                skip_action = report.export_file(dict(options, l10n_nl_skip_forbidden_countries=True), 'l10n_nl_get_xaf')
                skip_action['data']['model'] = self._name
                forbidden_country_names = ''.join([
                    '  •  ' + self.env['res.country'].browse(country_id).name + '\n'
                    for country_id in forbidden_country_ids
                ])
                raise RedirectWarning(
                    _('Some partners are located in countries forbidden in dutch audit reports.\n'
                      'Those countries are:\n\n'
                      '%s\n'
                      'If you continue, please note that the fields <country> and <taxRegistrationCountry> '
                      'will be skipped in the report for those partners.\n\n'
                      'Otherwise, please change the address of the partners located in those countries.\n', forbidden_country_names),
                    skip_action,
                    _('Continue and skip country fields'),
                )

        company = self.env.company
        report = self.env['account.report'].browse(options['report_id'])
        msgs = []

        if not company.vat:
            msgs.append(_('- VAT number'))
        if not company.country_id:
            msgs.append(_('- Country'))

        if msgs:
            msgs = [_('Some fields must be specified on the company:')] + msgs
            raise UserError('\n'.join(msgs))

        date_from = options['date']['date_from']
        date_to = options['date']['date_to']

        # Retrieve periods values
        periods = []
        Period = namedtuple('Period', 'number name date_from date_to')
        for period in rrule(freq=MONTHLY, bymonth=(), dtstart=fields.Date.from_string(date_from),
                            until=fields.Date.from_string(date_to)):
            period_from = fields.Date.to_string(period.date())
            period_to = period.replace(day=calendar.monthrange(period.year, period.month)[1])
            period_to = fields.Date.to_string(period_to.date())
            periods.append(Period(
                number=self._l10n_nl_compute_period_number(period_from),
                name=period.strftime('%B') + ' ' + date_from[0:4],
                date_from=period_from,
                date_to=period_to
            ))

        opening_lines = []
        lines_count = 0
        sum_debit = 0
        sum_credit = 0
        query, params = self._l10n_nl_get_opening_balance_query(options)
        self.env.cr.execute(query, params)
        for query_res in self.env.cr.dictfetchall():
            lines_count += query_res['lines_count']
            sum_debit += query_res['sum_debit']
            sum_credit += query_res['sum_credit']

            opening_lines.append({
                'id': query_res['account_id'],
                'account_code': query_res['account_code'],
                'balance': query_res['sum_debit'] - query_res['sum_credit'],
            })

        config_query, config_params = self._l10n_nl_get_config_values_query(options)
        self.env.cr.execute(config_query, config_params)
        moves_count, moves_debit, moves_credit, account_ids, tax_ids = self.env.cr.fetchone()

        header_values = {
            'opening_lines_count': lines_count,
            'opening_debit': round(sum_debit, 2),
            'opening_credit': round(sum_credit, 2),
            'opening_lines': opening_lines,
            'company': company,
            'account_data': [],
            'partner_data': [],
            'journal_data': [],  # We need the key to be present, but it must remain empty -> will be rendered manually.
            'tax_data': [],
            'periods': periods,
            'fiscal_year': date_from[0:4],
            'date_from': date_from,
            'date_to': date_to,
            'date_created': fields.Date.context_today(report),
            'software_version': release.version,
            'moves_count': moves_count,
            'moves_debit': round(moves_debit or 0, 2),
            'moves_credit': round(moves_credit or 0, 2),
        }

        # Aggregate partners' values
        partner_query, partner_params = self._l10n_nl_get_partner_values_query(options)
        self.env.cr.execute(partner_query, partner_params)
        partner_values = self.env.cr.dictfetchall()
        iso_country_codes = self.env['ir.attachment'].l10n_nl_reports_load_iso_country_codes()
        if iso_country_codes:
            check_forbidden_countries(report, partner_values, iso_country_codes)
        for row in partner_values:
            street_detail = street_split(row['partner_street'])
            header_values['partner_data'].append({
                'partner_id': row['partner_id'],
                # XAF XSD has maximum 50 characters for customer/supplier name
                'partner_name': (row['partner_name']
                                    or row['partner_commercial_company_name']
                                    or str(row['partner_commercial_partner_id'])
                                    or ('id: ' + str(row['partner_id'])))[:50],
                'partner_is_company': row['partner_is_company'],
                'partner_phone': row['partner_phone'] and row['partner_phone'][:30],
                'partner_email': row['partner_email'],
                'partner_website': row['partner_website'],
                'partner_vat': row['partner_vat'],
                'partner_credit_limit': row['partner_credit_limit'],
                'partner_street_name': street_detail.get('street_name'),
                'partner_street_number': street_detail.get('street_number', "")[:15],
                'partner_street_number2': street_detail.get('street_number2'),
                'partner_city': row['partner_city'],
                'partner_zip': row['partner_zip'] and row['partner_zip'][:10],
                'partner_state_name': row['partner_state_name'],
                'partner_country_id': row['partner_country_id'],
                'partner_country_code': row['partner_country_code'] if row['partner_country_code'] in iso_country_codes else None,
                'partner_write_uid': row['partner_write_uid'],
                'partner_xaf_userid': self.env['res.users'].browse(row['partner_write_uid']).l10n_nl_report_xaf_userid,
                'partner_write_date': row['partner_write_date'],
                'partner_customer_rank': row['partner_customer_rank'],
                'partner_supplier_rank': row['partner_supplier_rank'],
                'partner_type': cust_sup_tp(row['partner_customer_rank'], row['partner_supplier_rank']),
                'partner_contact_name': row['partner_contact_name'] and row['partner_contact_name'][:50],
                'partner_bank_data': {},
            })
            # Aggregate bank values for each partner
            if row['partner_bank_id'] and row['partner_bank_id'] not in header_values['partner_data'][-1]['partner_bank_data']:
                header_values['partner_data'][-1]['partner_bank_data'][row['partner_bank_id']] = {
                    'partner_sanitized_acc_number': row['partner_sanitized_acc_number'],
                    'partner_bic': row['partner_bic'],
                }

        # Aggregate accounts' values
        all_account_ids = list(set(account_ids or []) | {line['id'] for line in opening_lines})
        header_values['account_data'] = [
            {
                'account_code': account.code,
                'account_name': account.name,
                'account_type': acc_tp(account.internal_group),
                'account_write_date': format_date_time(account.write_date),
                'account_write_uid': account.write_uid,  # TODO: Remove in master, just keep 'account_xaf_userid'.
                'account_xaf_userid': account.write_uid.l10n_nl_report_xaf_userid,
            }
            for account in (self.env['account.account'].search([('id', 'in', all_account_ids)], order='code'))]

        # Aggregate taxes' values
        header_values['tax_data'] = [
            {'tax_id': tax.id, 'tax_name': tax.name}
            for tax in self.env['account.tax'].search([('id', 'in', tax_ids or [])], order='name')
        ]

        return header_values

    def _get_xaf_stream(self, options):
        new_options = self._get_options_sum_balance(options)
        header_values = self._l10n_nl_get_header_values(new_options)
        header_content = self.env['ir.qweb']._render('l10n_nl_reports.xaf_audit_file', header_values)
        header, footer = header_content.split('</transactions>')
        return chain(
            [header],
            self._get_xaf_lines_stream(new_options),
            [Markup("""
                </transactions>""") + footer],
        )

    def _get_xaf_lines_stream(self, options):
        def journal_type(journal_type):
            if journal_type == 'bank':
                return 'B'
            if journal_type == 'cash':
                return 'C'
            if journal_type == 'situation':
                return 'O'
            if journal_type in ['sale', 'sale_refund']:
                return 'S'
            if journal_type in ['purchase', 'purchase_refund']:
                return 'P'
            return 'Z'

        def amount_type(credit):
            return 'C' if credit else 'D'

        with registry(self.env.cr.dbname).cursor() as cr:
            self = self.with_env(self.env(cr=cr))
            batch_size = int(self.env['ir.config_parameter'].sudo().get_param('l10n_nl_reports.general_ledger_batch_size', 10**4))
            transaction_query, transaction_params = self._l10n_nl_get_transaction_values_query(options)
            self.env.cr.execute(transaction_query, transaction_params)

            journal_id, move_id = None, None
            while transaction_values := self.env.cr.dictfetchmany(batch_size):
                for row in transaction_values:
                    if row['journal_id'] != journal_id:
                        if journal_id is not None:
                            yield Markup("""
                        </transaction>
                    </journal>""")
                        journal_id = row['journal_id']
                        move_id = None
                        yield Markup("""
                    <journal>
                        <jrnID>{journal_code}</jrnID>
                        <desc>{journal_name}</desc>
                        <jrnTp>{journal_type}</jrnTp>""").format(
                            journal_code=row['journal_code'],
                            journal_name=row['journal_name'],
                            journal_type=journal_type(row['journal_type']))
                    if row['move_id'] != move_id:
                        if move_id is not None:
                            yield Markup("""
                        </transaction>""")
                        move_id = row['move_id']
                        yield Markup("""
                        <transaction>
                            <nr>{move_id}</nr>
                            <desc>{move_name}</desc>
                            <periodNumber>{period_number}</periodNumber>
                            <trDt>{move_date}</trDt>
                            <amnt>{move_amount}</amnt>""").format(
                                move_id=row['move_id'],
                                move_name=row['move_name'],
                                period_number=self._l10n_nl_compute_period_number(row['move_date']),
                                move_date=row['move_date'],
                                move_amount=row['move_amount'])
                    yield Markup("""
                            <trLine>
                                <nr>{line_id}</nr>
                                <accID>{account_code}</accID>
                                <docRef>{line_ref}</docRef>
                                <effDate>{line_date}</effDate>
                                <desc>{line_name}</desc>
                                <amnt>{amount}</amnt>
                                <amntTp>{amount_type}</amntTp>
                                {matching}
                                {partner}
                                {inv_ref}""").format(
                                    line_id=row['line_id'],
                                    account_code=row['account_code'],
                                    line_ref=row['line_ref'] and row['line_ref'][:999] or '/',
                                    line_date=row['line_date'],
                                    line_name=row['line_name'],
                                    amount=row['line_credit'] or row['line_debit'],
                                    amount_type=amount_type(row['line_credit']),
                                    matching=row['line_reconcile_id'] and Markup("<recRef>{}</recRef>").format(row['line_reconcile_id']) or '',
                                    partner=row['line_partner_id'] and Markup("<custSupID>{}</custSupID>").format(row['line_partner_id']) or '',
                                    inv_ref=row['move_is_invoice'] and Markup("<invRef>{}</invRef>").format(row['line_move_name']) or '')
                    if row['line_currency_id'] or row['line_company_currency_id']:
                        yield Markup("""
                                <currency>
                                    <curCode>{code}</curCode>
                                    <curAmnt>{amount}</curAmnt>
                                </currency>""").format(
                                    code=row['line_currency_name'] if row['line_currency_id'] else row['line_company_currency_name'],
                                    amount=row['line_amount_currency'] if row['line_currency_id'] else row['line_balance'])
                    yield Markup("""
                            </trLine>""")
            if move_id is not None:
                yield Markup("""
                        </transaction>
                    </journal>""")

    def l10n_nl_get_xaf(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        return {
            'file_name': report.get_default_report_filename(options, 'xaf'),
            'file_content': (x.encode() for x in self._get_xaf_stream(options)),
            'file_type': 'xaf',
        }
