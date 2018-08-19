# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import pycompat, float_is_zero
from odoo.tools.misc import formatLang


class AccountReconciliation(models.AbstractModel):
    _name = 'account.reconciliation.widget'

    ####################################################
    # Search propositions
    ####################################################

    @api.model
    def _get_matching_amls_query(self, st_lines, excluded_ids=None):
        ''' Base query used by the matching rules.
        Main things about this huge query:
        - Try to join the res.partner table:
            1) On st_line.partner_id.
            2) On partner_id found on a res.partner.bank sharing the same account number.
            3) On a partner having the same case insensitive name.
        - Basic filters on account_move_line.

        :param st_lines:        Account.bank.statement.lines recordset.
        :param excluded_ids:    Account.move.lines to exclude.
        :return:                (query, params)
        '''
        params = [tuple(st_lines.ids)]

        # N.B: The first part of the CASE is about 'blue lines' while the second part is about 'black lines'.
        query = '''
            SELECT
                st_line.id                          AS id,
                aml.id                              AS aml_id,
                aml.currency_id                     AS aml_currency_id,
                aml.amount_residual                 AS aml_amount_residual,
                aml.amount_residual_currency        AS aml_amount_residual_currency
            FROM account_bank_statement_line st_line
            LEFT JOIN account_journal journal       ON journal.id = st_line.journal_id
            LEFT JOIN res_company company           ON company.id = st_line.company_id
            LEFT JOIN res_partner_bank bank         ON bank.id = st_line.bank_account_id OR bank.acc_number = st_line.account_number
            LEFT JOIN res_partner partner           ON (
                CASE WHEN st_line.partner_id IS NOT NULL THEN
                    partner.id = st_line.partner_id
                WHEN bank.partner_id IS NOT NULL THEN
                    partner.id = bank.partner_id
                ELSE
                    partner.name ILIKE st_line.partner_name
                END
            )
            , account_move_line aml
            LEFT JOIN res_company aml_company       ON aml_company.id = aml.company_id
            LEFT JOIN account_account aml_account   ON aml_account.id = aml.account_id
            WHERE st_line.id IN %s
                AND aml.company_id = st_line.company_id
                AND aml.statement_id IS NULL
                
                AND (
                    company.account_bank_reconciliation_start IS NULL
                    OR
                    aml.date > company.account_bank_reconciliation_start
                )
                
                AND CASE WHEN journal.default_credit_account_id IS NOT NULL
                    AND journal.default_debit_account_id IS NOT NULL
                    THEN
                        (
                            aml.account_id IN (journal.default_credit_account_id, journal.default_debit_account_id)
                            AND aml.payment_id IS NOT NULL
                        )
                        OR
                        (
                            aml_account.reconcile IS TRUE
                            AND aml.reconciled IS FALSE
                        )
                    END
        '''

        if excluded_ids:
            query += 'AND aml.id NOT IN %s'
            params.append(tuple(excluded_ids))
        return query, params

    @api.model
    def _get_matching_amls_invoice_rule(self, st_lines, excluded_ids=None):
        ''' RULE 1: Match an account.move.line automatically if linked to an invoice having a number or reference quite
        similar.

        This rule automatically match when invoice_reference match when:
        - matching only one invoice.
        - matching multiple invoices but having the same total amount residual.

        :param st_lines:        Account.bank.statement.lines recordset.
        :param excluded_ids:    Account.move.lines to exclude.
        :return:                (query, params, automatic_match_func)
        '''

        def automatic_match_func(st_line, fetched_amls):
            # Match only one invoice.
            if len(fetched_amls) == 1:
                return True

            # Match multiple invoices but having the same total amount residual.
            total_residual = sum(aml['aml_currency_id'] and aml['aml_amount_residual_currency'] or aml['aml_amount_residual'] for aml in fetched_amls)
            line_residual = st_line.currency_id and st_line.amount_currency or st_line.amount
            line_currency = st_line.currency_id or st_line.journal_id.currency_id or st_line.company_id.currency_id
            return float_is_zero(total_residual - line_residual, precision_rounding=line_currency.rounding)

        query, params = self._get_matching_amls_query(st_lines, excluded_ids=excluded_ids)

        # Join the account_invoice table.
        query = query.replace(
            'account_move_line aml',
            '''
            account_move_line aml
            LEFT JOIN account_move move                 ON move.id = aml.move_id
            LEFT JOIN account_invoice invoice           ON invoice.move_name = move.name
            '''
        )

        # Add where clause.
        # N.B: invoice_reference could be a list of invoice reference/number (e.g. 'INV/2018/0001,INV/2018/0002').
        query += '''
            AND invoice.state = 'open'
            AND CASE WHEN st_line.amount >= 0.0 THEN
                    invoice.type IN ('out_invoice', 'in_refund')
                ELSE
                    invoice.type IN ('in_invoice', 'out_refund')
                END
            AND (
                REGEXP_REPLACE(st_line.name, '[^0-9]', '', 'g') ~ REGEXP_REPLACE(invoice.number, '[^0-9]', '', 'g')
                OR (
                    invoice.reference IS NOT NULL
                    AND
                    REGEXP_REPLACE(st_line.name, '[^0-9]', '', 'g') ~ REGEXP_REPLACE(invoice.reference, '[^0-9]', '', 'g')
                )
            )
            AND CASE WHEN partner.id IS NOT NULL THEN
                    invoice.partner_id = partner.id
                ELSE
                    TRUE
                END
        '''
        return query, params, automatic_match_func

    @api.model
    def _get_matching_amls_amount_rule(self, st_lines, excluded_ids=None):
        ''' RULE 2: Match one or more account.move.lines automatically if either the statement line has exactly the same amount
        or either the statement line matchs a single line having a greater or equals amount.

        This only work if a partner has been found on the statement line.

        :param st_lines:        Account.bank.statement.lines recordset.
        :param excluded_ids:    Account.move.lines to exclude.
        :return:                (query, params, automatic_match_func)
        '''

        def automatic_match_func(st_line, fetched_amls):
            total_residual = sum(aml['aml_currency_id'] and aml['aml_amount_residual_currency'] or aml['aml_amount_residual'] for aml in fetched_amls)
            line_residual = st_line.currency_id and st_line.amount_currency or st_line.amount
            line_currency = st_line.currency_id or st_line.journal_id.currency_id or st_line.company_id.currency_id

            # Match the total residual amount.
            if float_is_zero(total_residual - line_residual, precision_rounding=line_currency.rounding):
                return True

            # Match only one line having a greater residual amount.
            return len(fetched_amls) == 1 and line_residual < total_residual

        query, params = self._get_matching_amls_query(st_lines, excluded_ids=excluded_ids)

        # Add where clause.
        # N.B: move.line currency_id is either set or either got from the company.
        # N.B2: statement.line currency_id is either set, either got from the journal or either got from the company.
        query += '''
            AND partner.id IS NOT NULL
            AND aml.partner_id = partner.id
            AND (
                CASE WHEN st_line.currency_id IS NOT NULL AND st_line.currency_id != aml_company.currency_id THEN
                    aml.currency_id = st_line.currency_id
                WHEN journal.currency_id IS NOT NULL AND journal.currency_id != aml_company.currency_id THEN
                    aml.currency_id = journal.currency_id
                ELSE
                    aml.currency_id IS NULL
                END
            )
        '''
        return query, params, automatic_match_func

    @api.model
    def _get_matching_amls(self, st_lines, excluded_ids=None):
        ''' Apply reconciliation matching rules in order to find matching account.move.lines.

        :param st_lines:        Account.bank.statement.lines recordset.
        :param excluded_ids:    Account.move.lines ids to exclude.
        :return:                A dictionnary mapping each id with:
            * line:     The account.bank.statement.line record.
            * aml_ids:  The matching account.move.line ids.
        '''
        results = dict((r.id, {'line': r, 'aml_ids': []}) for r in st_lines)
        excluded_ids = excluded_ids or []

        rules = [
            self._get_matching_amls_invoice_rule,
            self._get_matching_amls_amount_rule,
        ]
        for rule in rules:
            query, params, automatic_match_func = rule(st_lines, excluded_ids=excluded_ids)
            self._cr.execute(query, params)
            query_res = self._cr.dictfetchall()

            # Map statement line with candidates.
            candidates_map = {}
            for res in query_res:
                candidates_map.setdefault(res['id'], [])
                candidates_map[res['id']].append(res)

            for line_id, fetched_amls in candidates_map.items():
                st_line = results[line_id]['line']

                candidate_amls = []
                candidate_amls_ids = []
                for aml in fetched_amls:
                    if aml['aml_id'] not in excluded_ids:
                        candidate_amls.append(aml)
                        candidate_amls_ids.append(aml['aml_id'])

                if automatic_match_func(results[line_id]['line'], candidate_amls):
                    results[line_id]['aml_ids'] = candidate_amls_ids

                    # Mark statement line as already processed.
                    st_lines -= st_line

                    # Exclude move lines.
                    excluded_ids += candidate_amls_ids
        return results

    ####################################################
    # Public
    ####################################################

    @api.model
    def process_bank_statement_line(self, st_line_ids, data):
        """ Handles data sent from the bank statement reconciliation widget
            (and can otherwise serve as an old-API bridge)

            :param st_line_ids
            :param list of dicts data: must contains the keys
                'counterpart_aml_dicts', 'payment_aml_ids' and 'new_aml_dicts',
                whose value is the same as described in process_reconciliation
                except that ids are used instead of recordsets.
        """
        st_lines = self.env['account.bank.statement.line'].browse(st_line_ids)
        AccountMoveLine = self.env['account.move.line']
        ctx = dict(self._context, force_price_include=False)

        for st_line, datum in pycompat.izip(st_lines, data):
            payment_aml_rec = AccountMoveLine.browse(datum.get('payment_aml_ids', []))

            for aml_dict in datum.get('counterpart_aml_dicts', []):
                aml_dict['move_line'] = AccountMoveLine.browse(aml_dict['counterpart_aml_id'])
                del aml_dict['counterpart_aml_id']

            if datum.get('partner_id') is not None:
                st_line.write({'partner_id': datum['partner_id']})

            st_line.with_context(ctx).process_reconciliation(
                datum.get('counterpart_aml_dicts', []),
                payment_aml_rec,
                datum.get('new_aml_dicts', []))

    @api.model
    def get_move_lines_for_bank_statement_line(self, st_line_id, partner_id=None, excluded_ids=None, search_str=False, offset=0, limit=None):
        """ Returns move lines for the bank statement reconciliation widget,
            formatted as a list of dicts

            :param st_line_id: ids of the statement lines
            :param partner_id: optional partner id to select only the moves
                line corresponding to the partner
            :param excluded_ids: optional move lines ids excluded from the
                result
            :param search_str: optional search (can be the amout, display_name,
                partner name, move line name)
            :param offset: offset of the search result (to display pager)
            :param limit: number of the result to search
        """
        st_line = self.env['account.bank.statement.line'].browse(st_line_id)

        # Blue lines = payment on bank account not assigned to a statement yet
        aml_accounts = [
            st_line.journal_id.default_credit_account_id.id,
            st_line.journal_id.default_debit_account_id.id
        ]

        if partner_id is None:
            partner_id = st_line.partner_id.id

        domain = self._domain_move_lines_for_reconciliation(st_line, aml_accounts, partner_id, excluded_ids=excluded_ids, search_str=search_str)
        recs_count = self.env['account.move.line'].search_count(domain)
        aml_recs = self.env['account.move.line'].search(domain, offset=offset, limit=limit, order="date_maturity desc, id desc")
        target_currency = st_line.currency_id or st_line.journal_id.currency_id or st_line.journal_id.company_id.currency_id
        return self._prepare_move_lines(aml_recs, target_currency=target_currency, target_date=st_line.date, recs_count=recs_count)

    @api.model
    def get_bank_statement_line_data(self, st_line_ids, excluded_ids=None):
        """ Returns the data required to display a reconciliation widget, for
            each statement line in self

            :param st_line_id: ids of the statement lines
            :param excluded_ids: optional move lines ids excluded from the
                result
        """
        excluded_ids = excluded_ids or []
        ret = []
        st_lines = self.env['account.bank.statement.line'].browse(st_line_ids)
        matching_amls = self._get_matching_amls(st_lines, excluded_ids=excluded_ids)

        # Iterate on st_lines to keep the same order in the results list.
        for line in st_lines:
            aml_ids = matching_amls[line.id]['aml_ids']
            amls = aml_ids and self.env['account.move.line'].browse(aml_ids)
            ret.append({
                'st_line': self._get_statement_line(line),
                'reconciliation_proposition': aml_ids and self._prepare_move_lines(amls) or [],
            })
        return ret

    @api.model
    def get_bank_statement_data(self, bank_statement_ids):
        """ Get statement lines of the specified statements or all unreconciled
            statement lines and try to automatically reconcile them / find them
            a partner.
            Return ids of statement lines left to reconcile and other data for
            the reconciliation widget.

            :param st_line_id: ids of the bank statement
        """
        bank_statements = self.env['account.bank.statement'].browse(bank_statement_ids)
        Bank_statement_line = self.env['account.bank.statement.line']

        # NB : The field account_id can be used at the statement line creation/import to avoid the reconciliation process on it later on,
        # this is why we filter out statements lines where account_id is set

        sql_query = """SELECT stl.id
                        FROM account_bank_statement_line stl
                        WHERE account_id IS NULL AND stl.amount != 0.0 AND not exists (select 1 from account_move_line aml where aml.statement_line_id = stl.id)
                """
        params = []
        if bank_statements:
            sql_query += ' AND stl.statement_id IN %s'
            params += (tuple(bank_statements.ids),)
        else:
            sql_query += ' AND stl.company_id = %s'
            params += [self.env.user.company_id.id]
        sql_query += ' ORDER BY stl.id'
        self.env.cr.execute(sql_query, params)
        st_lines_left = Bank_statement_line.browse([line.get('id') for line in self.env.cr.dictfetchall()])

        #try to assign partner to bank_statement_line
        stl_to_assign = st_lines_left.filtered(lambda stl: not stl.partner_id)
        refs = set(stl_to_assign.mapped('name'))
        if stl_to_assign and refs\
           and st_lines_left[0].journal_id.default_credit_account_id\
           and st_lines_left[0].journal_id.default_debit_account_id:

            sql_query = """SELECT aml.partner_id, aml.ref, stl.id
                            FROM account_move_line aml
                                JOIN account_account acc ON acc.id = aml.account_id
                                JOIN account_bank_statement_line stl ON aml.ref = stl.name
                            WHERE (aml.company_id = stl.company_id
                                AND aml.partner_id IS NOT NULL)
                                AND (
                                    (aml.statement_id IS NULL AND aml.account_id IN %s)
                                    OR
                                    (acc.internal_type IN ('payable', 'receivable') AND aml.reconciled = false)
                                    )
                                AND aml.ref IN %s
                                """
            params = ((st_lines_left[0].journal_id.default_credit_account_id.id, st_lines_left[0].journal_id.default_debit_account_id.id), tuple(refs))
            if bank_statements:
                sql_query += 'AND stl.id IN %s'
                params += (tuple(stl_to_assign.ids),)
            self.env.cr.execute(sql_query, params)
            results = self.env.cr.dictfetchall()
            for line in results:
                Bank_statement_line.browse(line.get('id')).write({'partner_id': line.get('partner_id')})

        return {
            'st_lines_ids': st_lines_left.ids,
            'notifications': [],
            'statement_name': len(bank_statements) == 1 and bank_statements[0].name or False,
            'journal_id': bank_statements and bank_statements[0].journal_id.id or False,
            'num_already_reconciled_lines': 0,
        }

    @api.model
    def get_move_lines_for_manual_reconciliation(self, account_id, partner_id=False, excluded_ids=None, search_str=False, offset=0, limit=None, target_currency_id=False):
        """ Returns unreconciled move lines for an account or a partner+account, formatted for the manual reconciliation widget """

        Account_move_line = self.env['account.move.line']
        Account = self.env['account.account']
        Currency = self.env['res.currency']

        domain = self._domain_move_lines_for_manual_reconciliation(account_id, partner_id, excluded_ids, search_str)
        recs_count = Account_move_line.search_count(domain)
        lines = Account_move_line.search(domain, offset=offset, limit=limit, order="date_maturity desc, id desc")
        if target_currency_id:
            target_currency = Currency.browse(target_currency_id)
        else:
            account = Account.browse(account_id)
            target_currency = account.currency_id or account.company_id.currency_id
        return self._prepare_move_lines(lines, target_currency=target_currency,recs_count=recs_count)

    @api.model
    def get_all_data_for_manual_reconciliation(self, partner_ids, account_ids):
        """ Returns the data required for the invoices & payments matching of partners/accounts.
            If an argument is None, fetch all related reconciliations. Use [] to fetch nothing.
        """
        return {
            'customers': self.get_data_for_manual_reconciliation('partner', partner_ids, 'receivable'),
            'suppliers': self.get_data_for_manual_reconciliation('partner', partner_ids, 'payable'),
            'accounts': self.get_data_for_manual_reconciliation('account', account_ids),
        }

    @api.model
    def get_data_for_manual_reconciliation(self, res_type, res_ids=None, account_type=None):
        """ Returns the data required for the invoices & payments matching of partners/accounts (list of dicts).
            If no res_ids is passed, returns data for all partners/accounts that can be reconciled.

            :param res_type: either 'partner' or 'account'
            :param res_ids: ids of the partners/accounts to reconcile, use None to fetch data indiscriminately
                of the id, use [] to prevent from fetching any data at all.
            :param account_type: if a partner is both customer and vendor, you can use 'payable' to reconcile
                the vendor-related journal entries and 'receivable' for the customer-related entries.
        """

        Account = self.env['account.account']
        Partner = self.env['res.partner']

        if res_ids is not None and len(res_ids) == 0:
            # Note : this short-circuiting is better for performances, but also required
            # since postgresql doesn't implement empty list (so 'AND id in ()' is useless)
            return []
        res_ids = res_ids and tuple(res_ids)

        assert res_type in ('partner', 'account')
        assert account_type in ('payable', 'receivable', None)
        is_partner = res_type == 'partner'
        res_alias = is_partner and 'p' or 'a'
        aml_ids = self._context.get('active_ids') and self._context.get('active_model') == 'account.move.line' and tuple(self._context.get('active_ids'))

        query = ("""
            SELECT {0} account_id, account_name, account_code, max_date,
                   to_char(last_time_entries_checked, 'YYYY-MM-DD') AS last_time_entries_checked
            FROM (
                    SELECT {1}
                        {res_alias}.last_time_entries_checked AS last_time_entries_checked,
                        a.id AS account_id,
                        a.name AS account_name,
                        a.code AS account_code,
                        MAX(l.write_date) AS max_date
                    FROM
                        account_move_line l
                        RIGHT JOIN account_account a ON (a.id = l.account_id)
                        RIGHT JOIN account_account_type at ON (at.id = a.user_type_id)
                        {2}
                    WHERE
                        a.reconcile IS TRUE
                        AND l.full_reconcile_id is NULL
                        {3}
                        {4}
                        {5}
                        AND l.company_id = {6}
                        AND EXISTS (
                            SELECT NULL
                            FROM account_move_line l
                            WHERE l.account_id = a.id
                            {7}
                            AND l.amount_residual > 0
                        )
                        AND EXISTS (
                            SELECT NULL
                            FROM account_move_line l
                            WHERE l.account_id = a.id
                            {7}
                            AND l.amount_residual < 0
                        )
                        {8}
                    GROUP BY {9} a.id, a.name, a.code, {res_alias}.last_time_entries_checked
                    ORDER BY {res_alias}.last_time_entries_checked
                ) as s
            WHERE (last_time_entries_checked IS NULL OR max_date > last_time_entries_checked)
        """.format(
                is_partner and 'partner_id, partner_name,' or ' ',
                is_partner and 'p.id AS partner_id, p.name AS partner_name,' or ' ',
                is_partner and 'RIGHT JOIN res_partner p ON (l.partner_id = p.id)' or ' ',
                is_partner and ' ' or "AND at.type <> 'payable' AND at.type <> 'receivable'",
                account_type and "AND at.type = %(account_type)s" or '',
                res_ids and 'AND ' + res_alias + '.id in %(res_ids)s' or '',
                self.env.user.company_id.id,
                is_partner and 'AND l.partner_id = p.id' or ' ',
                aml_ids and 'AND l.id IN %(aml_ids)s' or '',
                is_partner and 'l.partner_id, p.id,' or ' ',
                res_alias=res_alias
            ))
        self.env.cr.execute(query, locals())

        # Apply ir_rules by filtering out
        rows = self.env.cr.dictfetchall()
        ids = [x['account_id'] for x in rows]
        allowed_ids = set(Account.browse(ids).ids)
        rows = [row for row in rows if row['account_id'] in allowed_ids]
        if is_partner:
            ids = [x['partner_id'] for x in rows]
            allowed_ids = set(Partner.browse(ids).ids)
            rows = [row for row in rows if row['partner_id'] in allowed_ids]

        # Fetch other data
        for row in rows:
            account = Account.browse(row['account_id'])
            currency = account.currency_id or account.company_id.currency_id
            row['currency_id'] = currency.id
            partner_id = is_partner and row['partner_id'] or None
            rec_prop = aml_ids and self.env['account.move.line'].browse(aml_ids) or self._get_move_line_reconciliation_proposition(account.id, partner_id)
            row['reconciliation_proposition'] = self._prepare_move_lines(rec_prop, target_currency=currency)
            row['company_id'] = account.company_id.id
        return rows

    @api.model
    def process_move_lines(self, data):
        """ Used to validate a batch of reconciliations in a single call
            :param data: list of dicts containing:
                - 'type': either 'partner' or 'account'
                - 'id': id of the affected res.partner or account.account
                - 'mv_line_ids': ids of existing account.move.line to reconcile
                - 'new_mv_line_dicts': list of dicts containing values suitable for account_move_line.create()
        """

        Partner = self.env['res.partner']
        Account = self.env['account.account']

        for datum in data:
            if len(datum['mv_line_ids']) >= 1 or len(datum['mv_line_ids']) + len(datum['new_mv_line_dicts']) >= 2:
                self._process_move_lines(datum['mv_line_ids'], datum['new_mv_line_dicts'])

            if datum['type'] == 'partner':
                partners = Partner.browse(datum['id'])
                partners.mark_as_reconciled()
            if datum['type'] == 'account':
                accounts = Account.browse(datum['id'])
                accounts.mark_as_reconciled()

    ####################################################
    # Private
    ####################################################

    @api.model
    def _domain_move_lines(self, search_str):
        """ Returns the domain from the search_str search
            :param search_str: search string
        """
        if not search_str:
            return []
        str_domain = [
            '|', ('move_id.name', 'ilike', search_str),
            '|', ('move_id.ref', 'ilike', search_str),
            '|', ('date_maturity', 'like', search_str),
            '&', ('name', '!=', '/'), ('name', 'ilike', search_str)
        ]
        if search_str[0] in ['-', '+']:
            try:
                amounts_str = search_str.split('|')
                for amount_str in amounts_str:
                    amount = amount_str[0] == '-' and float(amount_str) or float(amount_str[1:])
                    amount_domain = [
                        '|', ('amount_residual', '=', amount),
                        '|', ('amount_residual_currency', '=', amount),
                        '|', (amount_str[0] == '-' and 'credit' or 'debit', '=', float(amount_str[1:])),
                        ('amount_currency', '=', amount),
                    ]
                    str_domain = expression.OR([str_domain, amount_domain])
            except:
                pass
        else:
            try:
                amount = float(search_str)
                amount_domain = [
                    '|', ('amount_residual', '=', amount),
                    '|', ('amount_residual_currency', '=', amount),
                    '|', ('amount_residual', '=', -amount),
                    '|', ('amount_residual_currency', '=', -amount),
                    '&', ('account_id.internal_type', '=', 'liquidity'),
                    '|', '|', '|', ('debit', '=', amount), ('credit', '=', amount), ('amount_currency', '=', amount), ('amount_currency', '=', -amount),
                ]
                str_domain = expression.OR([str_domain, amount_domain])
            except:
                pass
        return str_domain

    @api.model
    def _domain_move_lines_for_reconciliation(self, st_line, aml_accounts, partner_id, excluded_ids=None, search_str=False):
        """ Return the domain for account.move.line records which can be used for bank statement reconciliation.

            :param aml_accounts:
            :param partner_id:
            :param excluded_ids:
            :param search_str:
        """

        domain_reconciliation = [
            '&', '&',
            ('statement_line_id', '=', False),
            ('account_id', 'in', aml_accounts),
            ('payment_id', '<>', False)
        ]

        # Black lines = unreconciled & (not linked to a payment or open balance created by statement
        domain_matching = [('reconciled', '=', False)]
        if partner_id:
            domain_matching = expression.AND([
                domain_matching,
                [('account_id.internal_type', 'in', ['payable', 'receivable'])]
            ])
        else:
            # TODO : find out what use case this permits (match a check payment, registered on a journal whose account type is other instead of liquidity)
            domain_matching = expression.AND([
                domain_matching,
                [('account_id.reconcile', '=', True)]
            ])

        # Let's add what applies to both
        domain = expression.OR([domain_reconciliation, domain_matching])
        if partner_id:
            domain = expression.AND([domain, [('partner_id', '=', partner_id)]])

        # Domain factorized for all reconciliation use cases
        if search_str:
            str_domain = self._domain_move_lines(search_str=search_str)
            if not partner_id:
                str_domain = expression.OR([
                    str_domain,
                    [('partner_id.name', 'ilike', search_str)]
                ])
            domain = expression.AND([
                domain,
                str_domain
            ])

        if excluded_ids:
            domain = expression.AND([
                [('id', 'not in', excluded_ids)],
                domain
            ])
        # filter on account.move.line having the same company as the statement line
        domain = expression.AND([domain, [('company_id', '=', st_line.company_id.id)]])

        if st_line.company_id.account_bank_reconciliation_start:
            domain = expression.AND([domain, [('date', '>=', st_line.company_id.account_bank_reconciliation_start)]])

        return domain

    @api.model
    def _domain_move_lines_for_manual_reconciliation(self, account_id, partner_id=False, excluded_ids=None, search_str=False):
        """ Create domain criteria that are relevant to manual reconciliation. """
        domain = ['&', ('reconciled', '=', False), ('account_id', '=', account_id)]
        if partner_id:
            domain = expression.AND([domain, [('partner_id', '=', partner_id)]])
        if excluded_ids:
            domain = expression.AND([[('id', 'not in', excluded_ids)], domain])
        if search_str:
            str_domain = self._domain_move_lines(search_str=search_str)
            domain = expression.AND([domain, str_domain])
        # filter on account.move.line having the same company as the given account
        account = self.env['account.account'].browse(account_id)
        domain = expression.AND([domain, [('company_id', '=', account.company_id.id)]])
        return domain

    @api.model
    def _prepare_move_lines(self, move_lines, target_currency=False, target_date=False, recs_count=0):
        """ Returns move lines formatted for the manual/bank reconciliation widget

            :param move_line_ids:
            :param target_currency: currency (browse) you want the move line debit/credit converted into
            :param target_date: date to use for the monetary conversion
        """
        context = dict(self._context or {})
        ret = []

        for line in move_lines:
            company_currency = line.account_id.company_id.currency_id
            line_currency = (line.currency_id and line.amount_currency) and line.currency_id or company_currency
            ret_line = {
                'id': line.id,
                'name': line.name and line.name != '/' and line.move_id.name + ': ' + line.name or line.move_id.name,
                'ref': line.move_id.ref or '',
                # For reconciliation between statement transactions and already registered payments (eg. checks)
                # NB : we don't use the 'reconciled' field because the line we're selecting is not the one that gets reconciled
                'account_id': [line.account_id.id, line.account_id.display_name],
                'already_paid': line.account_id.internal_type == 'liquidity',
                'account_code': line.account_id.code,
                'account_name': line.account_id.name,
                'account_type': line.account_id.internal_type,
                'date_maturity': line.date_maturity,
                'date': line.date,
                'journal_id': [line.journal_id.id, line.journal_id.display_name],
                'partner_id': line.partner_id.id,
                'partner_name': line.partner_id.name,
                'currency_id': line_currency.id,
            }

            debit = line.debit
            credit = line.credit
            amount = line.amount_residual
            amount_currency = line.amount_residual_currency

            # For already reconciled lines, don't use amount_residual(_currency)
            if line.account_id.internal_type == 'liquidity':
                amount = debit - credit
                amount_currency = line.amount_currency

            target_currency = target_currency or company_currency

            # Use case:
            # Let's assume that company currency is in USD and that we have the 3 following move lines
            #      Debit  Credit  Amount currency  Currency
            # 1)    25      0            0            NULL
            # 2)    17      0           25             EUR
            # 3)    33      0           25             YEN
            #
            # If we ask to see the information in the reconciliation widget in company currency, we want to see
            # The following information
            # 1) 25 USD (no currency information)
            # 2) 17 USD [25 EUR] (show 25 euro in currency information, in the little bill)
            # 3) 33 USD [25 YEN] (show 25 yen in currency information)
            #
            # If we ask to see the information in another currency than the company let's say EUR
            # 1) 35 EUR [25 USD]
            # 2) 25 EUR (no currency information)
            # 3) 50 EUR [25 YEN]
            # In that case, we have to convert the debit-credit to the currency we want and we show next to it
            # the value of the amount_currency or the debit-credit if no amount currency
            if target_currency == company_currency:
                if line_currency == target_currency:
                    amount = amount
                    amount_currency = ""
                    total_amount = debit - credit
                    total_amount_currency = ""
                else:
                    amount = amount
                    amount_currency = amount_currency
                    total_amount = debit - credit
                    total_amount_currency = line.amount_currency

            if target_currency != company_currency:
                if line_currency == target_currency:
                    amount = amount_currency
                    amount_currency = ""
                    total_amount = line.amount_currency
                    total_amount_currency = ""
                else:
                    amount_currency = line.currency_id and amount_currency or amount
                    company = line.account_id.company_id
                    date = target_date or line.date
                    amount = company_currency._convert(amount, target_currency, company, date)
                    total_amount = company_currency._convert((line.debit - line.credit), target_currency, company, date)
                    total_amount_currency = line.currency_id and line.amount_currency or (line.debit - line.credit)

            ret_line['recs_count'] = recs_count
            ret_line['debit'] = amount > 0 and amount or 0
            ret_line['credit'] = amount < 0 and -amount or 0
            ret_line['amount_currency'] = amount_currency
            ret_line['amount_str'] = formatLang(self.env, abs(amount), currency_obj=target_currency)
            ret_line['total_amount_str'] = formatLang(self.env, abs(total_amount), currency_obj=target_currency)
            ret_line['amount_currency_str'] = amount_currency and formatLang(self.env, abs(amount_currency), currency_obj=line_currency) or ""
            ret_line['total_amount_currency_str'] = total_amount_currency and formatLang(self.env, abs(total_amount_currency), currency_obj=line_currency) or ""
            ret.append(ret_line)
        return ret

    @api.model
    def _get_statement_line(self, st_line):
        """ Returns the data required by the bank statement reconciliation widget to display a statement line """

        statement_currency = st_line.journal_id.currency_id or st_line.journal_id.company_id.currency_id
        if st_line.amount_currency and st_line.currency_id:
            amount = st_line.amount_currency
            amount_currency = st_line.amount
            amount_currency_str = formatLang(self.env, abs(amount_currency), currency_obj=statement_currency)
        else:
            amount = st_line.amount
            amount_currency = amount
            amount_currency_str = ""
        amount_str = formatLang(self.env, abs(amount), currency_obj=st_line.currency_id or statement_currency)

        data = {
            'id': st_line.id,
            'ref': st_line.ref,
            'note': st_line.note or "",
            'name': st_line.name,
            'date': st_line.date,
            'amount': amount,
            'amount_str': amount_str,  # Amount in the statement line currency
            'currency_id': st_line.currency_id.id or statement_currency.id,
            'partner_id': st_line.partner_id.id,
            'journal_id': st_line.journal_id.id,
            'statement_id': st_line.statement_id.id,
            'account_id': [st_line.journal_id.default_debit_account_id.id, st_line.journal_id.default_debit_account_id.display_name],
            'account_code': st_line.journal_id.default_debit_account_id.code,
            'account_name': st_line.journal_id.default_debit_account_id.name,
            'partner_name': st_line.partner_id.name,
            'communication_partner_name': st_line.partner_name,
            'amount_currency_str': amount_currency_str,  # Amount in the statement currency
            'amount_currency': amount_currency,  # Amount in the statement currency
            'has_no_partner': not st_line.partner_id.id,
            'company_id': st_line.company_id.id,
        }
        if st_line.partner_id:
            if amount > 0:
                data['open_balance_account_id'] = st_line.partner_id.property_account_receivable_id.id
            else:
                data['open_balance_account_id'] = st_line.partner_id.property_account_payable_id.id

        return data

    @api.model
    def _get_move_line_reconciliation_proposition(self, account_id, partner_id=None):
        """ Returns two lines whose amount are opposite """

        Account_move_line = self.env['account.move.line']

        ir_rules_query = Account_move_line._where_calc([])
        Account_move_line._apply_ir_rules(ir_rules_query, 'read')
        from_clause, where_clause, where_clause_params = ir_rules_query.get_sql()
        where_str = where_clause and (" WHERE %s" % where_clause) or ''

        # Get pairs
        query = """
            SELECT a.id, b.id
            FROM account_move_line a, account_move_line b
            WHERE a.id != b.id
            AND a.amount_residual = -b.amount_residual
            AND NOT a.reconciled
            AND a.account_id = %s
            AND (%s IS NULL AND b.account_id = %s)
            AND (%s IS NULL AND NOT b.reconciled OR b.id = %s)
            AND (%s is NULL OR (a.partner_id = %s AND b.partner_id = %s))
            AND a.id IN (SELECT id FROM {0})
            AND b.id IN (SELECT id FROM {0})
            ORDER BY a.date desc
            LIMIT 1
            """.format(from_clause + where_str)
        move_line_id = self.env.context.get('move_line_id') or None
        params = [
            account_id,
            move_line_id, account_id,
            move_line_id, move_line_id,
            partner_id, partner_id, partner_id,
        ] + where_clause_params + where_clause_params
        self.env.cr.execute(query, params)

        pairs = self.env.cr.fetchall()

        if pairs:
            return Account_move_line.browse(pairs[0])
        return Account_move_line

    @api.model
    def _process_move_lines(self, move_line_ids, new_mv_line_dicts):
        """ Create new move lines from new_mv_line_dicts (if not empty) then call reconcile_partial on self and new move lines

            :param new_mv_line_dicts: list of dicts containing values suitable for account_move_line.create()
        """
        if len(move_line_ids) < 1 or len(move_line_ids) + len(new_mv_line_dicts) < 2:
            raise UserError(_('A reconciliation must involve at least 2 move lines.'))

        account_move_line = self.env['account.move.line'].browse(move_line_ids)
        writeoff_lines = self.env['account.move.line']

        # Create writeoff move lines
        if len(new_mv_line_dicts) > 0:
            company_currency = account_move_line[0].account_id.company_id.currency_id
            company = account_move_line[0].account_id.company_id
            date = fields.Date.today()
            writeoff_currency = account_move_line[0].currency_id or company_currency
            for mv_line_dict in new_mv_line_dicts:
                if writeoff_currency != company_currency:
                    mv_line_dict['debit'] = writeoff_currency._convert(mv_line_dict['debit'], company_currency, company, date)
                    mv_line_dict['credit'] = writeoff_currency._convert(mv_line_dict['credit'], company_currency, company, date)
                writeoff_lines += account_move_line._create_writeoff([mv_line_dict])

            (account_move_line + writeoff_lines).reconcile()
        else:
            account_move_line.reconcile()
